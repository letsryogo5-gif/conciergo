import asyncio
import os
import time
from collections.abc import Awaitable, Callable

import httpx
from pydantic import ValidationError

from app.models import GeocodingResult

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "YorimichiTravelPlanner/1.0")
CACHE_TTL_SECONDS = 3600
MINIMUM_REQUEST_INTERVAL_SECONDS = 1.0


class NominatimUnavailable(Exception):
    pass


class NominatimService:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        minimum_request_interval: float = MINIMUM_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=4.0),
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        )
        self._clock = clock
        self._sleep = sleep
        self._minimum_request_interval = minimum_request_interval
        self._request_lock = asyncio.Lock()
        self._last_request_at: float | None = None
        self._cache: dict[str, tuple[float, list[GeocodingResult]]] = {}

    async def __aenter__(self) -> "NominatimService":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 5) -> list[GeocodingResult]:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("地名を入力してください。")

        cache_key = normalized_query.casefold()
        now = self._clock()
        cached = self._cache.get(cache_key)
        if cached is not None and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1].copy()

        async with self._request_lock:
            now = self._clock()
            cached = self._cache.get(cache_key)
            if cached is not None and now - cached[0] < CACHE_TTL_SECONDS:
                return cached[1].copy()

            if self._last_request_at is not None:
                wait_seconds = self._minimum_request_interval - (now - self._last_request_at)
                if wait_seconds > 0:
                    await self._sleep(wait_seconds)

            self._last_request_at = self._clock()
            try:
                response = await self._client.get(
                    NOMINATIM_SEARCH_URL,
                    params={
                        "q": normalized_query,
                        "format": "jsonv2",
                        "limit": limit,
                        "countrycodes": "jp",
                        "accept-language": "ja,en",
                        "addressdetails": 0,
                    },
                )
                response.raise_for_status()
                items = response.json()
                if not isinstance(items, list):
                    raise NominatimUnavailable("地名検索サービスから不正な応答がありました。")
                results = [
                    GeocodingResult(
                        place_id=int(item["place_id"]),
                        display_name=str(item["display_name"]),
                        latitude=float(item["lat"]),
                        longitude=float(item["lon"]),
                        category=str(item.get("category", "")),
                        place_type=str(item.get("type", "")),
                    )
                    for item in items
                ]
            except httpx.HTTPStatusError as error:
                raise NominatimUnavailable(
                    f"地名検索サービスがエラーを返しました (HTTP {error.response.status_code})。"
                ) from error
            except httpx.TimeoutException as error:
                raise NominatimUnavailable("地名検索サービスが時間内に応答しませんでした。") from error
            except httpx.RequestError as error:
                raise NominatimUnavailable("地名検索サービスに接続できませんでした。") from error
            except (KeyError, TypeError, ValueError, ValidationError) as error:
                raise NominatimUnavailable("地名検索サービスから不正な位置情報が返されました。") from error

            self._cache[cache_key] = (self._clock(), results)
            return results.copy()
