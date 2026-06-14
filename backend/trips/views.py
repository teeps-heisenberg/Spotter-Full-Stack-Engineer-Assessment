from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    """Simple liveness check used to confirm the API is up."""
    return Response({"status": "ok", "service": "spotter-eld-backend"})
