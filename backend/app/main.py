from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from app.integrations import google_maps, social
from app.integrations.hybrid_media import HybridMediaService
from app.integrations.nominatim import NominatimService, NominatimUnavailable
from app.integrations.osrm import OSRMService, OSRMUnavailable
from app.integrations.wikipedia import WikipediaService, WikipediaUnavailable
from app.event_sample_data import SAMPLE_EVENTS
from app.memory_sample_data import SAMPLE_MEMORIES
from app.models import AppStatus, GeocodingResult, LocalEvent, MediaType, ModelCourse, ModelCourseRequest, RoutePlan, RouteRequest, Spot, SpotDiscoveryResults, SpotMediaResults, TravelMemory, WikipediaSummary
from app.sample_data import SAMPLE_MODE
from app.services.discovery import discover_spots, get_sample_spot, list_sample_spots
from app.services.model_courses import list_model_courses, publish_model_course
from app.services.routes import create_sample_route

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    async with (
        NominatimService() as geocoder,
        OSRMService() as osrm,
        WikipediaService() as wikipedia,
        HybridMediaService() as media,
    ):
        application.state.geocoder = geocoder
        application.state.osrm = osrm
        application.state.wikipedia = wikipedia
        application.state.media = media
        yield


app = FastAPI(title="よりみち | 地域の魅力発見", version="1.0.0", lifespan=lifespan)
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


@app.get("/api/discover/spots", response_model=SpotDiscoveryResults)
def discover_spot_candidates(
    category: str | None = Query(default=None, min_length=1, max_length=40),
    region: str | None = Query(default=None, min_length=1, max_length=40),
    limit: int = Query(default=30, ge=1, le=100),
    random_order: bool = Query(default=False),
) -> SpotDiscoveryResults:
    items, categories, regions, total = discover_spots(
        category=category,
        region=region,
        limit=limit,
        random_order=random_order,
        event_spot_ids={event.spot_id for event in SAMPLE_EVENTS},
    )
    if category is not None and category not in categories:
        raise HTTPException(status_code=422, detail="指定されたカテゴリは見つかりません。")
    if region is not None and region not in regions:
        raise HTTPException(status_code=422, detail="指定された地域は見つかりません。")
    return SpotDiscoveryResults(items=items, categories=categories, regions=regions, total=total)


@app.get("/api/spots/{spot_id}", response_model=Spot)
def spot(spot_id: str) -> Spot:
    result = get_sample_spot(spot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="スポットが見つかりません。")
    return result


@app.get("/api/spots/{spot_id}/media", response_model=SpotMediaResults)
async def spot_media(
    spot_id: str,
    request: Request,
    media_type: MediaType = Query(default="image"),
    limit: int = Query(default=8, ge=1, le=30),
) -> SpotMediaResults:
    result = get_sample_spot(spot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="スポットが見つかりません。")
    query = " ".join([result.prefecture, result.region.split(",")[0], *result.tags[:2]])
    return await request.app.state.media.search(
        spot_id=result.id,
        query=query,
        media_type=media_type,
        fallback_url=result.image_url,
        limit=limit,
    )


@app.get("/api/spots/{spot_id}/knowledge", response_model=WikipediaSummary | None)
async def spot_knowledge(spot_id: str, request: Request) -> WikipediaSummary | None:
    result = get_sample_spot(spot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="スポットが見つかりません。")
    query = result.wikipedia_query or result.title
    try:
        return await request.app.state.wikipedia.search_summary(query)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except WikipediaUnavailable as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/geocode", response_model=list[GeocodingResult])
async def geocode(
    request: Request,
    q: str = Query(min_length=2, max_length=120),
) -> list[GeocodingResult]:
    try:
        return await request.app.state.geocoder.search(q, limit=5)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except NominatimUnavailable as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/events", response_model=list[LocalEvent])
def events() -> list[LocalEvent]:
    return SAMPLE_EVENTS.copy()


@app.get("/api/memories", response_model=list[TravelMemory])
def memories() -> list[TravelMemory]:
    return SAMPLE_MEMORIES.copy()


@app.get("/api/model-courses", response_model=list[ModelCourse])
def model_courses() -> list[ModelCourse]:
    return list_model_courses()


@app.post("/api/model-courses", response_model=ModelCourse, status_code=201)
def create_model_course(request: ModelCourseRequest) -> ModelCourse:
    try:
        return publish_model_course(request, list_sample_spots())
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/routes", response_model=RoutePlan)
async def route(request: RouteRequest, http_request: Request) -> RoutePlan:
    try:
        plan = create_sample_route(request, list_sample_spots(), SAMPLE_EVENTS)
        return await http_request.app.state.osrm.apply_to_plan(plan)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except OSRMUnavailable as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
