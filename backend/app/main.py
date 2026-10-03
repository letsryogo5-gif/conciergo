from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.integrations import google_maps, social
from app.event_sample_data import SAMPLE_EVENTS
from app.models import AppStatus, LocalEvent, RoutePlan, RouteRequest, Spot
from app.sample_data import SAMPLE_MODE
from app.services.discovery import get_sample_spot, list_sample_spots
from app.services.routes import create_sample_route

app = FastAPI(title="よりみち | 地域の魅力発見", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status", response_model=AppStatus)
def status() -> AppStatus:
    return AppStatus(
        sample_mode=SAMPLE_MODE,
        services={
            "google_maps": google_maps.STATUS,
            "social": social.STATUS,
        },
    )


@app.get("/api/spots", response_model=list[Spot])
def spots() -> list[Spot]:
    return list_sample_spots()


@app.get("/api/spots/{spot_id}", response_model=Spot)
def spot(spot_id: str) -> Spot:
    result = get_sample_spot(spot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="スポットが見つかりません。")
    return result


@app.get("/api/events", response_model=list[LocalEvent])
def events() -> list[LocalEvent]:
    return SAMPLE_EVENTS.copy()


@app.post("/api/routes", response_model=RoutePlan)
def route(request: RouteRequest) -> RoutePlan:
    try:
        return create_sample_route(request, list_sample_spots(), SAMPLE_EVENTS)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
