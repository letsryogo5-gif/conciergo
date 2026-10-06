import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.ekispert import _make_url, _parse_legs
from app.main import app
from app.models import RouteLeg
from app.places import choose_places


class RoutePlannerTests(unittest.TestCase):
    def test_public_catalog_endpoints_are_available_without_api_key(self):
        client = TestClient(app)

        self.assertEqual(client.get("/api/health").json(), {"status": "ok"})
        self.assertEqual(len(client.get("/api/places").json()), 10)
        self.assertGreater(len(client.get("/api/origins").json()), 0)

    def test_itinerary_uses_selected_theme_and_stop_limit(self):
        places = choose_places("nature", 2, "京都")

        self.assertEqual(len(places), 2)
        self.assertTrue(all("nature" in place.themes for place in places))

    def test_unknown_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            choose_places("all", 2, "知らない駅")

    def test_access_points_use_ekispert_station_names_not_bus_stop_names(self):
        access_points = {place.access_point for place in choose_places("all", 10, "京都")}

        self.assertIn("清水五条", access_points)
        self.assertIn("北野白梅町", access_points)
        self.assertIn("出町柳", access_points)
        self.assertNotIn("清水道", access_points)
        self.assertNotIn("金閣寺道", access_points)
        self.assertNotIn("銀閣寺道", access_points)

    def test_route_search_url_keeps_via_delimiters_unescaped(self):
        url = _make_url({"key": "safe-test-key", "viaList": "京都:稲荷:京都"})

        self.assertIn("viaList=%E4%BA%AC%E9%83%BD:%E7%A8%B2%E8%8D%B7:%E4%BA%AC%E9%83%BD", url)

    def test_ekispert_course_is_normalized_to_segments(self):
        course = {
            "Route": {
                "timeOnBoard": "25",
                "timeOther": "10",
                "Point": [
                    {"Station": {"Name": "京都"}},
                    {"Station": {"Name": "稲荷"}},
                ],
                "Line": [
                    {
                        "Name": "JR奈良線",
                        "Type": "train",
                        "timeOnBoard": "25",
                    }
                ],
            }
        }

        legs, total_minutes = _parse_legs(course)

        self.assertEqual(len(legs), 1)
        self.assertEqual(legs[0].from_name, "京都")
        self.assertEqual(legs[0].to_name, "稲荷")
        self.assertEqual(legs[0].line_name, "JR奈良線")
        self.assertEqual(total_minutes, 35)

    def test_route_search_reports_missing_api_key(self):
        client = TestClient(app)
        request = {
            "origin": "京都",
            "theme": "all",
            "stop_count": 1,
            "departure_date": "2026-10-05",
            "departure_time": "09:00",
        }
        with patch.dict("os.environ", {}, clear=True), patch("app.ekispert.load_dotenv"):
            response = client.post("/api/routes", json=request)

        self.assertEqual(response.status_code, 503)
        self.assertIn("EKISPERT_API_KEY", response.json()["detail"])

    def test_route_suggestion_uses_one_real_route_search(self):
        client = TestClient(app)
        request = {
            "origin": "京都",
            "theme": "all",
            "stop_count": 3,
            "departure_date": "2026-10-05",
            "departure_time": "09:00",
        }
        search = AsyncMock(return_value=(
            [RouteLeg(
                from_name="京都",
                to_name="稲荷",
                line_name="JR奈良線",
                mode="train",
                duration_minutes=5,
            )],
            35,
            "09:00",
            "09:35",
        ))

        with patch("app.main.search_route", search):
            response = client.post("/api/routes", json=request)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["legs"][0]["line_name"], "JR奈良線")
        self.assertEqual(body["total_minutes"], 35)
        selected = choose_places("all", 3, "京都")
        search.assert_awaited_once_with(
            via_points=[
                "34.98585,135.75877",
                *(f"{place.latitude},{place.longitude}" for place in selected),
                "34.98585,135.75877",
            ],
            departure_date="2026-10-05",
            departure_time="09:00",
        )


if __name__ == "__main__":
    unittest.main()
