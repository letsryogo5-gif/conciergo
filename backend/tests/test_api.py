import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.event_sample_data import SAMPLE_EVENTS
from app.integrations.nominatim import NominatimService
from app.integrations.osrm import OSRMUnavailable
from app.integrations.wikipedia import WikipediaUnavailable
from app.main import app
from app.models import GeocodingResult, MediaAsset, MediaProviderStatus, RouteRequest, SpotMediaResults, WikipediaSummary
from app.sample_data import SPOTS
from app.services.routes import create_sample_route


class DiscoveryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        osrm_patch = patch("app.main.OSRMService.apply_to_plan", new_callable=AsyncMock)
        self.osrm_apply = osrm_patch.start()
        self.osrm_apply.side_effect = lambda plan: plan
        self.addCleanup(osrm_patch.stop)
        wikipedia_patch = patch("app.main.WikipediaService.search_summary", new_callable=AsyncMock)
        self.wikipedia_search = wikipedia_patch.start()
        self.wikipedia_search.return_value = None
        self.addCleanup(wikipedia_patch.stop)
        media_patch = patch("app.main.HybridMediaService.search", new_callable=AsyncMock)
        self.media_search = media_patch.start()
        self.media_search.return_value = SpotMediaResults(
            spot_id="yakushima",
            query="鹿児島県 Yakushima 世界自然遺産 苔の森",
            media_type="image",
            source="local_sample",
            items=[],
            fallback_url="/sample-media/moss-forest.svg",
            providers=[
                MediaProviderStatus(provider="pixabay", status="not_configured", result_count=0),
                MediaProviderStatus(provider="pexels", status="not_configured", result_count=0),
            ],
        )
        self.addCleanup(media_patch.stop)

    def test_status_explicitly_reports_sample_mode_and_unimplemented_services(self) -> None:
        response = self.client.get("/api/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "sample_mode": True,
                "services": {
                    "google_maps": "not_implemented",
                    "social": "not_implemented",
                },
            },
        )

    def test_spot_feed_includes_location_media_and_local_discoveries(self) -> None:
        response = self.client.get("/api/spots")

        self.assertEqual(response.status_code, 200)
        spots = response.json()
        self.assertGreaterEqual(len(spots), 5)
        self.assertTrue(
            all(
                spot["image_url"]
                and -90 <= spot["latitude"] <= 90
                and -180 <= spot["longitude"] <= 180
                and spot["local_food"]
                and spot["local_species"]
                for spot in spots
            )
        )
        self.assertTrue(all(spot["image_url"].startswith("/sample-media/") for spot in spots))
        self.assertTrue(all(spot["video_url"] is None for spot in spots))
        self.assertTrue(all(spot["local_trivia"] for spot in spots))
        self.assertTrue(any(spot["is_world_heritage"] for spot in spots))

    def test_catalog_exposes_scoped_sources_and_keeps_unverified_records_labeled(self) -> None:
        response = self.client.get("/api/spots")

        self.assertEqual(response.status_code, 200)
        spots = {spot["id"]: spot for spot in response.json()}
        yakushima = spots["yakushima"]
        self.assertEqual(yakushima["data_status"], "sourced")
        self.assertIn("description", yakushima["sources"][0]["verified_fields"])
        self.assertEqual(yakushima["sources"][0]["license_name"], "CC BY-SA 4.0 (本文)")
        self.assertEqual(spots["shiretoko"]["data_status"], "sample")
        self.assertEqual(spots["shiretoko"]["sources"], [])

    def test_gion_event_cites_official_july_ritual_dates(self) -> None:
        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        gion = next(event for event in response.json() if event["id"] == "gion-matsuri")
        self.assertEqual(gion["data_status"], "sourced")
        self.assertEqual((gion["start_month"], gion["end_month"]), (7, 7))
        self.assertIn("7月17日", gion["description"])
        self.assertIn("7月24日", gion["description"])
        self.assertEqual(gion["sources"][0]["publisher"], "Kyoto Travel")

    def test_spot_media_uses_local_fallback_when_external_keys_are_unset(self) -> None:
        response = self.client.get("/api/spots/yakushima/media")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "local_sample")
        self.assertEqual(body["items"], [])
        self.assertEqual(body["fallback_url"], "/sample-media/moss-forest.svg")
        self.assertEqual(
            [provider["status"] for provider in body["providers"]],
            ["not_configured", "not_configured"],
        )
        self.media_search.assert_awaited_once()

    def test_spot_media_supports_video_search_and_limit(self) -> None:
        self.media_search.return_value = SpotMediaResults(
            spot_id="yakushima",
            query="鹿児島県 Yakushima 世界自然遺産 苔の森",
            media_type="video",
            source="providers",
            items=[
                MediaAsset(
                    id="pexels-7",
                    media_type="video",
                    url="https://videos.example.test/forest.mp4",
                    preview_url="https://videos.example.test/forest.jpg",
                    page_url="https://www.pexels.com/video/forest-7/",
                    source="pexels",
                    description="Forest",
                    duration_seconds=12,
                )
            ],
            fallback_url="/sample-media/moss-forest.svg",
            providers=[MediaProviderStatus(provider="pexels", status="available", result_count=1)],
        )

        response = self.client.get(
            "/api/spots/yakushima/media",
            params={"media_type": "video", "limit": 3},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["media_type"], "video")
        self.assertEqual(response.json()["items"][0]["source"], "pexels")
        self.media_search.assert_awaited_once()
        self.assertEqual(self.media_search.await_args.kwargs["media_type"], "video")
        self.assertEqual(self.media_search.await_args.kwargs["limit"], 3)

    def test_spot_media_rejects_unknown_spots_and_invalid_limits(self) -> None:
        unknown = self.client.get("/api/spots/unknown/media")
        invalid_limit = self.client.get("/api/spots/yakushima/media", params={"limit": 0})

        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(invalid_limit.status_code, 422)

    def test_discovery_spots_can_be_filtered_by_dynamic_category_and_region(self) -> None:
        response = self.client.get(
            "/api/discover/spots",
            params={"category": "世界遺産", "region": "北海道"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual({spot["prefecture"] for spot in payload["items"]}, {"北海道"})
        self.assertTrue(all(spot["is_world_heritage"] for spot in payload["items"]))
        self.assertIn("年中行事", payload["categories"])
        self.assertIn("世界遺産", payload["categories"])
        self.assertEqual(payload["source"], "sample_catalog")

    def test_annual_event_category_is_derived_from_linked_events(self) -> None:
        response = self.client.get("/api/discover/spots", params={"category": "年中行事"})

        self.assertEqual(response.status_code, 200)
        spot_ids = {spot["id"] for spot in response.json()["items"]}
        self.assertEqual(spot_ids, {event.spot_id for event in SAMPLE_EVENTS})

    def test_discovery_inspiration_returns_a_limited_random_candidate_set(self) -> None:
        response = self.client.get(
            "/api/discover/spots",
            params={"limit": 3, "random_order": "true"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 3)
        self.assertEqual(payload["total"], len(SPOTS))
        self.assertEqual(len({spot["id"] for spot in payload["items"]}), 3)

    def test_discovery_rejects_unknown_filter_values(self) -> None:
        category_response = self.client.get("/api/discover/spots", params={"category": "未登録"})
        region_response = self.client.get("/api/discover/spots", params={"region": "未登録県"})

        self.assertEqual(category_response.status_code, 422)
        self.assertEqual(region_response.status_code, 422)

    def test_seasonal_events_include_months_and_linked_spots(self) -> None:
        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        events = response.json()
        self.assertGreaterEqual(len(events), 4)
        self.assertTrue(
            all(
                1 <= event["start_month"] <= event["end_month"] <= 12
                and event["spot_id"]
                and event["image_url"]
                for event in events
            )
        )

    def test_memories_include_ordered_routes_and_geotagged_sample_photos(self) -> None:
        response = self.client.get("/api/memories")

        self.assertEqual(response.status_code, 200)
        memories = response.json()
        known_spot_ids = {spot.id for spot in SPOTS}
        self.assertGreaterEqual(len(memories), 2)
        for memory in memories:
            date.fromisoformat(memory["visited_at"])
            self.assertTrue(memory["route"])
            self.assertTrue(memory["photos"])
            route_ids = {point["spot_id"] for point in memory["route"]}
            self.assertTrue(route_ids.issubset(known_spot_ids))
            for photo in memory["photos"]:
                datetime.fromisoformat(photo["captured_at"])
                self.assertTrue(
                    photo["spot_id"] in route_ids
                    and photo["image_url"]
                    and -90 <= photo["latitude"] <= 90
                    and -180 <= photo["longitude"] <= 180
                )

    def test_model_course_feed_contains_the_setouchi_sample_itinerary(self) -> None:
        response = self.client.get("/api/model-courses")

        self.assertEqual(response.status_code, 200)
        courses = response.json()
        setouchi_course = next(
            course for course in courses if course["id"] == "setouchi-udon-towel-yaki"
        )
        self.assertIn("香川・愛媛", setouchi_course["title"])
        self.assertEqual(
            set(setouchi_course["spot_ids"]),
            {
                "kagawa-sanuki-udon",
                "imabari-towel-museum",
                "matsuyama-mitsuhama-yaki",
            },
        )
        self.assertTrue(all(spot_id in {spot.id for spot in SPOTS} for spot_id in setouchi_course["spot_ids"]))

    def test_sample_content_images_are_local_assets(self) -> None:
        response_sets = [
            self.client.get("/api/spots"),
            self.client.get("/api/events"),
            self.client.get("/api/memories"),
            self.client.get("/api/model-courses"),
        ]
        self.assertTrue(all(response.status_code == 200 for response in response_sets))

        image_urls = [
            item["image_url"]
            for response in response_sets
            for item in response.json()
            for item in (
                [*item["photos"]] if "photos" in item else [item]
            )
        ]
        self.assertTrue(image_urls)
        for image_url in image_urls:
            self.assertTrue(image_url.startswith("/sample-media/"), image_url)
            asset_path = Path(__file__).resolve().parents[2] / "frontend" / "public" / image_url.lstrip("/")
            self.assertTrue(asset_path.is_file(), image_url)

    def test_published_model_course_is_returned_by_the_sample_api(self) -> None:
        request = {
            "title": "瀬戸内の味をめぐる小さな旅",
            "description": "うどんと港町の味を楽しむコース。",
            "region": "香川・愛媛",
            "creator": "テストの旅人",
            "spot_ids": ["kagawa-sanuki-udon", "matsuyama-mitsuhama-yaki"],
        }

        response = self.client.post("/api/model-courses", json=request)

        self.assertEqual(response.status_code, 201)
        published = response.json()
        self.assertEqual(published["title"], request["title"])
        self.assertEqual(published["spot_ids"], request["spot_ids"])
        self.assertEqual(published["likes"], 0)
        listed = self.client.get("/api/model-courses").json()
        self.assertEqual(listed[0]["id"], published["id"])

    def test_model_course_rejects_duplicate_and_unknown_spots(self) -> None:
        request = {
            "title": "確認用モデルコース",
            "description": "スポット入力の検証。",
            "region": "香川",
            "spot_ids": ["kagawa-sanuki-udon", "kagawa-sanuki-udon"],
        }
        duplicate = self.client.post("/api/model-courses", json=request)
        request["spot_ids"] = ["missing-spot"]
        unknown = self.client.post("/api/model-courses", json=request)

        self.assertEqual(duplicate.status_code, 422)
        self.assertEqual(unknown.status_code, 404)

    def test_saved_spot_can_be_loaded_again_by_id(self) -> None:
        response = self.client.get("/api/spots/fuji-shibazakura")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["local_species"], "富士の芝桜")
        self.assertTrue(response.json()["image_url"].startswith("/sample-media/"))
        self.assertIsNone(response.json()["video_url"])

    def test_unknown_spot_returns_an_explicit_not_found_error(self) -> None:
        response = self.client.get("/api/spots/unknown")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "スポットが見つかりません。")

    def test_spot_knowledge_returns_a_linked_wikipedia_summary(self) -> None:
        summary = WikipediaSummary(
            title="屋久島",
            extract="屋久島は鹿児島県の島である。",
            article_url="https://ja.wikipedia.org/wiki/%E5%B1%8B%E4%B9%85%E5%B3%B6",
        )
        self.wikipedia_search.return_value = summary

        response = self.client.get("/api/spots/yakushima/knowledge")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), summary.model_dump())
        self.wikipedia_search.assert_awaited_once_with("屋久島")

    def test_spot_knowledge_returns_null_when_no_article_is_found(self) -> None:
        response = self.client.get("/api/spots/ine/knowledge")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json())
        self.wikipedia_search.assert_awaited_once_with("伊根町 舟屋")

    def test_spot_knowledge_reports_upstream_errors(self) -> None:
        self.wikipedia_search.side_effect = WikipediaUnavailable("Wikipediaに接続できませんでした。")

        response = self.client.get("/api/spots/yakushima/knowledge")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Wikipediaに接続できませんでした。")

    def test_geocode_returns_normalized_japan_place_results(self) -> None:
        result = GeocodingResult(
            place_id=123,
            display_name="京都駅, 京都市, 京都府, 日本",
            latitude=34.9858,
            longitude=135.7588,
            category="railway",
            place_type="station",
        )
        with patch.object(NominatimService, "search", new_callable=AsyncMock, return_value=[result]) as search:
            response = self.client.get("/api/geocode", params={"q": "京都駅"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["display_name"], result.display_name)
        self.assertEqual(response.json()[0]["latitude"], result.latitude)
        search.assert_awaited_once_with("京都駅", limit=5)

    def test_geocode_rejects_too_short_queries(self) -> None:
        response = self.client.get("/api/geocode", params={"q": "a"})

        self.assertEqual(response.status_code, 422)

    def test_route_uses_saved_spots_and_returns_sample_day_timelines(self) -> None:
        response = self.client.post(
            "/api/routes",
            json={"spot_ids": ["ine", "fuji-shibazakura"]},
        )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertTrue(route["sample_mode"])
        self.assertEqual(route["algorithm"], "sample_proximity_nearest_neighbor")
        self.assertEqual(route["total_spots"], 2)
        self.assertEqual(len(route["days"]), 2)
        self.assertEqual(
            {day["stops"][0]["spot"]["id"] for day in route["days"]},
            {"ine", "fuji-shibazakura"},
        )
        self.assertTrue(all(day["start_time"] == "09:00" for day in route["days"]))
        self.assertIn("直線距離", route["note"])
        self.assertIn("日をまたぐ移動は考慮していません", route["note"])

    def test_route_uses_only_the_selected_spot_ids(self) -> None:
        response = self.client.post(
            "/api/routes",
            json={"spot_ids": ["kagawa-sanuki-udon"]},
        )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        route_spot_ids = {
            stop["spot"]["id"]
            for day in route["days"]
            for stop in day["stops"]
        }
        self.assertEqual(route["total_spots"], 1)
        self.assertEqual(route_spot_ids, {"kagawa-sanuki-udon"})

    def test_route_requires_unique_known_spots(self) -> None:
        empty = self.client.post("/api/routes", json={"spot_ids": []})
        duplicate = self.client.post("/api/routes", json={"spot_ids": ["ine", "ine"]})
        unknown = self.client.post("/api/routes", json={"spot_ids": ["unknown"]})

        self.assertEqual(empty.status_code, 422)
        self.assertEqual(duplicate.status_code, 422)
        self.assertEqual(unknown.status_code, 404)
        self.assertIn("unknown", unknown.json()["detail"])

    def test_route_reports_osrm_failures_without_sample_fallback(self) -> None:
        self.osrm_apply.side_effect = OSRMUnavailable("経路サービスに接続できませんでした。")

        response = self.client.post(
            "/api/routes",
            json={"spot_ids": ["kyoto-kamogawa", "nara-park"]},
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "経路サービスに接続できませんでした。")

    def test_kansai_sample_spots_can_generate_a_single_day_loop(self) -> None:
        response = self.client.post(
            "/api/routes",
            json={"spot_ids": ["ine", "kyoto-kamogawa", "nara-park"]},
        )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertEqual(len(route["days"]), 1)
        self.assertTrue(route["days"][0]["title"].endswith("をめぐる日"))
        self.assertEqual(len(route["days"][0]["stops"]), 3)
        self.assertEqual(route["total_estimated_travel_minutes"], sum(
            stop["travel_minutes_from_previous"] for stop in route["days"][0]["stops"]
        ))

    def test_event_route_adds_nearby_heritage_and_trivia_spots(self) -> None:
        response = self.client.post(
            "/api/routes",
            json={"spot_ids": ["kyoto-kamogawa"], "event_id": "gion-matsuri"},
        )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertEqual(route["occasion"]["id"], "gion-matsuri")
        self.assertEqual(route["occasion"]["best_time"], "7月")
        self.assertEqual(route["total_spots"], 3)
        self.assertEqual(set(route["added_spot_ids"]), {"ine", "nara-park"})
        route_spots = {
            stop["spot"]["id"]
            for day in route["days"]
            for stop in day["stops"]
        }
        self.assertEqual(route_spots, {"kyoto-kamogawa", "ine", "nara-park"})
        self.assertIn("祇園祭", route["note"])

    def test_shiretoko_event_route_includes_nearby_heritage_and_trivia(self) -> None:
        response = self.client.post(
            "/api/routes",
            json={"spot_ids": ["shiretoko"], "event_id": "shiretoko-drift-ice"},
        )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertEqual(route["occasion"]["id"], "shiretoko-drift-ice")
        self.assertIn("shiretoko-five-lakes", route["added_spot_ids"])
        route_spots = {
            stop["spot"]["id"]
            for day in route["days"]
            for stop in day["stops"]
        }
        self.assertEqual(route_spots, {"shiretoko", "shiretoko-five-lakes"})
        five_lakes = next(
            stop["spot"]
            for day in route["days"]
            for stop in day["stops"]
            if stop["spot"]["id"] == "shiretoko-five-lakes"
        )
        self.assertTrue(five_lakes["is_world_heritage"])
        self.assertTrue(five_lakes["local_trivia"])

    def test_route_groups_nearby_spots_and_orders_each_day_by_proximity(self) -> None:
        tokyo_spots = [
            SPOTS[0].model_copy(
                update={
                    "id": "tokyo-south",
                    "latitude": 35.0,
                    "longitude": 139.0,
                    "prefecture": "東京都",
                }
            ),
            SPOTS[1].model_copy(
                update={
                    "id": "tokyo-center",
                    "latitude": 35.1,
                    "longitude": 139.1,
                    "prefecture": "東京都",
                }
            ),
            SPOTS[2].model_copy(
                update={
                    "id": "tokyo-east",
                    "latitude": 35.05,
                    "longitude": 139.2,
                    "prefecture": "東京都",
                }
            ),
        ]
        hokkaido_spot = SPOTS[3].model_copy(
            update={
                "id": "hokkaido",
                "latitude": 44.0,
                "longitude": 145.0,
                "prefecture": "北海道",
            }
        )
        response = create_sample_route(
            RouteRequest(spot_ids=["tokyo-center", "tokyo-south", "tokyo-east", "hokkaido"]),
            [*tokyo_spots, hokkaido_spot],
        )

        self.assertEqual(len(response.days), 2)
        tokyo_day = next(day for day in response.days if day.title.startswith("東京都"))
        self.assertEqual(
            [stop.spot.id for stop in tokyo_day.stops],
            ["tokyo-south", "tokyo-center", "tokyo-east"],
        )
        self.assertLessEqual(len(tokyo_day.stops), 3)


if __name__ == "__main__":
    unittest.main()
