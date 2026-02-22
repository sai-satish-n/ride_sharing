from rest_framework import serializers
from authentication.models import User
from rides.models import Ride, RideDetailsForRiders, RideStatusLookup, EventLog, Region, RideLocationLog, Driver, DriverRideRejection, RideCancellationLog, VehicleType, TenantRegion
import uuid
import secrets
from payments_module.models import RideFareSnapshot


def generate_otp():
    return secrets.randbelow(900000) + 100000


class BookRideSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    region_code = serializers.UUIDField()
    from_location = serializers.CharField()
    to_location = serializers.CharField()
    vehicle_type = serializers.IntegerField()
    ride_fare = serializers.FloatField()

    def create(self, validated_data):
        user = User.objects.get(user_id=validated_data["user_id"])
        region = Region.objects.get(region_code=validated_data["region_code"])
        booked_status = RideStatusLookup.objects.get(ride_status="BOOKED")
        vehicle_type = validated_data["vehicle_type"]
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
            ride_status=booked_status,
            vehicle_type_id = vehicle_type,
            ride_fare = validated_data["ride_fare"],
        )

        EventLog.objects.create(
            ride=ride,
            ride_status=booked_status
        )

        return ride, otp


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
        driver_id = validated_data.pop("driver_id")  # remove driver_id from data
        driver = Driver.objects.get(pk=driver_id)    # fetch the Driver instance
        return RideLocationLog.objects.create(driver=driver, **validated_data)
    
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
        driver_id = validated_data.pop("driver_id")  # remove driver_id from data
        driver = Driver.objects.get(user_id=driver_id)    # fetch the Driver instance

        ride_id = validated_data.pop("ride_id")  # remove driver_id from data
        ride = Ride.objects.get(pk=ride_id) 

        return DriverRideRejection.objects.create(driver=driver, ride=ride, **validated_data)


class RideDetailsForRidersSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideDetailsForRiders
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class FareBreakupSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideFareSnapshot
        fields = ['base_fare', 'distance_fare', 'time_fare', 'surge_multiplier', 'tax_amount', 'final_fare']


class AddExtraAmountSerializer(serializers.Serializer):
    ride_id = serializers.UUIDField()
    rider_id = serializers.UUIDField()
    extra_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value