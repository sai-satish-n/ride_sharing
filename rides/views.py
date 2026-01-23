from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rides.serializers import *
from drivers.models import Driver, VehicleDriverAssignment
from rides.models import RideCancellationLog
from rides.serializers import RideCancellationSerializer, RejectRideSerializer
from django.utils import timezone
import h3
from rides.models import RideDetailsForRiders, RideStatusLookup
import json

def get_nearby_rides_for_driver(driver, k_ring=3, target_res=9):
    """
    Returns nearby BOOKED rides for a driver using H3 proximity,
    excluding rides already rejected by the driver
    """

    if not driver.current_h3_index:
        return RideDetailsForRiders.objects.none()

    # driver_h3_index = h3.int_to_str(driver.current_h3_index)
    driver_h3_index = h3.cell_to_parent(driver.current_h3_index, target_res)
    nearby_cells = list(h3.grid_disk(driver_h3_index, k_ring))

    booked_status = RideStatusLookup.objects.get(
        ride_status="BOOKED"
    )

    rejected_rides = DriverRideRejection.objects.filter(
        driver=driver
    ).values_list("ride_id", flat=True)

    rides = (
        RideDetailsForRiders.objects
        .filter(
            ride_status=booked_status,
            from_location__in=nearby_cells
        )
        .exclude(ride_id__in=rejected_rides)
        .select_related("ride", "rider")
        .order_by("created_at")
    )

    return rides


class BookRideView(APIView):
    def post(self, request):
        serializer = BookRideSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        ride, otp = serializer.save()


        return Response(
            {
                "ride_id": ride.ride_id,
                "status": "BOOKED",
                "from_location": ride.timezone,
                "otp": otp
            },
            status=status.HTTP_201_CREATED
        )
    

class AvailableRidesForDriverView(APIView):

    def post(self, request):
        driver_id = request.data.get("driver_id")

        if not driver_id:
            return Response(
                {"error": "driver_id is required"},
                status=400
            )

        driver = Driver.objects.get(driver_id=driver_id)

        rides = get_nearby_rides_for_driver(
            driver=driver,
            k_ring=1  # tune this (1–3)
        )

        serializer = AvailableRideSerializer(rides, many=True)
        return Response(serializer.data)
    

class AcceptRideView(APIView):

    def post(self, request):
        ride_id = request.data.get("ride_id")
        otp = request.data.get("otp")
        driver_id = request.data.get("driver_id")

        if not all([ride_id, otp, driver_id]):
            return Response(
                {"error": "ride_id, otp and driver_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        driver = Driver.objects.get(driver_id=driver_id)

        with transaction.atomic():
            details = RideDetailsForRiders.objects.select_for_update().get(
                ride_id=ride_id
            )

            if details.ride_status.ride_status != "BOOKED":
                return Response(
                    {"error": "Ride already accepted"},
                    status=status.HTTP_409_CONFLICT
                )

            if details.verification_status:
                return Response(
                    {"error": "OTP already verified"},
                    status=status.HTTP_409_CONFLICT
                )

            if details.otp != int(otp):
                return Response(
                    {"error": "Invalid OTP"},
                    status=status.HTTP_403_FORBIDDEN
                )

            details.verification_status = True

            accepted_status = RideStatusLookup.objects.get(
                ride_status="DRIVER_ASSIGNED"
            )
            details.ride_status = accepted_status
            details.save()

            now = timezone.now()
            vehicle = VehicleDriverAssignment.objects.filter(
                driver__driver_id=driver_id,
                start_time__lte=now,
                end_time__gte=now
            ).first()

            Ride.objects.filter(ride_id=ride_id).update(
                driver=driver,
                vehicle=vehicle
            )

            EventLog.objects.create(
                ride_id=ride_id,
                ride_status=accepted_status
            )

        return Response(
            {"status": "ACCEPTED"},
            status=status.HTTP_200_OK
        )
    

class UpdateRideStatusView(APIView):
    def post(self, request):
        data_bytes = request.body
        data_str = data_bytes.decode("utf-8")        # convert bytes to str
        data = json.loads(data_str)
        ride_id = data["ride_id"]

        status_code = request.data.get("ride_status")
        lat = request.data.get("latitude")
        lng = request.data.get("longitude")

        new_status = RideStatusLookup.objects.get(
            ride_status=status_code
        )

        details = RideDetailsForRiders.objects.get(ride_id=ride_id)
        details.ride_status = new_status
        details.save()

        EventLog.objects.create(
            ride_id=ride_id,
            ride_status=new_status,
            latitude=lat,
            longitude=lng
        )

        return Response({"status": status_code})


class RideLocationLogView(APIView):
    def post(self, request):
        print("request received", request.body)
        serializer = RideLocationLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response({"logged": True})
    

class CancelRideView(APIView):
    def post(self, request):
        serializer = RideCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cancellation = serializer.save()

        return Response(
            {
                "status": "CANCELLED",
                "cancellation_id": str(cancellation.cancellation_id)
            },
            status=status.HTTP_201_CREATED
        )
    

class RejectRideView(APIView):
    def post(self, request):
        serializer = RejectRideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rejection = serializer.save()

        return Response({"status": "REJECTED", "rejection_id": str(rejection.rejection_id)}, status=status.HTTP_201_CREATED)


class ListPreviousRidesView(APIView):
    def get(self, request, user_id):
        rides = RideDetailsForRiders.objects.filter(rider_id = user_id)
        serializer = RideDetailsForRidersSerializer(rides, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)