import unittest

import httpx

from app.integrations.wikipedia import USER_AGENT, WikipediaService, WikipediaUnavailable


class WikipediaServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_returns_plain_text_summary_and_official_article_url(self) -> None:
        requests: list[httpx.Request] = []

        async def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "query": {
                        "pages": [
                            {
                                "pageid": 123,
                                "title": "屋久島",
                                "extract": "屋久島は鹿児島県の島である。",
                                "fullurl": "https://ja.wikipedia.org/wiki/%E5%B1%8B%E4%B9%85%E5%B3%B6",
                            }
                        ]
                    }
                },
            )

        async with WikipediaService(
            transport=httpx.MockTransport(respond),
            minimum_request_interval=0,
        ) as service:
            summary = await service.search_summary("  屋久島 ")

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.params["gsrsearch"], "屋久島")
        self.assertEqual(requests[0].url.params["explaintext"], "1")
        self.assertEqual(requests[0].headers["user-agent"], USER_AGENT)
        self.assertEqual(summary.title, "屋久島")
        self.assertEqual(summary.extract, "屋久島は鹿児島県の島である。")
        self.assertTrue(summary.article_url.startswith("https://ja.wikipedia.org/wiki/"))

    async def test_no_search_results_are_cached(self) -> None:
        request_count = 0

        async def respond(_: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            return httpx.Response(200, json={"query": {"pages": []}})

        async with WikipediaService(
            transport=httpx.MockTransport(respond),
            minimum_request_interval=0,
        ) as service:
            self.assertIsNone(await service.search_summary("見つからない場所"))
            self.assertIsNone(await service.search_summary("見つからない場所"))

        self.assertEqual(request_count, 1)

    async def test_empty_query_is_rejected_without_network_request(self) -> None:
        async with WikipediaService(
            transport=httpx.MockTransport(lambda _: self.fail("unexpected request")),
        ) as service:
            with self.assertRaisesRegex(ValueError, "2文字以上"):
                await service.search_summary(" ")

    async def test_invalid_article_link_is_reported(self) -> None:
        async def respond(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "query": {
                        "pages": [
                            {
                                "title": "屋久島",
                                "extract": "概要",
                                "fullurl": "https://example.com/article",
                            }
                        ]
                    }
                },
            )

        async with WikipediaService(
            transport=httpx.MockTransport(respond),
            minimum_request_interval=0,
        ) as service:
            with self.assertRaisesRegex(WikipediaUnavailable, "リンクが正しくありません"):
                await service.search_summary("屋久島")


if __name__ == "__main__":
    unittest.main()
