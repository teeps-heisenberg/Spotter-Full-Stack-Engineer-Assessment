from datetime import datetime

from django.test import SimpleTestCase

from .services import logsheet, planner

START = datetime(2025, 1, 6, 8, 0)
GEOMETRY = [[-87.6, 41.9], [-92.0, 40.0], [-96.0, 39.0]]


def _stub_labels(coords):
    return {(round(lat, 3), round(lon, 3)): "Testville, IL" for lat, lon in coords}


def _build(miles_leg0, hr_leg0, miles_leg1, hr_leg1, cycle=0):
    segs = planner.plan_trip(
        legs=[
            {"distance_mi": miles_leg0, "time_hr": hr_leg0},
            {"distance_mi": miles_leg1, "time_hr": hr_leg1},
        ],
        geometry=GEOMETRY,
        current_cycle_used=cycle,
        start_dt=START,
    )
    return logsheet.build_trip(segs, resolve_labels=_stub_labels)


class DaySplitterTests(SimpleTestCase):
    def test_each_day_totals_sum_to_24(self):
        trip = _build(900, 16.0, 600, 11.0)  # multi-day
        self.assertGreater(len(trip["days"]), 1)
        for day in trip["days"]:
            self.assertAlmostEqual(sum(day["totals"].values()), 24.0, places=2)

    def test_first_day_padded_from_midnight_last_day_to_midnight(self):
        trip = _build(120, 2.0, 60, 1.0)  # single day
        day = trip["days"][0]
        self.assertTrue(day["segments"][0]["start"].endswith("T00:00:00"))
        self.assertTrue(day["segments"][-1]["end"].endswith("T00:00:00"))

    def test_short_trip_is_one_day(self):
        trip = _build(120, 2.0, 60, 1.0)
        self.assertEqual(len(trip["days"]), 1)
        self.assertEqual(trip["summary"]["total_days"], 1)

    def test_remarks_include_start_pickup_dropoff(self):
        trip = _build(120, 2.0, 60, 1.0)
        notes = [r["note"] for day in trip["days"] for r in day["remarks"]]
        self.assertIn("Trip start", notes)
        self.assertIn("Pickup (load)", notes)
        self.assertIn("Drop-off (unload)", notes)

    def test_remarks_have_labels(self):
        trip = _build(120, 2.0, 60, 1.0)
        for day in trip["days"]:
            for remark in day["remarks"]:
                self.assertEqual(remark["label"], "Testville, IL")

    def test_stops_include_start_and_dropoff(self):
        trip = _build(120, 2.0, 60, 1.0)
        kinds = [s["kind"] for s in trip["stops"]]
        self.assertEqual(kinds[0], "start")
        self.assertIn("pickup", kinds)
        self.assertIn("dropoff", kinds)

    def test_total_miles_per_day_sums_to_trip_distance(self):
        trip = _build(900, 16.0, 600, 11.0)
        day_miles = sum(day["total_miles"] for day in trip["days"])
        self.assertAlmostEqual(day_miles, trip["summary"]["total_distance_mi"], delta=1.0)

    def test_restart_scenario_spans_multiple_days_and_lists_restart_stop(self):
        # High cycle use -> a 34h restart -> trip spans extra days and the
        # restart shows up as a stop/marker.
        trip = _build(300, 6.0, 0, 0, cycle=69)
        self.assertGreaterEqual(trip["summary"]["total_days"], 2)
        self.assertIn("restart", [s["kind"] for s in trip["stops"]])

    def test_empty_segments_safe(self):
        self.assertEqual(logsheet.build_trip([]), {"days": [], "stops": [], "summary": {}})
