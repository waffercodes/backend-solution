from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class StashpointSearchParams(BaseModel):
    """Validates search params for the stashpoints endpoint"""
    
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    dropoff: datetime = Field(..., description="Dropoff time (ISO format)")
    pickup: datetime = Field(..., description="Pickup time (ISO format)")
    bag_count: int = Field(..., gt=0, description="Number of bags")
    radius_km: Optional[float] = Field(None, gt=0, description="Max distance in km")
    
    @field_validator('lat')
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return value
    
    @field_validator('lng')
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return value
    
    @field_validator('pickup')
    @classmethod
    def validate_pickup_after_dropoff(cls, value: datetime, info) -> datetime:
        if 'dropoff' in info.data and value <= info.data['dropoff']:
            raise ValueError('Pickup time must be after dropoff time')
        return value
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "lat": 51.5074,
                "lng": -0.1278,
                "dropoff": "2024-01-15T10:00:00Z",
                "pickup": "2024-01-15T18:00:00Z",
                "bag_count": 2,
                "radius_km": 5.0
            }
        }
    )


class StashpointResponse(BaseModel):
    """Response model for stashpoints"""
    
    id: str
    name: str
    description: Optional[str]
    address: str
    postal_code: str
    latitude: float
    longitude: float
    capacity: int
    open_from: str
    open_until: str
    distance_km: Optional[float] = Field(None, description="Distance in km")
    
    model_config = ConfigDict(
        from_attributes=True
    )