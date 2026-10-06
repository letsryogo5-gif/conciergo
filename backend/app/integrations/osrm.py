import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypedDict

import httpx

from app.models import RouteCoordinate, RouteDay, RoutePlan, RouteStop

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
OSRM_USER_AGENT = os.getenv("OSRM_USER_AGENT", "YorimichiTravelPlanner/1.0")
CACHE_TTL_SECONDS = 600
MINIMUM_REQUEST_INTERVAL_SECONDS = 1.0


class OSRMUnavailable(Exception):
    pass


class _Waypoint(TypedDict):
    waypoint_index: int


class _Leg(TypedDict):
    duration: float
    distance: float


@dataclass(frozen=True)
class _TripData:
    waypoints: list[_Waypoint]
    legs: list[_Leg]
    coordinates: list[list[float]]


class OSRMService:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        minimum_request_interval: float = MINIMUM_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers={"User-Agent": OSRM_USER_AGENT},
            transport=transport,
        )
        self._base_url = OSRM_BASE_URL.rstrip("/")
        self._clock = clock
        self._sleep = sleep
        self._minimum_request_interval = minimum_request_interval
        self._request_lock = asyncio.Lock()
        self._last_request_at: float | None = None
        self._cache: dict[tuple[tuple[float, float], ...], tuple[float, _TripData]] = {}

    async def __aenter__(self) -> "OSRMService":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def apply_to_plan(self, plan: RoutePlan) -> RoutePlan:
        days: list[RouteDay] = []
        total_travel_minutes = 0
        for day in plan.days:
            routed_day = await self._route_day(day)
            days.append(routed_day)
            total_travel_minutes += sum(
                stop.travel_minutes_from_previous for stop in routed_day.stops
            )

        occasion_note = (
            f"{plan.occasion.name}（開催目安：{plan.occasion.best_time}）に合わせた提案です。"
            if plan.occasion
            else ""
        )
        note = (
            f"{occasion_note}訪問順とスポット間の自動車ルート、距離・所要時間はOSRMの道路網データに基づく目安です。"
            "道路状況や通行規制、フェリー・公共交通、スポットの営業時間は反映していません。"
            "写真・紹介情報と滞在時間はサンプルです。"
        )
        return plan.model_copy(
            update={
                "algorithm": "osrm_trip",
                "days": days,
                "total_estimated_travel_minutes": total_travel_minutes,
                "note": note,
            }
        )

    async def _route_day(self, day: RouteDay) -> RouteDay:
        stops = day.stops
        coordinates = [
            (stop.spot.longitude, stop.spot.latitude)
            for stop in stops
        ]
        if len(stops) < 2:
            return day.model_copy(
                update={
                    "route_coordinates": [
                        RouteCoordinate(
                            latitude=stops[0].spot.latitude,
                            longitude=stops[0].spot.longitude,
                        )
                    ]
                    if stops
                    else []
                }
            )

        route_data = await self._trip(coordinates)
        waypoints = route_data.waypoints
        legs = route_data.legs
        geometry = route_data.coordinates
        if len(waypoints) != len(stops) or len(legs) != len(stops) - 1:
            raise OSRMUnavailable("経路サービスから不完全なルートが返されました。")
        if len(geometry) < 2:
            raise OSRMUnavailable("経路サービスから道路形状が返されませんでした。")

        indexed_stops: list[tuple[int, RouteStop]] = []
        try:
            for stop, waypoint in zip(stops, waypoints, strict=True):
                visit_index = int(waypoint["waypoint_index"])
                indexed_stops.append((visit_index, stop))
            indexed_stops.sort(key=lambda item: item[0])
            if [index for index, _ in indexed_stops] != list(range(len(stops))):
                raise ValueError("Invalid OSRM waypoint order")

            ordered_stops: list[RouteStop] = []
            current_time = day.start_time
            for index, (_, stop) in enumerate(indexed_stops):
                travel_minutes = 0
                distance_km = 0.0
                if index > 0:
                    leg = legs[index - 1]
                    travel_minutes = round(float(leg["duration"]) / 60)
                    distance_km = round(float(leg["distance"]) / 1000, 1)
                    current_time = _add_minutes(current_time, travel_minutes)
                arrival_time = current_time
                departure_time = _add_minutes(arrival_time, stop.visit_minutes)
                ordered_stops.append(
                    stop.model_copy(
                        update={
                            "arrival_time": arrival_time,
                            "departure_time": departure_time,
                            "travel_minutes_from_previous": travel_minutes,
                            "distance_km_from_previous": distance_km,
                        }
                    )
                )
                current_time = departure_time

            route_coordinates = [
                RouteCoordinate(latitude=float(point[1]), longitude=float(point[0]))
                for point in geometry
            ]
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise OSRMUnavailable("経路サービスから不正な距離・所要時間が返されました。") from error

        return day.model_copy(
            update={
                "stops": ordered_stops,
                "end_time": current_time,
                "route_coordinates": route_coordinates,
            }
        )

    async def _trip(self, coordinates: list[tuple[float, float]]) -> _TripData:
        cache_key = tuple((round(longitude, 6), round(latitude, 6)) for longitude, latitude in coordinates)
        now = self._clock()
        cached = self._cache.get(cache_key)
        if cached is not None and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

        async with self._request_lock:
            now = self._clock()
            cached = self._cache.get(cache_key)
            if cached is not None and now - cached[0] < CACHE_TTL_SECONDS:
                return cached[1]
            if self._last_request_at is not None:
                wait_seconds = self._minimum_request_interval - (now - self._last_request_at)
                if wait_seconds > 0:
                    await self._sleep(wait_seconds)

            coordinate_text = ";".join(
                f"{longitude:.6f},{latitude:.6f}" for longitude, latitude in coordinates
            )
            self._last_request_at = self._clock()
            try:
                response = await self._client.get(
                    f"{self._base_url}/trip/v1/driving/{coordinate_text}",
                    params={
                        "source": "first",
                        "destination": "last",
                        "roundtrip": "false",
                        "geometries": "geojson",
                        "overview": "full",
                        "steps": "false",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or payload.get("code") != "Ok":
                    message = payload.get("message") if isinstance(payload, dict) else None
                    raise OSRMUnavailable(
                        f"経路サービスがルートを作成できませんでした{f'：{message}' if message else '。'}"
                    )
                trips = payload.get("trips")
                waypoints = payload.get("waypoints")
                trip = trips[0] if isinstance(trips, list) and trips else None
                geometry = trip.get("geometry") if isinstance(trip, dict) else None
                legs = trip.get("legs") if isinstance(trip, dict) else None
                coordinates_result = geometry.get("coordinates") if isinstance(geometry, dict) else None
                if not isinstance(waypoints, list) or not isinstance(legs, list) or not isinstance(coordinates_result, list):
                    raise OSRMUnavailable("経路サービスから不正なルートが返されました。")
                data = _TripData(
                    waypoints=[
                        {"waypoint_index": int(waypoint["waypoint_index"])}
                        for waypoint in waypoints
                        if isinstance(waypoint, dict)
                    ],
                    legs=[
                        {
                            "duration": float(leg["duration"]),
                            "distance": float(leg["distance"]),
                        }
                        for leg in legs
                        if isinstance(leg, dict)
                    ],
                    coordinates=[
                        [float(point[0]), float(point[1])]
                        for point in coordinates_result
                        if isinstance(point, list) and len(point) >= 2
                    ],
                )
                if (
                    len(data.waypoints) != len(waypoints)
                    or len(data.legs) != len(legs)
                    or len(data.coordinates) != len(coordinates_result)
                ):
                    raise ValueError("Invalid OSRM route data")
            except OSRMUnavailable:
                raise
            except httpx.HTTPStatusError as error:
                raise OSRMUnavailable(
                    f"経路サービスがエラーを返しました (HTTP {error.response.status_code})。"
                ) from error
            except httpx.TimeoutException as error:
                raise OSRMUnavailable("経路サービスが時間内に応答しませんでした。") from error
            except httpx.RequestError as error:
                raise OSRMUnavailable("経路サービスに接続できませんでした。") from error
            except (KeyError, TypeError, ValueError) as error:
                raise OSRMUnavailable("経路サービスから不正な応答がありました。") from error

            self._cache[cache_key] = (self._clock(), data)
            return data


def _add_minutes(time_text: str, minutes: int) -> str:
    hours, remainder = divmod(minutes, 60)
    start_hour, start_minute = (int(part) for part in time_text.split(":"))
    total_minutes = (start_hour * 60 + start_minute + hours * 60 + remainder) % (24 * 60)
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"
