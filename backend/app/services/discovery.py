from app.models import Spot
from app.sample_data import SPOTS


def list_sample_spots() -> list[Spot]:
    return SPOTS.copy()


def get_sample_spot(spot_id: str) -> Spot | None:
    return next((spot for spot in SPOTS if spot.id == spot_id), None)
