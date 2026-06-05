"""Store model with GeoJSON location and operating context."""

from pydantic import BaseModel, Field


class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float] = Field(default_factory=list)  # [lng, lat]


class OpeningHours(BaseModel):
    monday: str = "10:00-22:00"
    tuesday: str = "10:00-22:00"
    wednesday: str = "10:00-22:00"
    thursday: str = "10:00-22:00"
    friday: str = "10:00-22:30"
    saturday: str = "10:00-22:30"
    sunday: str = "10:00-22:00"


class Store(BaseModel):
    store_id: str
    name: str
    brand: str = "RetailGroup"  # RetailGroup, MaxValu, RetailGroup BiG, RetailGroup Credit, RetailGroup Bank
    state: str = ""
    city: str = ""
    address: str = ""
    location: GeoJSONPoint | None = None
    format: str = ""  # mall, standalone, hypermart, digital, branch, kiosk
    opening_date: str = ""
    size_sqm: int = 0
    opening_hours: OpeningHours = Field(default_factory=OpeningHours)
    anchor_tenants: list[str] = Field(default_factory=list)
    parking_bays: int = 0
    avg_daily_footfall: int = 0
    has_drive_thru: bool = False
    has_food_court: bool = False
    services_offered: list[str] = Field(default_factory=list)
