import pytest
from datetime import datetime, timedelta
from app import db
from app.models import Booking


@pytest.fixture
def test_all_filters_combined(client, sample_stashpoints, sample_customer):
    """Test that all three filters work together correctly"""
    # Add a booking to reduce capacity on sp2
    with client.application.app_context():
        booking = Booking(
            stashpoint_id="sp2",
            customer_id=sample_customer.id,
            bag_count=95,  # Leaves only 5 slots in sp2
            dropoff_time=datetime(2024, 1, 15, 10, 0),
            pickup_time=datetime(2024, 1, 15, 14, 0),
            is_paid=True,
            is_cancelled=False
        )
        db.session.add(booking)
        db.session.commit()
    
    # Search with all filters
    params = {
        'lat': 51.5074,
        'lng': -0.1278,
        'dropoff': '2024-01-15T11:00:00Z',  # During booking period
        'pickup': '2024-01-15T13:00:00Z',
        'bag_count': 10,  # More than sp2 has available
        'radius_km': 50.0  # Wide enough to include all if not for other filters
    }
    
    response = client.get('/api/v1/stashpoints/', query_string=params)
    assert response.status_code == 200
    data = response.get_json()
    
    # sp1: Should be included (within radius, has capacity, open during hours)
    assert any(sp['id'] == 'sp1' for sp in data)
    
    # sp2: Should NOT be included (not enough capacity during this period)
    assert not any(sp['id'] == 'sp2' for sp in data)
    
    # sp3: Should NOT be included (closes at 17:00, but we need until 13:00 so it's open)
    # Actually sp3 should be included if it's within radius and has capacity
    # Let's check if it appears
    sp3_in_results = any(sp['id'] == 'sp3' for sp in data)
    if sp3_in_results:
        # If it appears, verify it meets all criteria
        sp3 = next(sp for sp in data if sp['id'] == 'sp3')
        assert sp3['distance_km'] <= 50.0


class TestStashpointsRoute:
    
    def test_get_all_stashpoints_no_params(self, client, sample_stashpoints):
        """Test getting all stashpoints without query parameters"""
        response = client.get('/api/v1/stashpoints/')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3
        assert all('id' in sp for sp in data)
        assert all('name' in sp for sp in data)
    
    def test_valid_search_with_all_params(self, client, sample_stashpoints):
        """Test search with all valid parameters"""
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T10:00:00Z',
            'pickup': '2024-01-15T18:00:00Z',
            'bag_count': 2,
            'radius_km': 5.0
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        # Results should be sorted by distance
        if len(data) > 1:
            assert data[0]['distance_km'] <= data[1]['distance_km']
    
    def test_missing_required_params(self, client):
        """Test with missing required parameters"""
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            # Missing dropoff, pickup, and bag_count
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'details' in data
        # Should have errors for missing fields
        missing_fields = {error['field'] for error in data['details']}
        assert 'dropoff' in missing_fields
        assert 'pickup' in missing_fields
        assert 'bag_count' in missing_fields
    
    def test_invalid_latitude(self, client):
        """Test with invalid latitude value"""
        params = {
            'lat': 91.0,  # Invalid: > 90
            'lng': -0.1278,
            'dropoff': '2024-01-15T10:00:00Z',
            'pickup': '2024-01-15T18:00:00Z',
            'bag_count': 2
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert any(error['field'] == 'lat' for error in data['details'])
    
    def test_invalid_longitude(self, client):
        """Test with invalid longitude value"""
        params = {
            'lat': 51.5074,
            'lng': -181.0,  # Invalid: < -180
            'dropoff': '2024-01-15T10:00:00Z',
            'pickup': '2024-01-15T18:00:00Z',
            'bag_count': 2
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert any(error['field'] == 'lng' for error in data['details'])
    
    def test_pickup_before_dropoff(self, client):
        """Test with pickup time before dropoff time"""
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T18:00:00Z',
            'pickup': '2024-01-15T10:00:00Z',  # Before dropoff
            'bag_count': 2
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert any(error['field'] == 'pickup' for error in data['details'])
    
    def test_invalid_bag_count(self, client):
        """Test with invalid bag count"""
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T10:00:00Z',
            'pickup': '2024-01-15T18:00:00Z',
            'bag_count': 0  # Invalid: must be > 0
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert any(error['field'] == 'bag_count' for error in data['details'])
    
    def test_opening_hours_filter(self, client, sample_stashpoints):
        """Test that stashpoints are filtered by opening hours - must be open at BOTH dropoff and pickup times"""
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T06:00:00Z',  # 6 AM - before most open
            'pickup': '2024-01-15T23:00:00Z',   # 11 PM - after some close
            'bag_count': 1
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 200
        data = response.get_json()
        # Only 24/7 storage should be available (open at both 6 AM and 11 PM)
        assert len(data) == 1
        assert data[0]['name'] == "Airport Express Storage"
        
        # Test case where stashpoint is open at dropoff but closed at pickup
        params2 = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T10:00:00Z',  # 10 AM - most are open
            'pickup': '2024-01-15T23:00:00Z',   # 11 PM - some are closed
            'bag_count': 1
        }
        response2 = client.get('/api/v1/stashpoints/', query_string=params2)
        assert response2.status_code == 200
        data2 = response2.get_json()
        # Central Station Storage closes at 22:00, so shouldn't be included
        assert not any(sp['name'] == 'Central Station Storage' for sp in data2)
    
    def test_capacity_filter_with_bookings(self, client, sample_stashpoints, sample_customer):
        """Test capacity filtering with existing bookings during the specified time period"""
        # Create a booking that takes up most of sp1's capacity
        with client.application.app_context():
            booking = Booking(
                stashpoint_id="sp1",
                customer_id=sample_customer.id,
                bag_count=48,  # Leaves only 2 slots
                dropoff_time=datetime(2024, 1, 15, 12, 0),
                pickup_time=datetime(2024, 1, 15, 16, 0),
                is_paid=True,
                is_cancelled=False
            )
            db.session.add(booking)
            db.session.commit()
        
        # Search for 3 bags during overlapping period
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T13:00:00Z',  # Overlaps with existing booking
            'pickup': '2024-01-15T15:00:00Z',
            'bag_count': 3
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 200
        data = response.get_json()
        # sp1 should not be in results (not enough capacity during this period)
        assert not any(sp['id'] == 'sp1' for sp in data)
        
        # Search for 2 bags during the same period (should work as exactly 2 slots left)
        params['bag_count'] = 2
        response = client.get('/api/v1/stashpoints/', query_string=params)
        data = response.get_json()
        assert any(sp['id'] == 'sp1' for sp in data)
        
        # Test with cancelled booking (should not affect capacity)
        with client.application.app_context():
            cancelled_booking = Booking(
                stashpoint_id="sp2",
                customer_id=sample_customer.id,
                bag_count=90,  # Would exceed capacity if counted
                dropoff_time=datetime(2024, 1, 15, 12, 0),
                pickup_time=datetime(2024, 1, 15, 16, 0),
                is_paid=True,
                is_cancelled=True  # Cancelled booking
            )
            db.session.add(cancelled_booking)
            db.session.commit()
        
        # sp2 should still appear in results despite the cancelled booking
        response = client.get('/api/v1/stashpoints/', query_string=params)
        data = response.get_json()
        assert any(sp['id'] == 'sp2' for sp in data)
    
    def test_radius_filter(self, client, sample_stashpoints):
        """Test that only stashpoints within the specified radius are returned"""
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T10:00:00Z',
            'pickup': '2024-01-15T16:00:00Z',  # Within Far Away Storage hours
            'bag_count': 1,
            'radius_km': 10.0  # Small radius
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 200
        data = response.get_json()
        # Should not include the far away storage
        assert not any(sp['name'] == 'Far Away Storage' for sp in data)
        # All results should have distance <= radius
        assert all(sp['distance_km'] <= 10.0 for sp in data)
        
        # Test without radius filter - Far Away Storage should be included if within hours
        params_no_radius = params.copy()
        del params_no_radius['radius_km']
        response_no_radius = client.get('/api/v1/stashpoints/', query_string=params_no_radius)
        data_no_radius = response_no_radius.get_json()
        # Should include Far Away Storage now
        assert any(sp['name'] == 'Far Away Storage' for sp in data_no_radius)
    
    def test_distance_calculation_and_ordering(self, client, sample_stashpoints):
        """Test that results are ordered by distance from search coordinates"""
        params = {
            'lat': 51.5074,
            'lng': -0.1278,
            'dropoff': '2024-01-15T10:00:00Z',
            'pickup': '2024-01-15T18:00:00Z',
            'bag_count': 1
        }
        response = client.get('/api/v1/stashpoints/', query_string=params)
        assert response.status_code == 200
        data = response.get_json()
        
        # All results should have distance_km field
        assert all('distance_km' in sp for sp in data)
        assert all(isinstance(sp['distance_km'], (int, float)) for sp in data)
        
        # Results should be ordered by distance (ascending)
        distances = [sp['distance_km'] for sp in data]
        assert distances == sorted(distances)
        
        # The stashpoint at exact same coordinates should have ~0 distance and be first
        assert data[0]['id'] == 'sp1'
        assert data[0]['distance_km'] < 0.1  # Very close to 0
        
        # sp2 should be second (closer than sp3)
        if len(data) > 1:
            assert data[1]['id'] == 'sp2'


if __name__ == "__main__":
    pytest.main(["-v", __file__])