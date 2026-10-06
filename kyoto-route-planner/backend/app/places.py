from math import asin, cos, radians, sin, sqrt

from app.models import Origin, Place, Theme


ORIGINS = [
    Origin(name="京都", latitude=34.98585, longitude=135.75877),
    Origin(name="四条", latitude=35.00375, longitude=135.76812),
    Origin(name="三条", latitude=35.00935, longitude=135.77154),
    Origin(name="嵯峨嵐山", latitude=35.01894, longitude=135.68108),
]

PLACES = [
    Place(
        id="fushimi-inari",
        name="伏見稲荷大社",
        category="神社・寺院",
        description="朱色の鳥居が連なる参道で知られる神社。",
        access_point="稲荷",
        latitude=34.96714,
        longitude=135.77267,
        themes=["temple", "nature"],
    ),
    Place(
        id="kiyomizu-dera",
        name="清水寺",
        category="神社・寺院",
        description="京都市街を望む舞台と歴史ある境内を訪ねます。",
        access_point="清水五条",
        latitude=34.99485,
        longitude=135.78505,
        themes=["history", "temple"],
    ),
    Place(
        id="kinkaku-ji",
        name="金閣寺",
        category="歴史・文化",
        description="池に映る舎利殿で知られる寺院。",
        access_point="北野白梅町",
        latitude=35.03937,
        longitude=135.72924,
        themes=["history", "temple"],
    ),
    Place(
        id="arashiyama-bamboo",
        name="嵐山 竹林の小径",
        category="自然・景色",
        description="竹林の間を歩く、嵐山エリアの散策路。",
        access_point="嵯峨嵐山",
        latitude=35.01750,
        longitude=135.67150,
        themes=["nature"],
    ),
    Place(
        id="nijo-castle",
        name="二条城",
        category="歴史・文化",
        description="二の丸御殿や庭園を見学できる城跡。",
        access_point="二条城前",
        latitude=35.01423,
        longitude=135.74820,
        themes=["history"],
    ),
    Place(
        id="nishiki-market",
        name="錦市場",
        category="食・商店街",
        description="食材や京の味を扱う店が並ぶ市場。",
        access_point="四条",
        latitude=35.00404,
        longitude=135.76400,
        themes=["food"],
    ),
    Place(
        id="yasaka-shrine",
        name="八坂神社",
        category="神社・寺院",
        description="祇園エリアにある神社。周辺散策の起点にも。",
        access_point="祇園四条",
        latitude=35.00363,
        longitude=135.77852,
        themes=["history", "temple"],
    ),
    Place(
        id="kyoto-gyoen",
        name="京都御苑",
        category="自然・景色",
        description="広い苑内で季節の景色を楽しめる公園。",
        access_point="丸太町",
        latitude=35.02132,
        longitude=135.76227,
        themes=["nature"],
    ),
    Place(
        id="to-ji",
        name="東寺",
        category="神社・寺院",
        description="五重塔で知られる寺院。京都駅からも訪れやすい場所です。",
        access_point="東寺",
        latitude=34.98052,
        longitude=135.74778,
        themes=["history", "temple"],
    ),
    Place(
        id="philosophers-path",
        name="哲学の道",
        category="自然・景色",
        description="疏水沿いを歩く散策路。",
        access_point="出町柳",
        latitude=35.02700,
        longitude=135.79820,
        themes=["nature"],
    ),
]


def list_places() -> list[Place]:
    return PLACES.copy()


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


def choose_places(theme: Theme, stop_count: int, origin_name: str) -> list[Place]:
    origin = next((item for item in ORIGINS if item.name == origin_name), None)
    if origin is None:
        raise ValueError("出発駅を選び直してください。")

    candidates = [
        place for place in PLACES
        if theme == "all" or theme in place.themes
    ]
    if not candidates:
        raise ValueError("選択したテーマの候補がありません。")

    selected: list[Place] = []
    current = (origin.latitude, origin.longitude)
    while candidates and len(selected) < stop_count:
        closest = min(
            candidates,
            key=lambda place: _distance_km(
                current,
                (place.latitude, place.longitude),
            ),
        )
        selected.append(closest)
        candidates.remove(closest)
        current = (closest.latitude, closest.longitude)

    return selected
