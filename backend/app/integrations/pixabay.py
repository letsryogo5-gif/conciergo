import os
from typing import Literal

import httpx

from app.models import MediaAsset

PIXABAY_IMAGE_API_URL = "https://pixabay.com/api/"
PIXABAY_VIDEO_API_URL = "https://pixabay.com/api/videos/"


class MediaProviderUnavailable(Exception):
    pass


class PixabayClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        configured_key = os.getenv("PIXABAY_API_KEY", "") if api_key is None else api_key
        self._api_key = configured_key.strip()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=4.0),
            transport=transport,
        )

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def __aenter__(self) -> "PixabayClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def search(
        self,
        query: str,
        media_type: Literal["image", "video"],
        limit: int,
    ) -> list[MediaAsset]:
        if not self.configured:
            return []

        endpoint = PIXABAY_IMAGE_API_URL if media_type == "image" else PIXABAY_VIDEO_API_URL
        try:
            response = await self._client.get(
                endpoint,
                params={
                    "key": self._api_key,
                    "q": query,
                    "per_page": max(3, limit),
                    "safesearch": "true",
                    **({"image_type": "photo"} if media_type == "image" else {}),
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as error:
            raise MediaProviderUnavailable(
                f"Pixabay returned HTTP {error.response.status_code}."
            ) from error
        except httpx.TimeoutException as error:
            raise MediaProviderUnavailable("Pixabay request timed out.") from error
        except httpx.RequestError as error:
            raise MediaProviderUnavailable("Pixabay could not be reached.") from error
        except ValueError as error:
            raise MediaProviderUnavailable("Pixabay returned invalid JSON.") from error

        if not isinstance(payload, dict):
            raise MediaProviderUnavailable("Pixabay returned an invalid response.")
        records = payload.get("hits")
        if not isinstance(records, list):
            raise MediaProviderUnavailable("Pixabay returned an invalid media list.")

        assets: list[MediaAsset] = []
        for record in records:
            if not isinstance(record, dict):
                raise MediaProviderUnavailable("Pixabay returned an invalid media record.")
            record_id = record.get("id")
            page_url = record.get("pageURL")
            if not isinstance(record_id, (str, int)) or not isinstance(page_url, str):
                continue

            if media_type == "image":
                url = record.get("largeImageURL") or record.get("webformatURL")
                preview_url = record.get("previewURL") or url
                duration_seconds = None
            else:
                video_variants = record.get("videos")
                if not isinstance(video_variants, dict):
                    continue
                variant = video_variants.get("large") or video_variants.get("medium")
                if not isinstance(variant, dict):
                    continue
                url = variant.get("url")
                preview_url = record.get("picture") or url
                duration = record.get("duration")
                duration_seconds = duration if isinstance(duration, int) and duration >= 0 else None

            if not isinstance(url, str) or not url.startswith("https://"):
                continue
            if not isinstance(preview_url, str) or not preview_url.startswith("https://"):
                preview_url = url
            tags = record.get("tags")
            description = tags.strip() if isinstance(tags, str) else ""
            creator_value = record.get("user")
            assets.append(
                MediaAsset(
                    id=f"pixabay-{record_id}",
                    media_type=media_type,
                    url=url,
                    preview_url=preview_url,
                    page_url=page_url,
                    source="pixabay",
                    description=description,
                    duration_seconds=duration_seconds,
                    creator=creator_value.strip() if isinstance(creator_value, str) and creator_value.strip() else None,
                )
            )
            if len(assets) >= limit:
                break
        return assets
