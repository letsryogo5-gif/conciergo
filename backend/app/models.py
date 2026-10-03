from pydantic import BaseModel, Field, field_validator


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
    is_world_heritage: bool = False
    heritage_name: str | None = None


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


class RouteDay(BaseModel):
    day_number: int
    title: str
    start_time: str
    end_time: str
    stops: list[RouteStop]


class RoutePlan(BaseModel):
    sample_mode: bool
    algorithm: str
    days: list[RouteDay]
    total_spots: int
    total_estimated_travel_minutes: int
    note: str
    occasion: LocalEvent | None = None
    added_spot_ids: list[str] = Field(default_factory=list)
