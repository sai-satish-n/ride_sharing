from rest_framework import serializers
from authentication.models import User
from rides.models import Ride, RideDetailsForRiders, RideStatusLookup, EventLog, Region, RideLocationLog, Driver, DriverRideRejection, RideCancellationLog
import uuid
import secrets


def generate_otp():
    return secrets.randbelow(900000) + 100000


class BookRideSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    region_code = serializers.UUIDField()
    from_location = serializers.IntegerField()
    to_location = serializers.IntegerField()

    def create(self, validated_data):
        user = User.objects.get(user_id=validated_data["user_id"])
        region = Region.objects.get(region_code=validated_data["region_code"])
        booked_status = RideStatusLookup.objects.get(ride_status="BOOKED")
        otp = secrets.randbelow(900000) + 100000

        ride = Ride.objects.create(
            ride_id=uuid.uuid4(),
            region=region,
            currency_code=region.country.currency_code,
            timezone=region.country.default_timezone
        )

        RideDetailsForRiders.objects.create(
            ride=ride,
            rider=user,
            otp=otp,
            from_location=validated_data["from_location"],
            to_location=validated_data["to_location"],
            ride_status=booked_status
        )

        EventLog.objects.create(
            ride=ride,
            ride_status=booked_status
        )

        return ride, otp


class AvailableRideSerializer(serializers.ModelSerializer):
    ride_id = serializers.UUIDField(source="ride.ride_id")
    region = serializers.CharField(source="ride.region.region_name")

    class Meta:
        model = RideDetailsForRiders
        fields = [
            "ride_id",
            "from_location",
            "to_location",
            "region",
            "created_at"
        ]


class RideLocationLogSerializer(serializers.ModelSerializer):
    driver_id = serializers.UUIDField(write_only=True)
    class Meta:
        model = RideLocationLog
        fields = [
            "ride",
            "latitude",
            "longitude",
            "heading_towards",
            "h3_index",
            "speed",
            "driver_id"
        ]

    def create(self, validated_data):
        print("data for validation", validated_data)
        driver_id = validated_data.pop("driver_id")  # remove driver_id from data
        driver = Driver.objects.get(pk=driver_id)    # fetch the Driver instance
        return RideLocationLog.objects.create(driver=driver, **validated_data)


class RideCancellationSerializer(serializers.Serializer):
    ride_id = serializers.UUIDField()
    role_name = serializers.CharField()
    user_id = serializers.UUIDField(required=False)    # optional if role=user
    driver_id = serializers.UUIDField(required=False)  # optional if role=driver
    reason = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        ride_id = validated_data.pop("ride_id")
        role_name = validated_data.pop("role_name").lower()
        reason = validated_data.pop("reason", None)

        ride = Ride.objects.get(ride_id=ride_id)
        

        cancelled_by = None
        cancelled_by_driver = None

        if role_name == "user":
            user_id = validated_data.pop("user_id")
            cancelled_by = User.objects.get(pk=user_id)
            ride_detail = RideDetailsForRiders.objects.get(ride_id=ride_id, rider=User.objects.get(user_id=user_id))
            ride_detail.ride_status = RideStatusLookup.objects.get(ride_status_id=7)
            ride_detail.save()
        else:
            driver_id = validated_data.pop("driver_id")
            cancelled_by_driver = Driver.objects.get(pk=driver_id)

        return RideCancellationLog.objects.create(
            ride=ride,
            cancelled_by=cancelled_by,
            cancelled_by_driver=cancelled_by_driver,
            reason=reason
        )
    
    
class RejectRideSerializer(serializers.Serializer):
    ride_id = serializers.UUIDField(write_only=True)
    driver_id = serializers.UUIDField(write_only=True)
    class Meta:
        model = DriverRideRejection
        fields = [
            "ride_id",
            "driver_id"
        ]

    def create(self, validated_data):
        print("data for validation", validated_data)
        driver_id = validated_data.pop("driver_id")  # remove driver_id from data
        driver = Driver.objects.get(pk=driver_id)    # fetch the Driver instance

        ride_id = validated_data.pop("ride_id")  # remove driver_id from data
        ride = Ride.objects.get(pk=ride_id) 

        return DriverRideRejection.objects.create(driver=driver, ride=ride, **validated_data)


class RideDetailsForRidersSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideDetailsForRiders
        fields = '__all__'