import asyncio
import os
import time
from collections.abc import Awaitable, Callable

import httpx
from pydantic import ValidationError

from app.models import WikipediaSummary

WIKIPEDIA_API_URL = "https://ja.wikipedia.org/w/api.php"
USER_AGENT = os.getenv("WIKIPEDIA_USER_AGENT", "YorimichiTravelPlanner/1.0")
CACHE_TTL_SECONDS = 86_400
MINIMUM_REQUEST_INTERVAL_SECONDS = 1.0


class WikipediaUnavailable(Exception):
    pass


class WikipediaService:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        minimum_request_interval: float = MINIMUM_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=5.0),
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        )
        self._clock = clock
        self._sleep = sleep
        self._minimum_request_interval = minimum_request_interval
        self._request_lock = asyncio.Lock()
        self._last_request_at: float | None = None
        self._cache: dict[str, tuple[float, WikipediaSummary | None]] = {}

    async def __aenter__(self) -> "WikipediaService":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def search_summary(self, query: str) -> WikipediaSummary | None:
        normalized_query = " ".join(query.split())
        if len(normalized_query) < 2:
            raise ValueError("Wikipediaの検索語は2文字以上必要です。")

        cache_key = normalized_query.casefold()
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

            self._last_request_at = self._clock()
            try:
                response = await self._client.get(
                    WIKIPEDIA_API_URL,
                    params={
                        "action": "query",
                        "generator": "search",
                        "gsrsearch": normalized_query,
                        "gsrlimit": 1,
                        "prop": "extracts|info",
                        "exintro": 1,
                        "explaintext": 1,
                        "exchars": 720,
                        "inprop": "url",
                        "format": "json",
                        "formatversion": 2,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise WikipediaUnavailable("Wikipediaから不正な概要データが返されました。")
                query_data = payload.get("query")
                if not isinstance(query_data, dict):
                    raise WikipediaUnavailable("Wikipediaから不正な概要データが返されました。")
                pages = query_data.get("pages", [])
                if not isinstance(pages, list):
                    raise WikipediaUnavailable("Wikipediaから不正な記事一覧が返されました。")
                if not pages:
                    summary = None
                else:
                    page = pages[0]
                    if not isinstance(page, dict):
                        raise WikipediaUnavailable("Wikipediaから不正な記事データが返されました。")
                    extract = page.get("extract")
                    article_url = page.get("fullurl")
                    title = page.get("title")
                    if not isinstance(extract, str) or not extract.strip():
                        summary = None
                    elif (
                        not isinstance(title, str)
                        or not title.strip()
                        or not isinstance(article_url, str)
                        or not article_url.startswith("https://ja.wikipedia.org/wiki/")
                    ):
                        raise WikipediaUnavailable("Wikipedia記事のリンクが正しくありません。")
                    else:
                        summary = WikipediaSummary(
                            title=title,
                            extract=extract.strip(),
                            article_url=article_url,
                        )
            except httpx.HTTPStatusError as error:
                raise WikipediaUnavailable(
                    f"Wikipediaがエラーを返しました (HTTP {error.response.status_code})。"
                ) from error
            except httpx.TimeoutException as error:
                raise WikipediaUnavailable("Wikipediaが時間内に応答しませんでした。") from error
            except httpx.RequestError as error:
                raise WikipediaUnavailable("Wikipediaに接続できませんでした。") from error
            except (KeyError, TypeError, ValueError, ValidationError) as error:
                raise WikipediaUnavailable("Wikipediaから不正な概要データが返されました。") from error

            self._cache[cache_key] = (self._clock(), summary)
            return summary
