# Stasher Interview Backend Solution

Solution by Delkys Welffer for Stasher interview challenge[https://github.com/stasher-city/backend-test]

## Getting Started

### Prerequisites

- Docker and Docker Compose installed on your machine
- Git

### Setup

1. Clone this repository
2. Navigate to the project directory
3. Start the application using Docker Compose:

```bash
docker-compose up -d
```

4. The API will be available at `http://localhost:5000`
5. You can verify it's running with:

```bash
curl http://localhost:5000/healthcheck
```

## The Challenge

### Current Functionality

The application already has basic functionality:

- A Stashpoint model that represents bag storage locations
- A Booking model to track bag storage reservations
- An endpoint to list all stashpoints at `/api/v1/stashpoints/`
- Database with test data pre-populated

### Your Task

You need to enhance the stashpoints endpoint to allow filtering by availability. The endpoint should:

1. Accept the following query parameters:

   - `lat` (float): Latitude for the search location
   - `lng` (float): Longitude for the search location
   - `dropoff` (ISO datetime): When the user wants to drop off their bags
   - `pickup` (ISO datetime): When the user wants to pick up their bags
   - `bag_count` (integer): Number of bags to store
   - `radius_km` (float, optional): Search radius in kilometers

2. Return only stashpoints that:

   - Are within the specified radius of the coordinates
   - Have enough capacity for the requested number of bags during the specified time period
   - Are open during the requested drop-off and pick-up times

3. Results should be ordered by distance from the search coordinates

# The Solution

## Get All Stashpoints

To retrieve all stashpoints without any filtering:

```bash
GET /api/v1/stashpoints/
```

## Search Stashpoints with Query Parameters

To search for stashpoints based on location, time, and capacity requirements:

```bash
GET /api/v1/stashpoints/?lat=51.5074&lng=-0.1278&dropoff=2024-01-15T10:00:00Z&pickup=2024-01-15T18:00:00Z&bag_count=2&radius_km=5.0
```

### Query Parameters

- **lat** (required): Latitude for the search location (e.g., 51.5074)
- **lng** (required): Longitude for the search location (e.g., -0.1278)
- **dropoff** (required): ISO datetime when bags will be dropped off (e.g., 2024-01-15T10:00:00Z)
- **pickup** (required): ISO datetime when bags will be picked up (e.g., 2024-01-15T18:00:00Z)
- **bag_count** (required): Number of bags to store (must be greater than 0)
- **radius_km** (optional): Search radius in kilometers (e.g., 5.0)

### Example Response

```json
[
  {
    "id": "abc123",
    "name": "Central Station Storage",
    "description": "Secure storage near the main station",
    "address": "123 Station Road",
    "postal_code": "SW1A 1AA",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "capacity": 50,
    "open_from": "08:00",
    "open_until": "22:00",
    "distance_km": 0.5
  },
  {
    "id": "def456",
    "name": "Airport Express Storage",
    "description": "24/7 storage facility",
    "address": "456 Airport Way",
    "postal_code": "SW1A 2BB",
    "latitude": 51.5144,
    "longitude": -0.1226,
    "capacity": 100,
    "open_from": "00:00",
    "open_until": "23:59",
    "distance_km": 1.2
  }
]
```

### Error Response Examples

#### Missing Required Parameters

```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "lat",
      "message": "field required",
      "type": "value_error.missing"
    },
    {
      "field": "lng",
      "message": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Invalid Parameter Values

```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "lat",
      "message": "Latitude must be between -90 and 90",
      "type": "value_error"
    }
  ]
}
```

#### Pickup Before Dropoff

```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "pickup",
      "message": "Pickup time must be after dropoff time",
      "type": "value_error"
    }
  ]
}
```

### Filtering Logic

The endpoint returns only stashpoints that meet ALL of the following criteria:

1. **Distance**: Are within the specified radius of the coordinates (if radius_km is provided)
2. **Capacity**: Have enough capacity for the requested number of bags during the specified time period
   - Checks existing bookings that overlap with the requested dropoff-pickup period
   - Cancelled bookings are not counted against capacity
3. **Opening Hours**: Are open during BOTH the requested drop-off and pick-up times
   - The stashpoint must be open at the exact dropoff time or after
   - The stashpoint must be open at the exact pickup time or before

Results are ordered by distance from the search coordinates (closest first).

## Running tests

### Run all tests
```bash
docker-compose run --rm app pytest app/tests/
```

### Run specific test file
```bash
docker-compose run --rm app pytest app/tests/stashpoints.py
```

### Run with verbose output
```bash
docker-compose run --rm app pytest app/tests/ -v
```
