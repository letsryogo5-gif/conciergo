from typing import Literal

from pydantic import BaseModel, Field, field_validator

MediaType = Literal["image", "video"]
MediaProviderName = Literal["pixabay", "pexels"]
CatalogDataStatus = Literal["sample", "sourced"]


class SourceReference(BaseModel):
    publisher: str
    title: str
    url: str
    verified_fields: list[str] = Field(default_factory=list)
    license_name: str | None = None
    license_url: str | None = None


class Spot(BaseModel):
    id: str
    region: str
    prefecture: str
    title: str
    description: str
    image_url: str
    video_url: str | None = None
    category: str
    local_food: str
    local_species: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    tags: list[str]
    creator: str
    likes: int = Field(ge=0)
    local_trivia: str
    discovery_categories: list[str] = Field(default_factory=list)
    is_world_heritage: bool = False
    heritage_name: str | None = None
    wikipedia_query: str | None = None
    data_status: CatalogDataStatus = "sample"
    sources: list[SourceReference] = Field(default_factory=list)


class GeocodingResult(BaseModel):
    place_id: int
    display_name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category: str
    place_type: str


class WikipediaSummary(BaseModel):
    title: str
    extract: str
    article_url: str


class MediaAsset(BaseModel):
    id: str
    media_type: Literal["image", "video"]
    url: str
    preview_url: str
    page_url: str
    source: MediaProviderName
    description: str
    duration_seconds: int | None = Field(default=None, ge=0)
    creator: str | None = None


class MediaProviderStatus(BaseModel):
    provider: MediaProviderName
    status: Literal["not_configured", "available", "unavailable", "empty"]
    result_count: int = Field(ge=0)


class SpotMediaResults(BaseModel):
    spot_id: str
    query: str
    media_type: Literal["image", "video"]
    source: Literal["providers", "local_sample"]
    items: list[MediaAsset]
    fallback_url: str
    providers: list[MediaProviderStatus]


class SpotDiscoveryResults(BaseModel):
    items: list[Spot]
    categories: list[str]
    regions: list[str]
    total: int = Field(ge=0)
    source: str = "sample_catalog"


class LocalEvent(BaseModel):
    id: str
    spot_id: str
    name: str
    region: str
    description: str
    image_url: str
    start_month: int = Field(ge=1, le=12)
    end_month: int = Field(ge=1, le=12)
    best_time: str
    category: str
    data_status: CatalogDataStatus = "sample"
    sources: list[SourceReference] = Field(default_factory=list)


class MemoryCoordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    spot_id: str
    label: str


class MemoryPhoto(BaseModel):
    id: str
    image_url: str
    caption: str
    captured_at: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    spot_id: str


class TravelMemory(BaseModel):
    id: str
    title: str
    region: str
    visited_at: str
    note: str
    route: list[MemoryCoordinate]
    photos: list[MemoryPhoto]


class ModelCourse(BaseModel):
    id: str
    title: str
    description: str
    region: str
    creator: str
    image_url: str
    spot_ids: list[str]
    likes: int = Field(ge=0)


class ModelCourseRequest(BaseModel):
    title: str = Field(min_length=3, max_length=90)
    description: str = Field(min_length=1, max_length=500)
    region: str = Field(min_length=1, max_length=80)
    creator: str = Field(default="よりみちユーザー", min_length=1, max_length=40)
    spot_ids: list[str] = Field(min_length=1, max_length=30)

    @field_validator("spot_ids")
    @classmethod
    def spot_ids_must_be_unique(cls, spot_ids: list[str]) -> list[str]:
        if len(set(spot_ids)) != len(spot_ids):
            raise ValueError("スポット ID を重複して指定できません。")
        return spot_ids


class AppStatus(BaseModel):
    sample_mode: bool
    services: dict[str, str]


class RouteRequest(BaseModel):
    spot_ids: list[str] = Field(min_length=1, max_length=30)
    event_id: str | None = None

    @field_validator("spot_ids")
    @classmethod
    def spot_ids_must_be_unique(cls, spot_ids: list[str]) -> list[str]:
        if len(set(spot_ids)) != len(spot_ids):
            raise ValueError("スポット ID を重複して指定できません。")
        return spot_ids


class RouteStop(BaseModel):
    arrival_time: str
    departure_time: str
    visit_minutes: int
    travel_minutes_from_previous: int
    distance_km_from_previous: float
    spot: Spot


class RouteCoordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteDay(BaseModel):
    day_number: int
    title: str
    start_time: str
    end_time: str
    stops: list[RouteStop]
    route_coordinates: list[RouteCoordinate] = Field(default_factory=list)


class RoutePlan(BaseModel):
    sample_mode: bool
    algorithm: str
    days: list[RouteDay]
    total_spots: int
    total_estimated_travel_minutes: int
    note: str
    occasion: LocalEvent | None = None
    added_spot_ids: list[str] = Field(default_factory=list)
