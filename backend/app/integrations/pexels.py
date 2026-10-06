import os
from typing import Literal

import httpx

from app.integrations.pixabay import MediaProviderUnavailable
from app.models import MediaAsset

PEXELS_PHOTO_API_URL = "https://api.pexels.com/v1/search"
PEXELS_VIDEO_API_URL = "https://api.pexels.com/videos/search"


class PexelsClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        configured_key = os.getenv("PEXELS_API_KEY", "") if api_key is None else api_key
        self._api_key = configured_key.strip()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=4.0),
            headers={"Authorization": self._api_key} if self._api_key else {},
            transport=transport,
        )

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def __aenter__(self) -> "PexelsClient":
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

        endpoint = PEXELS_PHOTO_API_URL if media_type == "image" else PEXELS_VIDEO_API_URL
        try:
            response = await self._client.get(
                endpoint,
                params={"query": query, "per_page": limit},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as error:
            raise MediaProviderUnavailable(
                f"Pexels returned HTTP {error.response.status_code}."
            ) from error
        except httpx.TimeoutException as error:
            raise MediaProviderUnavailable("Pexels request timed out.") from error
        except httpx.RequestError as error:
            raise MediaProviderUnavailable("Pexels could not be reached.") from error
        except ValueError as error:
            raise MediaProviderUnavailable("Pexels returned invalid JSON.") from error

        if not isinstance(payload, dict):
            raise MediaProviderUnavailable("Pexels returned an invalid response.")
        records_key = "photos" if media_type == "image" else "videos"
        records = payload.get(records_key)
        if not isinstance(records, list):
            raise MediaProviderUnavailable("Pexels returned an invalid media list.")

        assets: list[MediaAsset] = []
        for record in records:
            if not isinstance(record, dict):
                raise MediaProviderUnavailable("Pexels returned an invalid media record.")
            record_id = record.get("id")
            page_url = record.get("url")
            if not isinstance(record_id, (str, int)) or not isinstance(page_url, str):
                continue

            if media_type == "image":
                sources = record.get("src")
                if not isinstance(sources, dict):
                    continue
                url = sources.get("large2x") or sources.get("large") or sources.get("original")
                preview_url = sources.get("medium") or sources.get("small") or url
                description_value = record.get("alt")
                description = description_value.strip() if isinstance(description_value, str) else ""
                duration_seconds = None
            else:
                files = record.get("video_files")
                if not isinstance(files, list):
                    continue
                usable_files = [
                    file for file in files
                    if isinstance(file, dict)
                    and isinstance(file.get("link"), str)
                    and file["link"].startswith("https://")
                ]
                if not usable_files:
                    continue
                chosen_file = max(
                    usable_files,
                    key=lambda file: (
                        file.get("width", 0) if isinstance(file.get("width"), int) else 0,
                        file.get("height", 0) if isinstance(file.get("height"), int) else 0,
                    ),
                )
                url = chosen_file["link"]
                preview_value = record.get("image")
                preview_url = preview_value if isinstance(preview_value, str) else url
                description = ""
                duration = record.get("duration")
                duration_seconds = duration if isinstance(duration, int) and duration >= 0 else None
            user = record.get("user")
            creator_value = user.get("name") if isinstance(user, dict) else None

            if not isinstance(url, str) or not url.startswith("https://"):
                continue
            if not isinstance(preview_url, str) or not preview_url.startswith("https://"):
                preview_url = url
            assets.append(
                MediaAsset(
                    id=f"pexels-{record_id}",
                    media_type=media_type,
                    url=url,
                    preview_url=preview_url,
                    page_url=page_url,
                    source="pexels",
                    description=description,
                    duration_seconds=duration_seconds,
                    creator=creator_value.strip() if isinstance(creator_value, str) and creator_value.strip() else None,
                )
            )
            if len(assets) >= limit:
                break
        return assets
