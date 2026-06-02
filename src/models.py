from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class GeoPoint(BaseModel):
    lat: float
    lng: float

    def maps_url(self) -> str:
        return f"https://yandex.ru/maps/?pt={self.lng},{self.lat}&z=17"

    def route_from(self, origin: "GeoPoint") -> str:
        return f"https://yandex.ru/maps/?rtext={origin.lat},{origin.lng}~{self.lat},{self.lng}"


class GreenZone(BaseModel):
    name: Optional[str] = None
    zone_type: str = Field(
        ..., description="park | pond | alley | square | forest | unknown"
    )
    distance_meters: Optional[float] = None
    walking_minutes: Optional[float] = None
    centroid: Optional[GeoPoint] = None
    area_pixels: Optional[int] = None
    source: str = "cv_detection"


class SearchResult(BaseModel):
    id: Optional[int] = None
    address: str
    city: str = "Москва"
    center_coords: Optional[GeoPoint] = None
    map_zoom: Optional[int] = None
    green_zones: list[GreenZone] = Field(default_factory=list)
    searched_at: datetime = Field(default_factory=datetime.now)
    screenshot_path: Optional[str] = None
    status: str = "pending"


class AddressInput(BaseModel):
    address: str
    city: str = "Москва"
