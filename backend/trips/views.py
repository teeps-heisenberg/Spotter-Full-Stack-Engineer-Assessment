from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import TripInputSerializer
from .services import geoapify


@api_view(["GET"])
def health(request):
    """Simple liveness check used to confirm the API is up."""
    return Response({"status": "ok", "service": "spotter-eld-backend"})


@api_view(["POST"])
def route(request):
    """Geocode the three trip locations and return the driving route.

    This is the Part 1 endpoint: it proves the geocode + routing pipeline
    end-to-end. The HOS planner (Part 2) and per-day logs (Part 3) build on
    the same geocode/route results.
    """
    serializer = TripInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Geocode each location; report which one failed so the UI can guide the user.
    locations = {}
    for field in ("current_location", "pickup_location", "dropoff_location"):
        try:
            locations[field] = geoapify.geocode(data[field])
        except geoapify.GeocodingError as exc:
            return Response(
                {"error": str(exc), "field": field},
                status=status.HTTP_404_NOT_FOUND,
            )

    waypoints = [
        (locations["current_location"]["lat"], locations["current_location"]["lon"]),
        (locations["pickup_location"]["lat"], locations["pickup_location"]["lon"]),
        (locations["dropoff_location"]["lat"], locations["dropoff_location"]["lon"]),
    ]

    try:
        route_result = geoapify.route(waypoints)
    except geoapify.GeoapifyError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(
        {
            "input": {
                "current_location": data["current_location"],
                "pickup_location": data["pickup_location"],
                "dropoff_location": data["dropoff_location"],
                "current_cycle_used": data["current_cycle_used"],
            },
            "locations": locations,
            "route": route_result,
        }
    )
