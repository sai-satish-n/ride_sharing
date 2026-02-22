from rest_framework import serializers
from drivers.models import Driver
from authentication.models import User

class DriverUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
        ]


class DriverSerializer(serializers.ModelSerializer):
    user = DriverUserSerializer(read_only=True)
    driver_online_status = serializers.StringRelatedField()

    class Meta:
        model = Driver
        fields = [
            "driver_id",
            "user",
            "driving_licence_number",
            "driver_rating",
            "driver_online_status",
            "current_latitude",
            "current_longitude",
            "last_location",
            "location_updated_at",
            "created_at"
        ]