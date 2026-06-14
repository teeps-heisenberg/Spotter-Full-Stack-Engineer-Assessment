"""Hours-of-Service trip planner (pure, no network).

Given the per-leg distance/time of a route and the hours already used in the
driver's 70-hour/8-day cycle, this simulates the whole trip into a list of
duty-status ``Segment``s that, by construction, never violate the federal
property-carrier HOS rules:

  * 11 hours max driving per 14-hour window,
  * no driving after the 14th hour of a window (off-duty breaks don't pause it),
  * a 30-minute off-duty break before driving once 8 cumulative driving hours
    have passed since the last >=30-min off-duty/sleeper period,
  * 70 hours max on-duty in the rolling cycle (a 34-hour restart resets it),
  * a 10-hour daily reset opens a fresh window.

Trip-specific rules from the brief: 30-min on-duty fuel stop every <=1000 mi,
1 hour on-duty pickup, 1 hour on-duty drop-off. The clock starts at 8:00 AM.

The planner is deliberately network-free: stop coordinates are interpolated
along the route polyline so the logic can be tested without any API calls.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# --- Duty status values (shared with the frontend + log renderer) ---
OFF_DUTY = "off_duty"
SLEEPER = "sleeper"
DRIVING = "driving"
ON_DUTY = "on_duty"

# --- HOS limits (hours) ---
MAX_DRIVE_PER_WINDOW = 11.0
MAX_WINDOW = 14.0
DRIVE_BEFORE_BREAK = 8.0
BREAK_DURATION = 0.5
DAILY_RESET = 10.0
CYCLE_LIMIT = 70.0
RESTART_DURATION = 34.0

# --- Trip constants (from the brief / locked decisions) ---
FUEL_INTERVAL_MI = 1000.0
FUEL_DURATION = 0.5
PICKUP_DURATION = 1.0
DROPOFF_DURATION = 1.0
DEFAULT_START_HOUR = 8

# Fallback driving speed (mph) if a leg reports zero time.
DEFAULT_SPEED = 50.0
EPS = 1e-6
EARTH_RADIUS_MI = 3958.7613


@dataclass
class Segment:
    """One continuous stretch of a single duty status."""

    status: str
    start: datetime
    end: datetime
    kind: str  # start | drive | fuel | break | rest | restart | pickup | dropoff
    remark: str
    start_mile: float
    lat: float | None = None
    lon: float | None = None

    @property
    def duration_hr(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "kind": self.kind,
            "remark": self.remark,
            "duration_hr": round(self.duration_hr, 4),
            "start_mile": round(self.start_mile, 2),
            "lat": self.lat,
            "lon": self.lon,
        }


def _haversine_mi(a: list[float], b: list[float]) -> float:
    """Great-circle distance in miles between two ``[lon, lat]`` points."""
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


class _Route:
    """Lets us look up a ``(lat, lon)`` at any fraction along the polyline."""

    def __init__(self, geometry: list[list[float]]):
        self.geometry = geometry or [[0.0, 0.0]]
        self.cum = [0.0]
        for i in range(1, len(self.geometry)):
            self.cum.append(self.cum[-1] + _haversine_mi(self.geometry[i - 1], self.geometry[i]))
        self.total = self.cum[-1]

    def at_fraction(self, fraction: float) -> tuple[float, float]:
        fraction = min(max(fraction, 0.0), 1.0)
        if self.total <= 0 or len(self.geometry) < 2:
            lon, lat = self.geometry[0]
            return lat, lon
        target = fraction * self.total
        idx = bisect.bisect_left(self.cum, target)
        if idx <= 0:
            lon, lat = self.geometry[0]
            return lat, lon
        if idx >= len(self.geometry):
            lon, lat = self.geometry[-1]
            return lat, lon
        d0, d1 = self.cum[idx - 1], self.cum[idx]
        t = 0.0 if d1 == d0 else (target - d0) / (d1 - d0)
        lon0, lat0 = self.geometry[idx - 1]
        lon1, lat1 = self.geometry[idx]
        return lat0 + (lat1 - lat0) * t, lon0 + (lon1 - lon0) * t


@dataclass
class _State:
    now: datetime
    cycle_used: float
    window_start: datetime
    drove_window: float = 0.0
    drove_since_break: float = 0.0
    cum_miles: float = 0.0
    miles_since_fuel: float = 0.0


def plan_trip(
    *,
    legs: list[dict],
    geometry: list[list[float]],
    current_cycle_used: float,
    start_dt: datetime | None = None,
) -> list[Segment]:
    """Simulate the trip and return the ordered list of duty ``Segment``s.

    ``legs`` is ``[{distance_mi, time_hr}, ...]`` (leg 0 = current->pickup,
    leg 1 = pickup->dropoff), as produced by the route service.
    """
    if start_dt is None:
        start_dt = datetime.combine(date.today(), time(DEFAULT_START_HOUR, 0))

    route = _Route(geometry)
    total_miles = sum(leg["distance_mi"] for leg in legs) or EPS
    segments: list[Segment] = []
    state = _State(now=start_dt, cycle_used=float(current_cycle_used), window_start=start_dt)

    def coord_now() -> tuple[float, float]:
        return route.at_fraction(state.cum_miles / total_miles)

    def add(status: str, dur: float, kind: str, remark: str) -> None:
        lat, lon = coord_now()
        seg = Segment(
            status=status,
            start=state.now,
            end=state.now + timedelta(hours=dur),
            kind=kind,
            remark=remark,
            start_mile=state.cum_miles,
            lat=lat,
            lon=lon,
        )
        segments.append(seg)
        state.now = seg.end
        if status in (DRIVING, ON_DUTY):
            state.cycle_used += dur

    def insert_break() -> None:
        add(OFF_DUTY, BREAK_DURATION, "break", "30-minute break")
        state.drove_since_break = 0.0

    def insert_daily_reset() -> None:
        add(SLEEPER, DAILY_RESET, "rest", "10-hour rest")
        state.window_start = state.now
        state.drove_window = 0.0
        state.drove_since_break = 0.0

    def insert_restart() -> None:
        add(OFF_DUTY, RESTART_DURATION, "restart", "34-hour restart (cycle reset)")
        state.cycle_used = 0.0
        state.window_start = state.now
        state.drove_window = 0.0
        state.drove_since_break = 0.0

    def insert_fuel() -> None:
        add(ON_DUTY, FUEL_DURATION, "fuel", "Fuel stop")
        state.miles_since_fuel = 0.0

    def drive_leg(leg_miles: float, speed: float) -> None:
        remaining = leg_miles
        while remaining > EPS:
            window_elapsed = (state.now - state.window_start).total_seconds() / 3600.0
            avail_window = MAX_WINDOW - window_elapsed
            avail_11 = MAX_DRIVE_PER_WINDOW - state.drove_window
            avail_break = DRIVE_BEFORE_BREAK - state.drove_since_break
            avail_cycle = CYCLE_LIMIT - state.cycle_used

            # Forced stops, most-disruptive first.
            if avail_cycle <= EPS:
                insert_restart()
                continue
            if avail_window <= EPS or avail_11 <= EPS:
                insert_daily_reset()
                continue
            if avail_break <= EPS:
                insert_break()
                continue

            drivable_hr = min(avail_window, avail_11, avail_break, avail_cycle)
            miles_to_fuel = FUEL_INTERVAL_MI - state.miles_since_fuel
            chunk_miles = min(remaining, miles_to_fuel, drivable_hr * speed)
            chunk_hr = chunk_miles / speed

            add(DRIVING, chunk_hr, "drive", "Driving")
            state.cum_miles += chunk_miles
            state.miles_since_fuel += chunk_miles
            state.drove_window += chunk_hr
            state.drove_since_break += chunk_hr
            remaining -= chunk_miles

            # Refuel if we've hit the interval and there's still road ahead.
            if remaining > EPS and state.miles_since_fuel >= FUEL_INTERVAL_MI - EPS:
                insert_fuel()

    def leg_speed(leg: dict) -> float:
        return leg["distance_mi"] / leg["time_hr"] if leg.get("time_hr", 0) > 0 else DEFAULT_SPEED

    # current -> pickup -> (load 1h) -> dropoff -> (unload 1h)
    if legs:
        drive_leg(legs[0]["distance_mi"], leg_speed(legs[0]))
    add(ON_DUTY, PICKUP_DURATION, "pickup", "Pickup (load)")
    if len(legs) > 1:
        drive_leg(legs[1]["distance_mi"], leg_speed(legs[1]))
    add(ON_DUTY, DROPOFF_DURATION, "dropoff", "Drop-off (unload)")

    return segments
