from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase

from .services import geoapify


def _fake_response(payload, status_code=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


GEOCODE_PAYLOAD = {
    "features": [
        {
            "properties": {
                "lat": 41.8755616,
                "lon": -87.6244212,
                "formatted": "Chicago, IL, United States of America",
                "city": "Chicago",
                "state_code": "IL",
            }
        }
    ]
}

ROUTE_PAYLOAD = {
    "features": [
        {
            "geometry": {
                "type": "MultiLineString",
                "coordinates": [
                    [[-87.62, 41.87], [-88.00, 41.50]],  # leg 0
                    [[-88.00, 41.50], [-90.19, 38.62]],  # leg 1
                ],
            },
            "properties": {
                "distance": 482575.0,
                "time": 16779.412,
                "legs": [
                    {"distance": 327004.0, "time": 11323.538},
                    {"distance": 155571.0, "time": 5455.874},
                ],
            },
        }
    ]
}


class HealthEndpointTests(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class GeocodeServiceTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("trips.services.geoapify.requests.get")
    def test_geocode_parses_fields(self, mock_get):
        mock_get.return_value = _fake_response(GEOCODE_PAYLOAD)
        result = geoapify.geocode("Chicago, IL")
        self.assertEqual(result["lat"], 41.8755616)
        self.assertEqual(result["lon"], -87.6244212)
        self.assertEqual(result["state_code"], "IL")
        self.assertEqual(result["city"], "Chicago")

    @patch("trips.services.geoapify.requests.get")
    def test_geocode_is_cached(self, mock_get):
        mock_get.return_value = _fake_response(GEOCODE_PAYLOAD)
        geoapify.geocode("Chicago, IL")
        geoapify.geocode("chicago, il")  # same query, different case
        self.assertEqual(mock_get.call_count, 1)

    @patch("trips.services.geoapify.requests.get")
    def test_geocode_no_results_raises(self, mock_get):
        mock_get.return_value = _fake_response({"features": []})
        with self.assertRaises(geoapify.GeocodingError):
            geoapify.geocode("Nowhere Fakecity 99999")

    def test_geocode_empty_text_raises(self):
        with self.assertRaises(geoapify.GeocodingError):
            geoapify.geocode("   ")


class RouteServiceTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("trips.services.geoapify.requests.get")
    def test_route_flattens_and_converts(self, mock_get):
        mock_get.return_value = _fake_response(ROUTE_PAYLOAD)
        result = geoapify.route([(41.87, -87.62), (41.50, -88.0), (38.62, -90.19)])

        # MultiLineString (2 legs) -> single flattened LineString (4 points).
        self.assertEqual(len(result["geometry"]), 4)
        self.assertEqual(result["geometry"][0], [-87.62, 41.87])

        # Meters -> miles, seconds -> hours.
        self.assertAlmostEqual(result["distance_mi"], 482575.0 / 1609.344, places=2)
        self.assertAlmostEqual(result["time_hr"], 16779.412 / 3600.0, places=2)
        self.assertEqual(len(result["legs"]), 2)
        self.assertAlmostEqual(result["legs"][0]["distance_mi"], 327004.0 / 1609.344, places=2)

    @patch("trips.services.geoapify.requests.get")
    def test_route_is_cached(self, mock_get):
        mock_get.return_value = _fake_response(ROUTE_PAYLOAD)
        wp = [(41.87, -87.62), (38.62, -90.19)]
        geoapify.route(wp)
        geoapify.route(wp)
        self.assertEqual(mock_get.call_count, 1)

    @patch("trips.services.geoapify.requests.get")
    def test_route_no_route_raises(self, mock_get):
        mock_get.return_value = _fake_response({"features": []})
        with self.assertRaises(geoapify.RoutingError):
            geoapify.route([(0, 0), (1, 1)])

    def test_route_requires_two_waypoints(self):
        with self.assertRaises(geoapify.RoutingError):
            geoapify.route([(0, 0)])


class RouteEndpointTests(TestCase):
    def setUp(self):
        cache.clear()

    VALID_INPUT = {
        "current_location": "Chicago, IL",
        "pickup_location": "Springfield, IL",
        "dropoff_location": "St. Louis, MO",
        "current_cycle_used": 10,
    }

    def test_invalid_input_returns_400(self):
        response = self.client.post("/api/route/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_cycle_used_out_of_range_returns_400(self):
        bad = {**self.VALID_INPUT, "current_cycle_used": 80}
        response = self.client.post("/api/route/", bad, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @patch("trips.views.geoapify.geocode")
    def test_geocode_failure_returns_404(self, mock_geocode):
        mock_geocode.side_effect = geoapify.GeocodingError("not found")
        response = self.client.post(
            "/api/route/", self.VALID_INPUT, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["field"], "current_location")

    @patch("trips.views.geoapify.route")
    @patch("trips.views.geoapify.geocode")
    def test_success_returns_route(self, mock_geocode, mock_route):
        mock_geocode.return_value = {
            "lat": 41.0, "lon": -87.0, "formatted": "X", "city": "X", "state_code": "IL",
        }
        mock_route.return_value = {
            "geometry": [[-87.0, 41.0], [-90.0, 38.0]],
            "distance_m": 482575.0, "distance_mi": 299.9,
            "time_s": 16779.0, "time_hr": 4.66, "legs": [],
        }
        response = self.client.post(
            "/api/route/", self.VALID_INPUT, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("route", body)
        self.assertIn("locations", body)
        self.assertEqual(mock_geocode.call_count, 3)
        self.assertEqual(mock_route.call_count, 1)


class TripEndpointTests(TestCase):
    def setUp(self):
        cache.clear()

    VALID_INPUT = {
        "current_location": "Chicago, IL",
        "pickup_location": "Springfield, IL",
        "dropoff_location": "St. Louis, MO",
        "current_cycle_used": 10,
    }

    @patch("trips.views.geoapify.reverse_geocode_many")
    @patch("trips.views.geoapify.route")
    @patch("trips.views.geoapify.geocode")
    def test_trip_returns_days_stops_summary(self, mock_geocode, mock_route, mock_reverse):
        mock_geocode.return_value = {
            "lat": 40.0, "lon": -89.0, "formatted": "X", "city": "X", "state_code": "IL",
        }
        mock_route.return_value = {
            "geometry": [[-87.6, 41.9], [-89.6, 39.8], [-90.2, 38.6]],
            "distance_m": 482575.0, "distance_mi": 300.0,
            "time_s": 18000.0, "time_hr": 5.0,
            "legs": [
                {"distance_m": 1, "distance_mi": 200.0, "time_s": 1, "time_hr": 3.3},
                {"distance_m": 1, "distance_mi": 100.0, "time_s": 1, "time_hr": 1.7},
            ],
        }
        mock_reverse.return_value = {}

        response = self.client.post(
            "/api/trip/", self.VALID_INPUT, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("days", body)
        self.assertIn("stops", body)
        self.assertIn("summary", body)
        # Every day must cover a full 24 hours.
        for day in body["days"]:
            self.assertAlmostEqual(sum(day["totals"].values()), 24.0, places=1)
        self.assertEqual(body["stops"][0]["kind"], "start")

    @patch("trips.views.geoapify.geocode")
    def test_trip_geocode_failure_returns_404(self, mock_geocode):
        mock_geocode.side_effect = geoapify.GeocodingError("not found")
        response = self.client.post(
            "/api/trip/", self.VALID_INPUT, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
