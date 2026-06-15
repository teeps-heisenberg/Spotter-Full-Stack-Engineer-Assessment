"""Turn a flat HOS timeline into per-day log sheets + map stops (pure).

``build_trip`` takes the ``Segment`` list from the planner and produces the
JSON-ready structure the frontend renders:

  * ``days``    — one entry per calendar day, each covering a full 24 hours
                  (padded with off-duty before the trip starts and after it
                  ends), with per-status totals that sum to 24, miles driven
                  that day, and the remarks (duty-change annotations).
  * ``stops``   — the non-driving events (pickup, fuel, breaks, rests,
                  drop-off) plus the trip start, as map markers.
  * ``summary`` — trip-level totals.

Segments that cross midnight are split so each piece belongs to exactly one
day. Location labels come from an injected ``resolve_label(lat, lon)`` callable
(the view passes a cached reverse-geocoder); this keeps the module network-free
and unit-testable.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Callable

from .planner import DRIVING, OFF_DUTY, ON_DUTY, SLEEPER, Segment

EVENT_KINDS = {"fuel", "break", "rest", "restart", "pickup", "dropoff"}
STATUS_KEYS = (OFF_DUTY, SLEEPER, DRIVING, ON_DUTY)


def _segment_miles(segments: list[Segment]) -> list[float]:
    """Miles covered by each segment (driving segments only)."""
    miles = [0.0] * len(segments)
    for i, seg in enumerate(segments):
        if seg.status == DRIVING:
            nxt = segments[i + 1].start_mile if i + 1 < len(segments) else seg.start_mile
            miles[i] = max(0.0, nxt - seg.start_mile)
    return miles


def _midnight_after(dt: datetime) -> datetime:
    return datetime.combine(dt.date() + timedelta(days=1), time(0, 0))


def _split_at_midnight(seg: Segment, miles: float) -> list[dict]:
    """Break a segment into one piece per calendar day it touches."""
    pieces: list[dict] = []
    total = (seg.end - seg.start).total_seconds()
    cursor = seg.start
    first = True
    while cursor < seg.end:
        piece_end = min(seg.end, _midnight_after(cursor))
        frac = ((piece_end - cursor).total_seconds() / total) if total > 0 else 0.0
        pieces.append(
            {
                "date": cursor.date(),
                "status": seg.status,
                "start": cursor,
                "end": piece_end,
                "kind": seg.kind,
                "remark": seg.remark,
                "lat": seg.lat,
                "lon": seg.lon,
                "miles": miles * frac,
                "continuation": not first,
            }
        )
        cursor = piece_end
        first = False
    return pieces


def _pad_piece(status: str, start: datetime, end: datetime) -> dict:
    return {
        "date": start.date(),
        "status": status,
        "start": start,
        "end": end,
        "kind": "off",
        "remark": "Off duty",
        "lat": None,
        "lon": None,
        "miles": 0.0,
        "continuation": True,  # padding is never a logged duty change
    }


def build_trip(
    segments: list[Segment],
    resolve_labels: Callable[[list[tuple[float, float]]], dict] | None = None,
) -> dict:
    if not segments:
        return {"days": [], "stops": [], "summary": {}}

    # Only the displayed points get labels: the trip start + non-driving events
    # (these are the stops and the remark annotations). Driving segments don't
    # need a label, so we never reverse-geocode them — far fewer API calls.
    needed = [(segments[0].lat, segments[0].lon)]
    needed += [(s.lat, s.lon) for s in segments if s.kind in EVENT_KINDS]
    label_map = resolve_labels(needed) if resolve_labels else {}

    def label_for(lat: float | None, lon: float | None) -> str | None:
        if lat is None or lon is None:
            return None
        return label_map.get((round(lat, 3), round(lon, 3)))

    miles = _segment_miles(segments)
    trip_start = segments[0].start
    trip_end = segments[-1].end

    # Build the full ordered list of day-pieces, padded to whole days.
    pieces: list[dict] = []
    day_start = datetime.combine(trip_start.date(), time(0, 0))
    if trip_start > day_start:
        pieces.append(_pad_piece(OFF_DUTY, day_start, trip_start))
    for seg, m in zip(segments, miles):
        pieces.extend(_split_at_midnight(seg, m))
    last_midnight = _midnight_after(trip_end)
    if trip_end < last_midnight:
        pieces.append(_pad_piece(OFF_DUTY, trip_end, last_midnight))

    # Group pieces by calendar day.
    days: list[dict] = []
    current_date = None
    for piece in pieces:
        if piece["date"] != current_date:
            current_date = piece["date"]
            days.append({"date": current_date, "_pieces": []})
        days[-1]["_pieces"].append(piece)

    out_days = []
    for day in days:
        day_pieces = day["_pieces"]
        totals = {key: 0.0 for key in STATUS_KEYS}
        day_miles = 0.0
        remarks = []
        seg_dicts = []
        for piece in day_pieces:
            dur = (piece["end"] - piece["start"]).total_seconds() / 3600.0
            totals[piece["status"]] += dur
            day_miles += piece["miles"]
            label = label_for(piece["lat"], piece["lon"])
            seg_dicts.append(
                {
                    "status": piece["status"],
                    "start": piece["start"].isoformat(),
                    "end": piece["end"].isoformat(),
                    "duration_hr": round(dur, 4),
                    "kind": piece["kind"],
                    "remark": piece["remark"],
                    "label": label,
                    "lat": piece["lat"],
                    "lon": piece["lon"],
                }
            )
            # A logged remark is written at each real duty change (not on
            # midnight continuations or padding, and not on resume-driving).
            if not piece["continuation"]:
                is_trip_start = piece["kind"] == "drive" and piece["start"] == trip_start
                if is_trip_start:
                    remarks.append(
                        {"time": piece["start"].isoformat(), "label": label, "note": "Trip start"}
                    )
                elif piece["kind"] in EVENT_KINDS:
                    remarks.append(
                        {"time": piece["start"].isoformat(), "label": label, "note": piece["remark"]}
                    )

        out_days.append(
            {
                "date": day["date"].isoformat(),
                "segments": seg_dicts,
                "totals": {key: round(totals[key], 4) for key in STATUS_KEYS},
                "total_miles": round(day_miles, 1),
                "remarks": remarks,
            }
        )

    # Map stops: trip start + every non-driving event.
    stops = [
        {
            "kind": "start",
            "status": segments[0].status,
            "time": trip_start.isoformat(),
            "lat": segments[0].lat,
            "lon": segments[0].lon,
            "label": label_for(segments[0].lat, segments[0].lon),
            "remark": "Trip start",
        }
    ]
    for seg in segments:
        if seg.kind in EVENT_KINDS:
            stops.append(
                {
                    "kind": seg.kind,
                    "status": seg.status,
                    "time": seg.start.isoformat(),
                    "lat": seg.lat,
                    "lon": seg.lon,
                    "label": label_for(seg.lat, seg.lon),
                    "remark": seg.remark,
                }
            )

    summary = {
        "start": trip_start.isoformat(),
        "end": trip_end.isoformat(),
        "total_days": len(out_days),
        "total_distance_mi": round(sum(miles), 1),
        "total_driving_hr": round(
            sum(s.duration_hr for s in segments if s.status == DRIVING), 2
        ),
        "total_on_duty_hr": round(
            sum(s.duration_hr for s in segments if s.status == ON_DUTY), 2
        ),
    }

    return {"days": out_days, "stops": stops, "summary": summary}
