import unittest
from datetime import date, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.models import RouteRequest
from app.sample_data import SPOTS
from app.services.routes import create_sample_route


class DiscoveryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

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
        self.assertTrue(any(spot["video_url"] for spot in spots))
        self.assertTrue(all(spot["local_trivia"] for spot in spots))
        self.assertTrue(any(spot["is_world_heritage"] for spot in spots))

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
        self.assertIsNotNone(response.json()["video_url"])

    def test_unknown_spot_returns_an_explicit_not_found_error(self) -> None:
        response = self.client.get("/api/spots/unknown")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "スポットが見つかりません。")

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
