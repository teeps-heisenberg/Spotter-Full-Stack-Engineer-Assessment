import socket
import time

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import TripInputSerializer
from .services import geoapify, logsheet, planner


@api_view(["GET"])
def health(request):
    """Simple liveness check used to confirm the API is up."""
    return Response({"status": "ok", "service": "spotter-eld-backend"})


@api_view(["GET"])
def diag(request):
    """Diagnostic: isolate outbound connectivity to Geoapify (timed)."""
    out = {"key_set": bool(settings.GEOAPIFY_API_KEY)}

    # 1) DNS resolution (the part requests' timeout does NOT cover).
    t0 = time.time()
    try:
        ip = socket.gethostbyname("api.geoapify.com")
        out["dns"] = {"ok": True, "ip": ip, "elapsed_s": round(time.time() - t0, 2)}
    except Exception as exc:
        out["dns"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                      "elapsed_s": round(time.time() - t0, 2)}

    # 2) A single geocode HTTP call.
    t1 = time.time()
    try:
        r = requests.get(
            "https://api.geoapify.com/v1/geocode/search",
            params={"text": "Chicago, IL", "filter": "countrycode:us", "limit": 1,
                    "apiKey": settings.GEOAPIFY_API_KEY},
            timeout=10,
        )
        out["geocode"] = {"status": r.status_code, "elapsed_s": round(time.time() - t1, 2),
                          "has_features": bool(r.json().get("features"))}
    except Exception as exc:
        out["geocode"] = {"error": f"{type(exc).__name__}: {exc}",
                          "elapsed_s": round(time.time() - t1, 2)}

    return Response(out)


def _geocode_and_route(data):
    """Shared pipeline: geocode the 3 inputs + compute the route.

    Returns ``(locations, route_result, error_response)``. If ``error_response``
    is not None the caller should return it directly.
    """
    locations = {}
    for field in ("current_location", "pickup_location", "dropoff_location"):
        try:
            locations[field] = geoapify.geocode(data[field])
        except geoapify.GeocodingError as exc:
            return None, None, Response(
                {"error": str(exc), "field": field}, status=status.HTTP_404_NOT_FOUND
            )
        except geoapify.GeoapifyError as exc:
            # Config/upstream issue (e.g. missing API key) — return a clean
            # error (with CORS headers) instead of an unhandled 500.
            return None, None, Response(
                {"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY
            )

    waypoints = [
        (locations["current_location"]["lat"], locations["current_location"]["lon"]),
        (locations["pickup_location"]["lat"], locations["pickup_location"]["lon"]),
        (locations["dropoff_location"]["lat"], locations["dropoff_location"]["lon"]),
    ]
    try:
        route_result = geoapify.route(waypoints)
    except geoapify.GeoapifyError as exc:
        return None, None, Response(
            {"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY
        )

    return locations, route_result, None


@api_view(["POST"])
def route(request):
    """Geocode the three trip locations and return the driving route (Part 1)."""
    serializer = TripInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    locations, route_result, error = _geocode_and_route(data)
    if error is not None:
        return error

    return Response(
        {
            "input": dict(data),
            "locations": locations,
            "route": route_result,
        }
    )


@api_view(["POST"])
def trip(request):
    """Full trip plan: route + HOS schedule + per-day ELD log sheets (Part 3).

    Pipeline: geocode -> route -> HOS planner -> per-day log sheets, with stop
    locations reverse-geocoded (cached) for the log remarks and map markers.
    """
    serializer = TripInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    locations, route_result, error = _geocode_and_route(data)
    if error is not None:
        return error

    try:
        segments = planner.plan_trip(
            legs=route_result["legs"],
            geometry=route_result["geometry"],
            current_cycle_used=data["current_cycle_used"],
        )
        trip_data = logsheet.build_trip(
            segments, resolve_labels=geoapify.reverse_geocode_many
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        return Response(
            {"error": f"Failed to build the trip plan: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "input": dict(data),
            "locations": locations,
            "route": {
                "geometry": route_result["geometry"],
                "distance_mi": round(route_result["distance_mi"], 1),
                "time_hr": round(route_result["time_hr"], 2),
                "legs": route_result["legs"],
            },
            "stops": trip_data["stops"],
            "days": trip_data["days"],
            "summary": trip_data["summary"],
        }
    )
