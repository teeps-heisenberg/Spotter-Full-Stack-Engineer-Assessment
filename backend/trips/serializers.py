from rest_framework import serializers


class TripInputSerializer(serializers.Serializer):
    """Validates the four trip inputs from the brief."""

    current_location = serializers.CharField(max_length=255, trim_whitespace=True)
    pickup_location = serializers.CharField(max_length=255, trim_whitespace=True)
    dropoff_location = serializers.CharField(max_length=255, trim_whitespace=True)
    # Hours already used in the 70-hour / 8-day cycle before this trip starts.
    current_cycle_used = serializers.FloatField(min_value=0, max_value=70)
