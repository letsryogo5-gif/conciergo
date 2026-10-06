import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

import httpx

from app.integrations.pexels import PexelsClient
from app.integrations.pixabay import MediaProviderUnavailable, PixabayClient
from app.models import MediaAsset, MediaProviderName, MediaProviderStatus, MediaType, SpotMediaResults

LOGGER = logging.getLogger(__name__)
PIXABAY_CACHE_TTL_SECONDS = 86_400
PEXELS_CACHE_TTL_SECONDS = 3_600
PARTIAL_FAILURE_CACHE_TTL_SECONDS = 300


class HybridMediaService:
    def __init__(
        self,
        pixabay_api_key: str | None = None,
        pexels_api_key: str | None = None,
        pixabay_transport: httpx.AsyncBaseTransport | None = None,
        pexels_transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.pixabay = PixabayClient(pixabay_api_key, transport=pixabay_transport)
        self.pexels = PexelsClient(pexels_api_key, transport=pexels_transport)
        self._clock = clock
        self._cache: dict[
            tuple[str, str, int],
            tuple[float, SpotMediaResults],
        ] = {}
        self._locks: dict[tuple[str, str, int], asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()

    async def __aenter__(self) -> "HybridMediaService":
        await self.pixabay.__aenter__()
        await self.pexels.__aenter__()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.pixabay.__aexit__()
        await self.pexels.__aexit__()

    async def search(
        self,
        *,
        spot_id: str,
        query: str,
        media_type: MediaType,
        fallback_url: str,
        limit: int = 8,
    ) -> SpotMediaResults:
        normalized_query = " ".join(query.split())
        if len(normalized_query) < 2:
            raise ValueError("メディア検索語は2文字以上必要です。")
        if not 1 <= limit <= 30:
            raise ValueError("メディア検索件数は1〜30件で指定してください。")
        cache_key = (normalized_query.casefold(), media_type, limit)

        async with self._locks_guard:
            lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(cache_key)
            now = self._clock()
            if cached is not None and now - cached[0] < self._cache_ttl(cached[1]):
                cached_result = cached[1]
                return cached_result.model_copy(update={"spot_id": spot_id, "fallback_url": fallback_url})

            result = await self._search_uncached(
                spot_id=spot_id,
                query=normalized_query,
                media_type=media_type,
                fallback_url=fallback_url,
                limit=limit,
            )
            self._cache[cache_key] = (self._clock(), result)
            return result

    def _cache_ttl(self, result: SpotMediaResults) -> int:
        if any(provider.status == "unavailable" for provider in result.providers):
            return PARTIAL_FAILURE_CACHE_TTL_SECONDS
        if result.source == "local_sample":
            return PARTIAL_FAILURE_CACHE_TTL_SECONDS
        if self.pexels.configured:
            return PEXELS_CACHE_TTL_SECONDS
        return PIXABAY_CACHE_TTL_SECONDS

    async def _search_uncached(
        self,
        *,
        spot_id: str,
        query: str,
        media_type: MediaType,
        fallback_url: str,
        limit: int,
    ) -> SpotMediaResults:
        providers: list[
            tuple[
                MediaProviderName,
                Callable[[str, MediaType, int], Awaitable[list[MediaAsset]]],
                bool,
            ]
        ] = [
            ("pixabay", self.pixabay.search, self.pixabay.configured),
            ("pexels", self.pexels.search, self.pexels.configured),
        ]
        configured = [provider for provider in providers if provider[2]]
        tasks = [
            provider[1](query, media_type, limit)
            for provider in configured
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        assets: list[MediaAsset] = []
        statuses: list[MediaProviderStatus] = []
        for (provider_name, _, _), outcome in zip(configured, outcomes):
            if isinstance(outcome, MediaProviderUnavailable):
                LOGGER.warning("%s media search failed; continuing with other sources: %s", provider_name, outcome)
                statuses.append(
                    MediaProviderStatus(
                        provider=provider_name,
                        status="unavailable",
                        result_count=0,
                    )
                )
                continue
            if isinstance(outcome, BaseException):
                raise outcome

            assets.extend(outcome)
            statuses.append(
                MediaProviderStatus(
                    provider=provider_name,
                    status="available" if outcome else "empty",
                    result_count=len(outcome),
                )
            )

        for provider_name, _, is_configured in providers:
            if not is_configured:
                statuses.append(
                    MediaProviderStatus(
                        provider=provider_name,
                        status="not_configured",
                        result_count=0,
                    )
                )

        deduplicated: list[MediaAsset] = []
        seen_urls: set[str] = set()
        for asset in assets:
            if asset.url in seen_urls:
                continue
            seen_urls.add(asset.url)
            deduplicated.append(asset)
        deduplicated = deduplicated[:limit]
        return SpotMediaResults(
            spot_id=spot_id,
            query=query,
            media_type=media_type,
            source="providers" if deduplicated else "local_sample",
            items=deduplicated,
            fallback_url=fallback_url,
            providers=statuses,
        )
