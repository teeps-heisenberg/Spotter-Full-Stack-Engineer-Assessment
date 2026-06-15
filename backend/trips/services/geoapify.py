"""Thin server-side client for the Geoapify geocoding + routing APIs.

Why this lives on the backend:
  * keeps the Geoapify API key secret (never shipped to the browser),
  * lets us cache results so a trip costs ~1 set of external calls, and
  * gives us one place to normalise Geoapify's response into the shape the
    HOS planner and the frontend actually want.

All distances are returned in BOTH meters (raw) and miles (derived); all
durations in BOTH seconds (raw) and hours (derived).
"""

from __future__ import annotations

import hashlib

import requests
from django.conf import settings
from django.core.cache import cache

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
REVERSE_URL = "https://api.geoapify.com/v1/geocode/reverse"
ROUTING_URL = "https://api.geoapify.com/v1/routing"

METERS_PER_MILE = 1609.344
REQUEST_TIMEOUT = 12  # seconds (geocode/route)
# Reverse-geocode runs once per stop; keep it short so a slow one degrades to a
# coordinate fallback rather than blowing the whole request's time budget.
REVERSE_TIMEOUT = 6

# Cache results for a day. Geocodes/routes for the same input never change in a
# session, so this keeps us well under the free-tier rate limit.
CACHE_TTL = 60 * 60 * 24


class GeoapifyError(Exception):
    """Base error for any Geoapify interaction."""


class GeocodingError(GeoapifyError):
    """Raised when an address cannot be geocoded."""


class RoutingError(GeoapifyError):
    """Raised when a route cannot be computed."""


def _api_key() -> str:
    key = settings.GEOAPIFY_API_KEY
    if not key:
        raise GeoapifyError("GEOAPIFY_API_KEY is not configured.")
    return key


def _cache_key(namespace: str, value: str) -> str:
    """Build a backend-safe cache key (no spaces/colons in the variable part)."""
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    return f"geoapify:{namespace}:{digest}"


def geocode(text: str) -> dict:
    """Resolve a free-text US location to coordinates.

    Returns ``{lat, lon, formatted, city, state_code}``.
    Raises ``GeocodingError`` if the location cannot be found.
    """
    query = (text or "").strip()
    if not query:
        raise GeocodingError("Location text is empty.")

    cache_key = _cache_key("geocode", query.lower())
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            GEOCODE_URL,
            params={
                "text": query,
                "filter": "countrycode:us",
                "limit": 1,
                "apiKey": _api_key(),
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise GeocodingError(f"Geocoding request failed: {exc}") from exc

    features = response.json().get("features") or []
    if not features:
        raise GeocodingError(f"Could not find a US location for '{query}'.")

    props = features[0]["properties"]
    if props.get("lat") is None or props.get("lon") is None:
        raise GeocodingError(f"Geocoding returned no coordinates for '{query}'.")

    result = {
        "lat": props["lat"],
        "lon": props["lon"],
        "formatted": props.get("formatted", query),
        "city": props.get("city") or props.get("county") or props.get("state"),
        "state_code": props.get("state_code"),
    }
    cache.set(cache_key, result, CACHE_TTL)
    return result


def reverse_geocode(lat: float, lon: float) -> str:
    """Resolve coordinates to a short ``"City, ST"`` label for log remarks.

    Best-effort: on any failure it falls back to rounded coordinates so the
    planner output is never blocked by a labelling hiccup. Cached by rounded
    coordinates to keep us within the free-tier call budget.
    """
    fallback = f"{lat:.3f}, {lon:.3f}"
    cache_key = _cache_key("reverse", f"{lat:.3f},{lon:.3f}")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            REVERSE_URL,
            params={"lat": lat, "lon": lon, "apiKey": _api_key()},
            timeout=REVERSE_TIMEOUT,
        )
        response.raise_for_status()
        features = response.json().get("features") or []
        if not features:
            return fallback
        props = features[0]["properties"]
        # Most specific sensible place name; skip empty / single-char junk.
        place = None
        for key in ("city", "town", "village", "municipality", "suburb", "county"):
            value = props.get(key)
            if value and len(value.strip()) > 2:
                place = value.strip()
                break
        place = place or props.get("state")
        state = props.get("state_code") or props.get("state")
        label = ", ".join(part for part in (place, state) if part) or fallback
    except (requests.RequestException, GeoapifyError):
        return fallback

    cache.set(cache_key, label, CACHE_TTL)
    return label


def route(coordinates: list[tuple[float, float]]) -> dict:
    """Compute a driving route through ordered ``(lat, lon)`` waypoints.

    Returns a normalised dict::

        {
            "geometry": [[lon, lat], ...],   # one flattened LineString
            "distance_m": float, "distance_mi": float,
            "time_s": float,     "time_hr": float,
            "legs": [{"distance_m","distance_mi","time_s","time_hr"}, ...],
        }

    Geoapify returns geometry as a MultiLineString with one sub-line per leg;
    we concatenate the sub-lines into a single LineString. Raises
    ``RoutingError`` on failure.
    """
    if len(coordinates) < 2:
        raise RoutingError("At least two waypoints are required to build a route.")

    waypoints = "|".join(f"{lat},{lon}" for lat, lon in coordinates)
    cache_key = _cache_key("route", waypoints)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            ROUTING_URL,
            params={"waypoints": waypoints, "mode": "drive", "apiKey": _api_key()},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RoutingError(f"Routing request failed: {exc}") from exc

    features = response.json().get("features") or []
    if not features:
        raise RoutingError("No route found between the given locations.")

    feature = features[0]
    props = feature["properties"]
    geometry = feature["geometry"]

    # Flatten MultiLineString -> single list of [lon, lat] points.
    if geometry["type"] == "MultiLineString":
        flat = [point for line in geometry["coordinates"] for point in line]
    else:  # LineString fallback
        flat = list(geometry["coordinates"])

    distance_m = float(props["distance"])
    time_s = float(props["time"])
    legs = [
        {
            "distance_m": float(leg["distance"]),
            "distance_mi": float(leg["distance"]) / METERS_PER_MILE,
            "time_s": float(leg["time"]),
            "time_hr": float(leg["time"]) / 3600.0,
        }
        for leg in props.get("legs", [])
    ]

    result = {
        "geometry": flat,
        "distance_m": distance_m,
        "distance_mi": distance_m / METERS_PER_MILE,
        "time_s": time_s,
        "time_hr": time_s / 3600.0,
        "legs": legs,
    }
    cache.set(cache_key, result, CACHE_TTL)
    return result
