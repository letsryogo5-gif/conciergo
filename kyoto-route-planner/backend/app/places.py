from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException

from app.models import Origin, Place, Theme


ORIGINS = [
    Origin(name="京都", latitude=34.98585, longitude=135.75877),
]


def list_origins() -> list[Origin]:
    return ORIGINS.copy()


def _distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    latitude_delta = radians(second[0] - first[0])
    longitude_delta = radians(second[1] - first[1])
    first_latitude = radians(first[0])
    second_latitude = radians(second[0])
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 6371.0 * 2 * asin(sqrt(haversine))


MIN_ORIGIN_DISTANCE_KM = 0.3
MIN_STOP_SEPARATION_KM = 0.5


def choose_places(
    theme: Theme,
    stop_count: int,
    origin_name: str,
    candidates: list[Place],
) -> list[Place]:
    origin = next((item for item in ORIGINS if item.name == origin_name), None)
    if origin is None:
        raise ValueError("出発駅を選び直してください。")

    remaining = [
        place
        for place in candidates
        if place.themes and (theme == "all" or theme in place.themes)
    ]
    if theme == "all":
        sightseeing = [
            place
            for place in remaining
            if set(place.themes) & {"history", "temple", "nature"}
        ]
        if len(sightseeing) >= stop_count:
            remaining = sightseeing
    if not remaining:
        raise ValueError("OpenStreetMapの取得データに選択したテーマの候補がありません。")

    selected: list[Place] = []
    current = (origin.latitude, origin.longitude)
    while len(selected) < stop_count:
        eligible = [
            place
            for place in remaining
            if (
                selected
                or _distance_km(
                    (origin.latitude, origin.longitude),
                    (place.latitude, place.longitude),
                ) >= MIN_ORIGIN_DISTANCE_KM
            )
            and all(
                _distance_km(
                    (selected_place.latitude, selected_place.longitude),
                    (place.latitude, place.longitude),
                ) >= MIN_STOP_SEPARATION_KM
                for selected_place in selected
            )
        ]
        if not eligible:
            break
        closest = min(
            eligible,
            key=lambda place: _distance_km(
                current,
                (place.latitude, place.longitude),
            ),
        )
        selected.append(closest)
        remaining.remove(closest)
        current = (closest.latitude, closest.longitude)

    if len(selected) < stop_count:
        raise HTTPException(
            status_code=422,
            detail=(
                f"OpenStreetMapの取得データから立ち寄り先が{len(selected)}件しか見つかりませんでした。"
                "出発駅や他の立ち寄り先に近すぎる地点は除外しています。"
                "立ち寄り件数またはテーマを変更してください。"
            ),
        )

    return selected
