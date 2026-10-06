import unittest

import httpx

from app.integrations.nominatim import NominatimService, USER_AGENT


class NominatimServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_is_japan_scoped_and_cached(self) -> None:
        requests: list[httpx.Request] = []

        async def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json=[
                    {
                        "place_id": 123,
                        "display_name": "京都駅, 京都市, 京都府, 日本",
                        "lat": "34.9858",
                        "lon": "135.7588",
                        "category": "railway",
                        "type": "station",
                    }
                ],
            )

        transport = httpx.MockTransport(respond)
        async with NominatimService(transport=transport) as service:
            first = await service.search("  京都駅  ")
            second = await service.search("京都駅")

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.params["q"], "京都駅")
        self.assertEqual(requests[0].url.params["countrycodes"], "jp")
        self.assertEqual(requests[0].headers["user-agent"], USER_AGENT)
        self.assertEqual(first, second)
        self.assertEqual(first[0].latitude, 34.9858)
        self.assertEqual(first[0].longitude, 135.7588)

    async def test_empty_query_is_rejected_without_network_request(self) -> None:
        async with NominatimService(transport=httpx.MockTransport(lambda _: self.fail("unexpected request"))) as service:
            with self.assertRaisesRegex(ValueError, "地名を入力してください"):
                await service.search("   ")
