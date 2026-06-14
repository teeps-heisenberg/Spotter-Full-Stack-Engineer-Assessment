from datetime import datetime

from django.test import SimpleTestCase

from .services import planner
from .services.planner import (
    DRIVE_BEFORE_BREAK,
    DRIVING,
    MAX_DRIVE_PER_WINDOW,
    MAX_WINDOW,
    OFF_DUTY,
    ON_DUTY,
    SLEEPER,
)

START = datetime(2025, 1, 6, 8, 0)  # a fixed Monday 8:00 AM for deterministic tests
# A simple straight-line route (lon, lat) from Chicago-ish to St-Louis-ish.
GEOMETRY = [[-87.6, 41.9], [-89.6, 39.8], [-90.2, 38.6]]


def make_legs(leg0_mi, leg0_hr, leg1_mi=0.0, leg1_hr=0.0):
    return [
        {"distance_mi": leg0_mi, "time_hr": leg0_hr},
        {"distance_mi": leg1_mi, "time_hr": leg1_hr},
    ]


def kinds(segs):
    return [s.kind for s in segs]


def total_driving_hr(segs):
    return sum(s.duration_hr for s in segs if s.status == DRIVING)


class PlannerBasicTests(SimpleTestCase):
    def test_short_trip_one_day_no_break_no_rest(self):
        # 200 + 100 mi, ~5 h driving total -> under 8 h, no break; under 11 h, no rest.
        segs = planner.plan_trip(
            legs=make_legs(200, 3.3, 100, 1.7),
            geometry=GEOMETRY,
            current_cycle_used=10,
            start_dt=START,
        )
        ks = kinds(segs)
        self.assertNotIn("break", ks)
        self.assertNotIn("rest", ks)
        self.assertEqual(ks.count("pickup"), 1)
        self.assertEqual(ks.count("dropoff"), 1)
        self.assertAlmostEqual(total_driving_hr(segs), 5.0, places=1)

    def test_pickup_and_dropoff_are_on_duty_one_hour(self):
        segs = planner.plan_trip(
            legs=make_legs(120, 2.0),
            geometry=GEOMETRY,
            current_cycle_used=0,
            start_dt=START,
        )
        pickup = next(s for s in segs if s.kind == "pickup")
        dropoff = next(s for s in segs if s.kind == "dropoff")
        self.assertEqual(pickup.status, ON_DUTY)
        self.assertEqual(dropoff.status, ON_DUTY)
        self.assertAlmostEqual(pickup.duration_hr, 1.0)
        self.assertAlmostEqual(dropoff.duration_hr, 1.0)

    def test_thirty_minute_break_after_eight_driving_hours(self):
        # ~10 h of driving in one leg -> one 30-min break, no daily reset (10 < 11).
        segs = planner.plan_trip(
            legs=make_legs(500, 10.0),
            geometry=GEOMETRY,
            current_cycle_used=0,
            start_dt=START,
        )
        breaks = [s for s in segs if s.kind == "break"]
        self.assertEqual(len(breaks), 1)
        self.assertEqual(breaks[0].status, OFF_DUTY)
        self.assertNotIn("rest", kinds(segs))
        # The break should land right around the 8th driving hour.
        driving_before_break = sum(
            s.duration_hr for s in segs[: segs.index(breaks[0])] if s.status == DRIVING
        )
        self.assertAlmostEqual(driving_before_break, DRIVE_BEFORE_BREAK, places=2)

    def test_long_drive_forces_daily_reset_and_spills_to_next_day(self):
        # 700 mi @ 50 mph = 14 h driving -> exceeds 11 h limit -> a 10-h sleeper reset.
        segs = planner.plan_trip(
            legs=make_legs(700, 14.0),
            geometry=GEOMETRY,
            current_cycle_used=0,
            start_dt=START,
        )
        rests = [s for s in segs if s.kind == "rest"]
        self.assertGreaterEqual(len(rests), 1)
        self.assertEqual(rests[0].status, SLEEPER)
        self.assertAlmostEqual(rests[0].duration_hr, 10.0)
        # Trip clearly spans more than one calendar day.
        self.assertGreater((segs[-1].end - segs[0].start).days, 0)

    def test_fuel_stop_inserted_every_thousand_miles(self):
        # 1500 mi -> one fuel stop (at ~1000 mi); 2200 mi -> two.
        segs1 = planner.plan_trip(
            legs=make_legs(1500, 25.0), geometry=GEOMETRY, current_cycle_used=0, start_dt=START
        )
        self.assertEqual(kinds(segs1).count("fuel"), 1)

        segs2 = planner.plan_trip(
            legs=make_legs(2200, 38.0), geometry=GEOMETRY, current_cycle_used=0, start_dt=START
        )
        self.assertEqual(kinds(segs2).count("fuel"), 2)

    def test_high_cycle_used_triggers_restart(self):
        # Only 1 h of cycle left, but ~6 h of driving needed -> a 34-h restart appears.
        segs = planner.plan_trip(
            legs=make_legs(300, 6.0),
            geometry=GEOMETRY,
            current_cycle_used=69,
            start_dt=START,
        )
        restarts = [s for s in segs if s.kind == "restart"]
        self.assertEqual(len(restarts), 1)
        self.assertEqual(restarts[0].status, OFF_DUTY)
        self.assertAlmostEqual(restarts[0].duration_hr, 34.0)

    def test_segments_are_contiguous(self):
        segs = planner.plan_trip(
            legs=make_legs(900, 16.0), geometry=GEOMETRY, current_cycle_used=20, start_dt=START
        )
        for a, b in zip(segs, segs[1:]):
            self.assertEqual(a.end, b.start)


class PlannerInvariantTests(SimpleTestCase):
    """No generated plan may ever violate the HOS limits."""

    def _assert_no_violation(self, segs, cycle_start):
        drove_window = drove_break = window_elapsed = 0.0
        cycle = cycle_start
        for s in segs:
            dur = s.duration_hr
            if s.kind in ("rest", "restart"):
                drove_window = drove_break = window_elapsed = 0.0
                if s.kind == "restart":
                    cycle = 0.0
                continue
            if s.status == DRIVING:
                drove_window += dur
                drove_break += dur
                window_elapsed += dur
                cycle += dur
                self.assertLessEqual(drove_window, MAX_DRIVE_PER_WINDOW + 1e-3)
                self.assertLessEqual(window_elapsed, MAX_WINDOW + 1e-3)
                self.assertLessEqual(drove_break, DRIVE_BEFORE_BREAK + 1e-3)
                self.assertLessEqual(cycle, 70.0 + 1e-3)
            elif s.status == ON_DUTY:
                window_elapsed += dur
                cycle += dur
            elif s.status == OFF_DUTY:
                window_elapsed += dur
                if dur >= 0.5 - 1e-9:
                    drove_break = 0.0

    def test_invariants_across_many_trip_lengths(self):
        for miles in (50, 150, 400, 650, 1000, 1400, 2000, 3000):
            for cycle in (0, 30, 55, 68):
                segs = planner.plan_trip(
                    legs=make_legs(miles * 0.6, miles * 0.6 / 55, miles * 0.4, miles * 0.4 / 55),
                    geometry=GEOMETRY,
                    current_cycle_used=cycle,
                    start_dt=START,
                )
                self._assert_no_violation(segs, cycle)
                # Every plan ends with a drop-off and contains exactly one pickup.
                self.assertEqual(kinds(segs).count("pickup"), 1)
                self.assertEqual(segs[-1].kind, "dropoff")
