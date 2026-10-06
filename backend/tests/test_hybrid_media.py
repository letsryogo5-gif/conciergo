import unittest

import httpx

from app.integrations.hybrid_media import HybridMediaService
from app.integrations.pexels import PEXELS_PHOTO_API_URL, PEXELS_VIDEO_API_URL, PexelsClient
from app.integrations.pixabay import PIXABAY_IMAGE_API_URL, PIXABAY_VIDEO_API_URL, PixabayClient
from app.models import SpotMediaResults


class MediaProviderClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_pixabay_parses_image_results(self) -> None:
        async def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url.copy_with(query=None)), PIXABAY_IMAGE_API_URL)
            self.assertEqual(request.url.params["key"], "test-pixabay-key")
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {
                            "id": 12,
                            "pageURL": "https://pixabay.com/photos/forest-12/",
                            "largeImageURL": "https://cdn.example.test/forest-large.jpg",
                            "previewURL": "https://cdn.example.test/forest-preview.jpg",
                            "tags": "forest, moss",
                            "user": "forest_photographer",
                        }
                    ]
                },
            )

        async with PixabayClient(
            "test-pixabay-key",
            transport=httpx.MockTransport(respond),
        ) as client:
            results = await client.search("Yakushima forest", "image", 4)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "pixabay")
        self.assertEqual(results[0].description, "forest, moss")
        self.assertEqual(results[0].creator, "forest_photographer")

    async def test_pixabay_requests_minimum_supported_page_size_for_one_result(self) -> None:
        async def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["per_page"], "3")
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {
                            "id": item_id,
                            "pageURL": f"https://pixabay.com/photos/forest-{item_id}/",
                            "largeImageURL": f"https://cdn.example.test/forest-{item_id}.jpg",
                        }
                        for item_id in range(1, 4)
                    ]
                },
            )

        async with PixabayClient(
            "test-pixabay-key",
            transport=httpx.MockTransport(respond),
        ) as client:
            results = await client.search("Yakushima forest", "image", 1)

        self.assertEqual(len(results), 1)

    async def test_pexels_parses_video_results(self) -> None:
        async def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url.copy_with(query=None)), PEXELS_VIDEO_API_URL)
            self.assertEqual(request.headers["authorization"], "test-pexels-key")
            return httpx.Response(
                200,
                json={
                    "videos": [
                        {
                            "id": 34,
                            "url": "https://www.pexels.com/video/forest-34/",
                            "image": "https://cdn.example.test/forest-cover.jpg",
                            "duration": 14,
                            "video_files": [
                                {
                                    "link": "https://cdn.example.test/forest-low.mp4",
                                    "width": 640,
                                    "height": 360,
                                },
                                {
                                    "link": "https://cdn.example.test/forest-hd.mp4",
                                    "width": 1920,
                                    "height": 1080,
                                },
                            ],
                        }
                    ]
                },
            )

        async with PexelsClient(
            "test-pexels-key",
            transport=httpx.MockTransport(respond),
        ) as client:
            results = await client.search("Yakushima forest", "video", 4)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "pexels")
        self.assertEqual(results[0].url, "https://cdn.example.test/forest-hd.mp4")
        self.assertEqual(results[0].duration_seconds, 14)

    async def test_pixabay_video_uses_the_video_endpoint(self) -> None:
        async def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url.copy_with(query=None)), PIXABAY_VIDEO_API_URL)
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {
                            "id": 5,
                            "pageURL": "https://pixabay.com/videos/forest-5/",
                            "picture": "https://cdn.example.test/cover.jpg",
                            "duration": 9,
                            "videos": {
                                "large": {"url": "https://cdn.example.test/forest.mp4"}
                            },
                        }
                    ]
                },
            )

        async with PixabayClient(
            "test-pixabay-key",
            transport=httpx.MockTransport(respond),
        ) as client:
            results = await client.search("forest", "video", 2)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].media_type, "video")
        self.assertEqual(results[0].duration_seconds, 9)

    async def test_pexels_parses_image_results(self) -> None:
        async def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url.copy_with(query=None)), PEXELS_PHOTO_API_URL)
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "id": 9,
                            "url": "https://www.pexels.com/photo/forest-9/",
                            "alt": "Moss forest",
                            "src": {
                                "large2x": "https://cdn.example.test/forest.jpg",
                                "medium": "https://cdn.example.test/forest-medium.jpg",
                            },
                        }
                    ]
                },
            )

        async with PexelsClient(
            "test-pexels-key",
            transport=httpx.MockTransport(respond),
        ) as client:
            results = await client.search("forest", "image", 2)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].description, "Moss forest")


class HybridMediaServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_sources_are_requested_and_results_are_merged(self) -> None:
        pixabay_requests: list[httpx.Request] = []
        pexels_requests: list[httpx.Request] = []

        async def pixabay(request: httpx.Request) -> httpx.Response:
            pixabay_requests.append(request)
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {
                            "id": 1,
                            "pageURL": "https://pixabay.com/photos/one/",
                            "largeImageURL": "https://cdn.example.test/one.jpg",
                            "previewURL": "https://cdn.example.test/one-preview.jpg",
                        }
                    ]
                },
            )

        async def pexels(request: httpx.Request) -> httpx.Response:
            pexels_requests.append(request)
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "id": 2,
                            "url": "https://www.pexels.com/photo/two/",
                            "src": {
                                "large": "https://cdn.example.test/two.jpg",
                                "medium": "https://cdn.example.test/two-preview.jpg",
                            },
                        }
                    ]
                },
            )

        async with HybridMediaService(
            pixabay_api_key="pixabay-key",
            pexels_api_key="pexels-key",
            pixabay_transport=httpx.MockTransport(pixabay),
            pexels_transport=httpx.MockTransport(pexels),
        ) as service:
            results = await service.search(
                spot_id="yakushima",
                query="Yakushima moss",
                media_type="image",
                fallback_url="/sample-media/moss-forest.svg",
            )

        self.assertEqual(len(pixabay_requests), 1)
        self.assertEqual(len(pexels_requests), 1)
        self.assertEqual(results.source, "providers")
        self.assertEqual([asset.source for asset in results.items], ["pixabay", "pexels"])

    async def test_one_rate_limited_provider_falls_back_to_the_other(self) -> None:
        async def pixabay(_: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": "rate limit"})

        async def pexels(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "photos": [
                        {
                            "id": 3,
                            "url": "https://www.pexels.com/photo/three/",
                            "src": {"large": "https://cdn.example.test/three.jpg"},
                        }
                    ]
                },
            )

        async with HybridMediaService(
            pixabay_api_key="pixabay-key",
            pexels_api_key="pexels-key",
            pixabay_transport=httpx.MockTransport(pixabay),
            pexels_transport=httpx.MockTransport(pexels),
        ) as service:
            results = await service.search(
                spot_id="yakushima",
                query="Yakushima moss",
                media_type="image",
                fallback_url="/sample-media/moss-forest.svg",
            )

        self.assertEqual(results.source, "providers")
        self.assertEqual([asset.source for asset in results.items], ["pexels"])
        self.assertEqual(
            [status.status for status in results.providers],
            ["unavailable", "available"],
        )

    async def test_missing_keys_skip_requests_and_return_local_fallback(self) -> None:
        async def unexpected_request(_: httpx.Request) -> httpx.Response:
            self.fail("No request should be made without API keys")

        async with HybridMediaService(
            pixabay_api_key="",
            pexels_api_key="",
            pixabay_transport=httpx.MockTransport(unexpected_request),
            pexels_transport=httpx.MockTransport(unexpected_request),
        ) as service:
            results = await service.search(
                spot_id="yakushima",
                query="Yakushima moss",
                media_type="image",
                fallback_url="/sample-media/moss-forest.svg",
            )

        self.assertEqual(results.source, "local_sample")
        self.assertEqual(results.items, [])
        self.assertEqual(results.fallback_url, "/sample-media/moss-forest.svg")
        self.assertEqual([status.status for status in results.providers], ["not_configured", "not_configured"])

    async def test_empty_results_use_local_fallback_and_are_cached(self) -> None:
        request_count = 0

        async def empty_response(_: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            return httpx.Response(200, json={"hits": []})

        async with HybridMediaService(
            pixabay_api_key="pixabay-key",
            pexels_api_key="",
            pixabay_transport=httpx.MockTransport(empty_response),
        ) as service:
            first = await service.search(
                spot_id="yakushima",
                query="Yakushima moss",
                media_type="image",
                fallback_url="/sample-media/moss-forest.svg",
            )
            second = await service.search(
                spot_id="yakushima",
                query="Yakushima moss",
                media_type="image",
                fallback_url="/sample-media/moss-forest.svg",
            )

        self.assertEqual(request_count, 1)
        self.assertEqual(first.source, "local_sample")
        self.assertEqual(second.fallback_url, first.fallback_url)

    async def test_both_unavailable_providers_return_local_fallback(self) -> None:
        async def unavailable(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        async with HybridMediaService(
            pixabay_api_key="pixabay-key",
            pexels_api_key="pexels-key",
            pixabay_transport=httpx.MockTransport(unavailable),
            pexels_transport=httpx.MockTransport(unavailable),
        ) as service:
            results = await service.search(
                spot_id="yakushima",
                query="Yakushima moss",
                media_type="image",
                fallback_url="/sample-media/moss-forest.svg",
            )

        self.assertEqual(results.source, "local_sample")
        self.assertEqual(results.items, [])
        self.assertEqual(
            [status.status for status in results.providers],
            ["unavailable", "unavailable"],
        )

    async def test_successful_pixabay_results_expire_after_24_hours(self) -> None:
        request_count = 0
        now = [0.0]

        async def response(_: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            return httpx.Response(
                200,
                json={
                    "hits": [
                        {
                            "id": request_count,
                            "pageURL": f"https://pixabay.com/photos/forest-{request_count}/",
                            "largeImageURL": f"https://cdn.example.test/forest-{request_count}.jpg",
                        }
                    ]
                },
            )

        async with HybridMediaService(
            pixabay_api_key="pixabay-key",
            pexels_api_key="",
            pixabay_transport=httpx.MockTransport(response),
            clock=lambda: now[0],
        ) as service:
            async def search() -> SpotMediaResults:
                return await service.search(
                    spot_id="yakushima",
                    query="Yakushima moss",
                    media_type="image",
                    fallback_url="/sample-media/moss-forest.svg",
                )

            await search()
            now[0] = 86_399
            await search()
            now[0] = 86_400
            await search()

        self.assertEqual(request_count, 2)


if __name__ == "__main__":
    unittest.main()
