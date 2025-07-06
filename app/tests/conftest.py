import pytest
from datetime import datetime
from app import create_app, db
from app.models import Stashpoint, Customer
from config import TestConfig


@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def sample_stashpoints(app):
    """Create sample stashpoints for testing"""
    with app.app_context():
        stashpoints = [
            Stashpoint(
                id="sp1",
                name="Central Station Storage",
                description="Near the main station",
                address="123 Station Road",
                postal_code="SW1A 1AA",
                latitude=51.5074,
                longitude=-0.1278,
                capacity=50,
                open_from=datetime.strptime("08:00", "%H:%M").time(),
                open_until=datetime.strptime("22:00", "%H:%M").time()
            ),
            Stashpoint(
                id="sp2",
                name="Airport Express Storage",
                description="24/7 storage facility",
                address="456 Airport Way",
                postal_code="SW1A 2BB",
                latitude=51.5144,
                longitude=-0.1226,
                capacity=100,
                open_from=datetime.strptime("00:00", "%H:%M").time(),
                open_until=datetime.strptime("23:59", "%H:%M").time()
            ),
            Stashpoint(
                id="sp3",
                name="Far Away Storage",
                description="Remote location",
                address="789 Distant Street",
                postal_code="SW1A 3CC",
                latitude=52.0000,
                longitude=-1.0000,
                capacity=30,
                open_from=datetime.strptime("09:00", "%H:%M").time(),
                open_until=datetime.strptime("17:00", "%H:%M").time()
            )
        ]
        
        for sp in stashpoints:
            db.session.add(sp)
        db.session.commit()
        
        return stashpoints


@pytest.fixture
def sample_customer(app):
    """Create a sample customer for bookings"""
    with app.app_context():
        customer = Customer(
            id="cust1",
            email="test@example.com",
            name="Test Customer"
        )
        db.session.add(customer)
        db.session.commit()
        yield customer