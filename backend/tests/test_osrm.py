import unittest

import httpx

from app.integrations.osrm import OSRMService, OSRMUnavailable, OSRM_USER_AGENT
from app.models import RouteRequest
from app.sample_data import SPOTS
from app.services.routes import create_sample_route


class OSRMServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_route_optimizes_stops_and_uses_road_metrics_and_geometry(self) -> None:
        requests: list[httpx.Request] = []

        async def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "code": "Ok",
                    "waypoints": [
                        {"waypoint_index": 2},
                        {"waypoint_index": 0},
                        {"waypoint_index": 1},
                    ],
                    "trips": [
                        {
                            "legs": [
                                {"duration": 3600, "distance": 25000},
                                {"duration": 1800, "distance": 12000},
                            ],
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [
                                    [135.7, 35.0],
                                    [135.8, 35.1],
                                    [135.9, 35.2],
                                ],
                            },
                        }
                    ],
                },
            )

        plan = create_sample_route(
            RouteRequest(spot_ids=["kyoto-kamogawa", "ine", "nara-park"]),
            SPOTS,
        )
        async with OSRMService(
            transport=httpx.MockTransport(respond),
            minimum_request_interval=0,
        ) as service:
            routed = await service.apply_to_plan(plan)

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].headers["user-agent"], OSRM_USER_AGENT)
        self.assertEqual(requests[0].url.params["roundtrip"], "false")
        day = routed.days[0]
        original_ids = [stop.spot.id for stop in plan.days[0].stops]
        self.assertEqual(
            [stop.spot.id for stop in day.stops],
            [original_ids[1], original_ids[2], original_ids[0]],
        )
        self.assertEqual(day.stops[1].travel_minutes_from_previous, 60)
        self.assertEqual(day.stops[1].distance_km_from_previous, 25.0)
        self.assertEqual(day.stops[2].travel_minutes_from_previous, 30)
        self.assertEqual(day.route_coordinates[0].latitude, 35.0)
        self.assertEqual(day.route_coordinates[0].longitude, 135.7)
        self.assertEqual(routed.total_estimated_travel_minutes, 90)
        self.assertEqual(routed.algorithm, "osrm_trip")

    async def test_successful_routes_are_cached(self) -> None:
        requests: list[httpx.Request] = []

        async def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "code": "Ok",
                    "waypoints": [{"waypoint_index": 0}, {"waypoint_index": 1}],
                    "trips": [
                        {
                            "legs": [{"duration": 600, "distance": 5000}],
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [[135.7, 35.0], [135.8, 35.1]],
                            },
                        }
                    ],
                },
            )

        plan = create_sample_route(
            RouteRequest(spot_ids=["kyoto-kamogawa", "nara-park"]),
            SPOTS,
        )
        async with OSRMService(
            transport=httpx.MockTransport(respond),
            minimum_request_interval=0,
        ) as service:
            await service.apply_to_plan(plan)
            await service.apply_to_plan(plan)

        self.assertEqual(len(requests), 1)

    async def test_unroutable_response_is_not_silently_replaced_by_sample_route(self) -> None:
        async def respond(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"code": "NoRoute", "message": "No route found"})

        plan = create_sample_route(
            RouteRequest(spot_ids=["kyoto-kamogawa", "nara-park"]),
            SPOTS,
        )
        async with OSRMService(
            transport=httpx.MockTransport(respond),
            minimum_request_interval=0,
        ) as service:
            with self.assertRaisesRegex(OSRMUnavailable, "経路サービスがルートを作成できませんでした"):
                await service.apply_to_plan(plan)


if __name__ == "__main__":
    unittest.main()
