import random

from app.models import Spot
from app.sample_data import SPOTS


def discover_spots(
    category: str | None = None,
    region: str | None = None,
    limit: int = 30,
    random_order: bool = False,
    event_spot_ids: set[str] | None = None,
) -> tuple[list[Spot], list[str], list[str], int]:
    categorized = [
        (
            spot,
            set(spot.discovery_categories)
            | {spot.category}
            | ({"世界遺産"} if spot.is_world_heritage else set())
            | ({"年中行事"} if event_spot_ids and spot.id in event_spot_ids else set()),
        )
        for spot in SPOTS
    ]
    categories = sorted({label for _, labels in categorized for label in labels})
    regions = sorted({spot.prefecture for spot in SPOTS})
    matches = [
        spot for spot, labels in categorized
        if (category is None or category in labels)
        and (region is None or region == spot.prefecture)
    ]
    total = len(matches)
    if random_order:
        random.SystemRandom().shuffle(matches)
    return matches[:limit], categories, regions, total


def list_sample_spots() -> list[Spot]:
    return SPOTS.copy()


def get_sample_spot(spot_id: str) -> Spot | None:
    return next((spot for spot in SPOTS if spot.id == spot_id), None)
