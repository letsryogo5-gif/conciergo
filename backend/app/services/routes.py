from app.models import LocalEvent, RouteDay, RoutePlan, RouteRequest, RouteStop, Spot
from app.route_sample_data import SAMPLE_ROUTE_NOTE, SAMPLE_ROUTE_SETTINGS

EARTH_RADIUS_KM = 6371.0


def _great_circle_distance_km(first: Spot, second: Spot) -> float:
    return _great_circle_distance_coordinates(
        (first.latitude, first.longitude),
        (second.latitude, second.longitude),
    )


def _great_circle_distance_coordinates(
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    from math import asin, cos, radians, sin, sqrt

    latitude_delta = radians(second[0] - first[0])
    longitude_delta = radians(second[1] - first[1])
    first_latitude = radians(first[0])
    second_latitude = radians(second[0])
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * asin(sqrt(haversine))


def _cluster_by_proximity(spots: list[Spot]) -> list[list[Spot]]:
    clusters: list[list[Spot]] = []
    radius = SAMPLE_ROUTE_SETTINGS["day_cluster_radius_km"]
    max_stops = SAMPLE_ROUTE_SETTINGS["max_stops_per_day"]

    for spot in spots:
        candidates = [
            (index, min(_great_circle_distance_km(spot, member) for member in cluster))
            for index, cluster in enumerate(clusters)
            if len(cluster) < max_stops
        ]
        nearest = min(candidates, key=lambda candidate: candidate[1], default=None)
        if nearest is not None and nearest[1] <= radius:
            clusters[nearest[0]].append(spot)
        else:
            clusters.append([spot])
    return clusters


def _centroid(cluster: list[Spot]) -> tuple[float, float]:
    return (
        sum(spot.latitude for spot in cluster) / len(cluster),
        sum(spot.longitude for spot in cluster) / len(cluster),
    )


def _order_clusters(clusters: list[list[Spot]]) -> list[list[Spot]]:
    if len(clusters) < 2:
        return clusters

    remaining = clusters.copy()
    current = max(remaining, key=lambda cluster: _centroid(cluster)[0])
    ordered = [current]
    remaining.remove(current)

    while remaining:
        current_center = _centroid(current)
        current = min(
            remaining,
            key=lambda cluster: _great_circle_distance_coordinates(
                current_center,
                _centroid(cluster),
            ),
        )
        ordered.append(current)
        remaining.remove(current)
    return ordered


def _order_stops(cluster: list[Spot]) -> list[Spot]:
    if len(cluster) < 2:
        return cluster

    remaining = cluster.copy()
    current = min(remaining, key=lambda spot: (spot.latitude, spot.longitude))
    ordered = [current]
    remaining.remove(current)
    while remaining:
        current = min(remaining, key=lambda spot: _great_circle_distance_km(ordered[-1], spot))
        ordered.append(current)
        remaining.remove(current)
    return ordered


def _add_minutes(time_text: str, minutes: int) -> str:
    hours, remainder = divmod(minutes, 60)
    start_hour, start_minute = (int(part) for part in time_text.split(":"))
    total_minutes = (start_hour * 60 + start_minute + hours * 60 + remainder) % (24 * 60)
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def _travel_minutes(distance_km: float) -> int:
    estimated_distance = distance_km * SAMPLE_ROUTE_SETTINGS["distance_detour_factor"]
    driving_minutes = estimated_distance / SAMPLE_ROUTE_SETTINGS["average_speed_kmh"] * 60
    return round(driving_minutes + SAMPLE_ROUTE_SETTINGS["transfer_buffer_minutes"])


def create_sample_route(
    request: RouteRequest,
    available_spots: list[Spot],
    events: list[LocalEvent] | None = None,
) -> RoutePlan:
    spots_by_id = {spot.id: spot for spot in available_spots}
    missing_ids = [spot_id for spot_id in request.spot_ids if spot_id not in spots_by_id]
    if missing_ids:
        raise ValueError(f"スポットが見つかりません: {', '.join(missing_ids)}")

    requested_spots = [spots_by_id[spot_id] for spot_id in request.spot_ids]
    occasion = None
    added_spot_ids: list[str] = []
    if request.event_id:
        occasion = next(
            (event for event in (events or []) if event.id == request.event_id),
            None,
        )
        if occasion is None:
            raise ValueError(f"イベントが見つかりません: {request.event_id}")
        event_spot = spots_by_id.get(occasion.spot_id)
        if event_spot is None:
            raise ValueError(f"イベントの関連スポットが見つかりません: {occasion.spot_id}")
        nearby_radius = SAMPLE_ROUTE_SETTINGS["day_cluster_radius_km"]
        for candidate in available_spots:
            if candidate.id in {spot.id for spot in requested_spots}:
                continue
            distance = _great_circle_distance_km(event_spot, candidate)
            is_local_interest = candidate.is_world_heritage or bool(candidate.local_trivia)
            if distance <= nearby_radius and is_local_interest:
                requested_spots.append(candidate)
                added_spot_ids.append(candidate.id)

    clusters = _order_clusters(_cluster_by_proximity(requested_spots))
    days: list[RouteDay] = []
    total_travel_minutes = 0

    for day_number, cluster in enumerate(clusters, start=1):
        ordered_spots = _order_stops(cluster)
        current_time = SAMPLE_ROUTE_SETTINGS["day_start_time"]
        previous_spot: Spot | None = None
        stops: list[RouteStop] = []

        for spot in ordered_spots:
            distance_km = (
                _great_circle_distance_km(previous_spot, spot)
                if previous_spot is not None
                else 0.0
            )
            travel_minutes = _travel_minutes(distance_km) if previous_spot is not None else 0
            arrival_time = _add_minutes(current_time, travel_minutes)
            departure_time = _add_minutes(arrival_time, SAMPLE_ROUTE_SETTINGS["visit_minutes"])
            stops.append(
                RouteStop(
                    arrival_time=arrival_time,
                    departure_time=departure_time,
                    visit_minutes=SAMPLE_ROUTE_SETTINGS["visit_minutes"],
                    travel_minutes_from_previous=travel_minutes,
                    distance_km_from_previous=round(distance_km, 1),
                    spot=spot,
                )
            )
            current_time = departure_time
            previous_spot = spot
            total_travel_minutes += travel_minutes

        first_spot = ordered_spots[0]
        title = f"{first_spot.prefecture}をめぐる日"
        if len(ordered_spots) > 1:
            title = f"{first_spot.prefecture}・近郊をめぐる日"
        days.append(
            RouteDay(
                day_number=day_number,
                title=title,
                start_time=SAMPLE_ROUTE_SETTINGS["day_start_time"],
                end_time=current_time,
                stops=stops,
            )
        )

    return RoutePlan(
        sample_mode=True,
        algorithm="sample_proximity_nearest_neighbor",
        days=days,
        total_spots=len(requested_spots),
        total_estimated_travel_minutes=total_travel_minutes,
        note=(
            f"{occasion.name}（開催目安：{occasion.best_time}）に合わせたサンプル提案です。"
            f"{SAMPLE_ROUTE_NOTE}"
            if occasion
            else SAMPLE_ROUTE_NOTE
        ),
        occasion=occasion,
        added_spot_ids=added_spot_ids,
    )
