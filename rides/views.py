from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rides.serializers import *
from drivers.models import Driver, VehicleDriverAssignment
from rides.serializers import RejectRideSerializer
from django.utils import timezone
import h3
from rides.models import RideDetailsForRiders, RideStatusLookup, Region
import json
from payments_module.models import PricingConfig, SurgePricing, RideFareSnapshot
from utils.ride_utils import point_in_geojson, haversine_distance
from decimal import Decimal


def get_nearby_rides_for_driver(driver, k_ring=3, target_res=10):
    """
    Returns nearby BOOKED rides for a driver using H3 proximity,
    excluding rides already rejected by the driver
    """

    if not driver.current_latitude or not driver.current_longitude:
        return RideDetailsForRiders.objects.none()

    driver_current_h3_index = h3.latlng_to_cell(lat=driver.current_latitude, lng=driver.current_longitude, res=target_res)
    driver_h3_index = h3.cell_to_parent(driver_current_h3_index, target_res)
    nearby_cells = list(h3.grid_disk(driver_h3_index, k_ring))

    booked_status = RideStatusLookup.objects.get(
        ride_status="BOOKED"
    )

    rejected_rides = DriverRideRejection.objects.filter(
        driver=driver
    ).values_list("ride_id", flat=True)

    vehicle_assignment = (
        VehicleDriverAssignment.objects
        .filter(driver=driver, is_default=True)
        .order_by("-start_time")
        .first()
    )

    if not vehicle_assignment:
        return []

    if not vehicle_assignment.vehicle or not vehicle_assignment.vehicle.vehicle_type:
        return []
    
    vehicle_type = vehicle_assignment.vehicle.vehicle_type.vehicle_type_id



    rides = RideDetailsForRiders.objects.filter(
        ride_status=booked_status,
        vehicle_type=vehicle_type
    ).exclude(ride_id__in=rejected_rides).select_related("ride", "rider").order_by("created_at")

    # Manually convert each ride's from_location string to an H3 index for comparison
    filtered_rides = []
    for ride in rides:
        # Assuming 'from_location' is stored as 'lat, lng' string (e.g., '34.0522, -118.2437')
        lat_lng_str = ride.from_location  # Example: '34.0522, -118.2437'
        lat, lng = map(float, lat_lng_str.split(", "))  # Split and convert to float
        ride_h3_index = h3.latlng_to_cell(lat, lng, res=target_res)
        drop_lat, drop_lng = map(float, ride.to_location.split(","))
        distance = haversine_distance(lat, lng, drop_lat, drop_lng)

        # Check if the ride's H3 index is within the nearby cells
        if ride_h3_index in nearby_cells:
            filtered_rides.append({
                "rider_id": ride.rider.user_id,
                "ride_id": ride.ride.ride_id,  # Including ride details
                "from_location": ride.from_location,
                "to_location": ride.to_location,
                "created_at": ride.created_at,
                "ride_fare": ride.ride_fare,
                "distance": distance
            })

    return filtered_rides




class CheckVehiclesBeforeBooking(APIView):
    """
    Fetch all available vehicles & pricing for pickup location
    """

    def post(self, request):
        pickup_lat = request.data.get("from_lat")
        pickup_lng = request.data.get("from_lng")
        drop_lat = request.data.get("to_lat")
        drop_lng = request.data.get("to_lng")

        if pickup_lat is None or pickup_lng is None:
            return Response(
                {"detail": "pickup_lat and pickup_lng are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Find matching region
        region = None
        regions = Region.objects.filter(
            is_service_active=True,
            geo_boundary__isnull=False
        )

        for r in regions:
            if point_in_geojson(pickup_lat, pickup_lng, r.geo_boundary):
                region = r
                break

        if not region:
            return Response(
                {"detail": "Service not available in this area"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Fetch pricing configs for region
        pricing_qs = PricingConfig.objects.select_related(
            "vehicle_type"
        ).filter(region=region)

        if not pricing_qs.exists():
            return Response(
                {"detail": "No vehicles available in this region"},
                status=status.HTTP_404_NOT_FOUND
            )

        distance = haversine_distance(pickup_lat, pickup_lng, drop_lat, drop_lng)
         
        # 3. Build response
        vehicles = []
        for p in pricing_qs:
            if p.base_fare > p.rate_per_km* Decimal(distance): 
                total = p.base_fare
            else:
                total = p.rate_per_km* Decimal(distance)

            # tenant_id = getattr(p.tenant, "tenant_id", None) if p.tenant else None
            # tenant_id = p.tenant_id

            now = timezone.now()

            active_surge = SurgePricing.objects.filter(
                region=region,
                effective_from__lte=now,
                expires_at__gte=now
            ).first()

            if active_surge:
                surge_multiplier = active_surge.surge_multiplier
                # print("Active surge found", active_surge.surge_pricing_id, surge_multiplier)
            else:
                surge_multiplier = 1

            total *= surge_multiplier


            vehicles.append({
                "vehicle_type_id": p.vehicle_type.vehicle_type_id,
                "vehicle_type": p.vehicle_type.vehicle_name,
                "capacity": p.vehicle_type.vehicle_capacity,
                "base_fare": str(p.base_fare),
                "rate_per_km": str(p.rate_per_km),
                "rate_per_min": str(p.rate_per_min),
                "surge_multiplier": surge_multiplier,
                "total_cost": str(total),
                "tenant_id": str(p.tenant_id) if p.tenant_id else None
            })

        return Response(
            {
                "region_code": region.region_code,
                "region_name": region.region_name,
                "vehicles": vehicles
            },
            status=status.HTTP_200_OK
        )
    


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
                "rider": str(serializer.validated_data["user_id"]),
                "ride": ride.ride_id,
                "ride_status": 2,
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

        driver = Driver.objects.get(user_id=driver_id)

        rides = get_nearby_rides_for_driver(
            driver=driver,
            k_ring=1  # tune this (1–3)
        )

        return Response(rides)
    

class AcceptRideView(APIView):

    def post(self, request):
        ride_id = request.data.get("ride_id")
        driver_id = request.data.get("driver_id")
        rider_id = request.data.get("rider_id")

        if not all([ride_id, driver_id, rider_id]):
            return Response(
                {"error": "ride_id and driver_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        driver = Driver.objects.get(user_id=driver_id)

        with transaction.atomic():
            details = RideDetailsForRiders.objects.select_for_update().get(
                ride_id=ride_id,
                rider_id = rider_id,
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
            {"status": "ACCEPTED", "from_location": details.from_location, "to_location": details.to_location},
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
    
    def get(self, request, ride_id, user_id):
        details = RideDetailsForRiders.objects.get(ride_id=ride_id, rider_id = user_id)

        serializers = RideDetailsForRidersSerializer(details)
        # serializers.is_valid(raise_exception=True)
        return Response(serializers.data)


class AddExtraAmountAPIView(APIView):
    """
    Add extra amount to a ride for a rider.
    """

    def post(self, request):
        serializer = AddExtraAmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ride_id = serializer.validated_data['ride_id']
        rider_id = serializer.validated_data['rider_id']
        amount = serializer.validated_data['extra_amount']

        try:
            ride_detail = RideDetailsForRiders.objects.get(
                ride_id=ride_id,
                rider_id=rider_id
            )
        except RideDetailsForRiders.DoesNotExist:
            return Response({"detail": "Ride not found"}, status=status.HTTP_404_NOT_FOUND)


        with transaction.atomic():
            # Add extra amount to ride_fare
            if ride_detail.ride_fare is None:
                ride_detail.ride_fare = amount
            else:
                ride_detail.ride_fare += amount

            ride_detail.is_extra_amount_added = True
            ride_detail.save()

        return Response({
            "ride_id": ride_detail.ride_id,
            "rider_id": ride_detail.rider_id,
            "ride_fare": str(ride_detail.ride_fare),
            "is_extra_amount_added": ride_detail.is_extra_amount_added
        }, status=status.HTTP_200_OK)


class RideLocationLogView(APIView):
    def post(self, request):
        serializer = RideLocationLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response({"logged": True})
    

class RejectRideView(APIView):
    def post(self, request):
        serializer = RejectRideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rejection = serializer.save()

        return Response({"status": "REJECTED", "rejection_id": str(rejection.rejection_id)}, status=status.HTTP_201_CREATED)


class ListPreviousRidesView(APIView):
    def get(self, request, user_id):
        rides = RideDetailsForRiders.objects.filter(rider_id = user_id, ride_status = 1).order_by("-created_at")
        serializer = RideDetailsForRidersSerializer(rides, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class ListPreviousRidesDriverView(APIView):
    def get(self, request, user_id):
        # start_date = request.query_params.get('start_date')
        # end_date = request.query_params.get('end_date')

        ride_ids = Ride.objects.filter(
            driver__user_id=user_id
        ).values_list('ride_id', flat=True)

        rides = RideDetailsForRiders.objects.filter(
            ride_id__in=ride_ids,
            ride_status=1
        ).order_by("-created_at")

        
        serializer = RideDetailsForRidersSerializer(rides, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class VerifyRideView(APIView):
    def post(self, request):
        rider_id = request.data.get('rider_id')
        ride_id = request.data.get('ride_id')
        otp = request.data.get('otp')

        try:
            # Fetch the RideDetailsForRiders entry
            ride_detail = RideDetailsForRiders.objects.get(ride_id=ride_id, rider_id=rider_id)

            # Verify OTP
            if str(ride_detail.otp) == str(otp):
                ride_detail.verification_status = True
                ride_detail.ride_status = RideStatusLookup.objects.get(ride_status_id=4)
                ride_detail.ride_started_at = timezone.now()

                ride_detail.save()
                return Response({"message": "OTP verified successfully", "status": "success"})
            else:
                return Response({"message": "Invalid OTP", "status": "error"})
        
        except RideDetailsForRiders.DoesNotExist:
            return Response({"message": "Ride details not found", "status": "error"})
        

class CancelRideByRiderView(APIView):
    def post(self, request, *args, **kwargs):
        rider_id = request.data.get('rider_id')
        ride_id = request.data.get('ride_id')

        try:
            # Fetch the RideDetailsForRiders entry
            ride_detail = RideDetailsForRiders.objects.get(ride_id=ride_id, rider_id=rider_id)

            # Fetch the 'CANCELLED_BY_USER' status from the RideStatusLookup model
            cancelled_status = RideStatusLookup.objects.get(ride_status="CANCELLED_BY_USER")

            # Set the ride status to 'CANCELLED_BY_USER'
            ride_detail.ride_status = cancelled_status
            ride_detail.save()

            return Response({"message": "Ride cancelled by rider", "status": "success"})
        
        except RideDetailsForRiders.DoesNotExist:
            return Response({"message": "Ride details not found", "status": "error"})
        except RideStatusLookup.DoesNotExist:
            return Response({"message": "Status 'CANCELLED_BY_USER' not found", "status": "error"})
        
    
class CancelRideByDriverView(APIView):
    def post(self, request, *args, **kwargs):
        driver_id = request.data.get('driver_id')
        ride_id = request.data.get('ride_id')

        try:
            # Fetch the RideDetailsForRiders entry
            ride_detail = RideDetailsForRiders.objects.get(ride_id=ride_id)

            # Ensure the ride is currently assigned to the driver (driver_id)
            try:
                
                if str(ride_detail.ride.driver.user.user_id) != str(driver_id):
                    return Response({"message": "This ride is not assigned to the specified driver", "status": "error"})
            
            except AttributeError:
                return Response({"message": "This ride is not assigned to the specified driver", "status": "error"})
            

            # Fetch the 'BOOKED' status from the RideStatusLookup model
            booked_status = RideStatusLookup.objects.get(ride_status="BOOKED")


            # Set the ride status to 'BOOKED' and remove the driver
            ride_detail.ride_status = booked_status
            ride_detail.verification_status = False
            ride_detail.ride.driver = None  # Remove the driver assignment
            ride_detail.ride.save()
            ride_detail.save()

            return Response({"message": "Ride cancelled by driver", "status": "success"})
        
        except RideDetailsForRiders.DoesNotExist:
            return Response({"message": "Ride details not found", "status": "error"})
        except RideStatusLookup.DoesNotExist:
            return Response({"message": "Status 'BOOKED' not found", "status": "error"})
        except Ride.DoesNotExist:
            return Response({"message": "Ride not found", "status": "error"})
        

class RideDetailView(APIView):
    def get(self, request, ride_id):
        # Fetch the ride details for the given ride_id
        ride_detail = get_object_or_404(RideDetailsForRiders, ride_id=ride_id)
        
        # Fetch the associated driver
        driver = ride_detail.ride.driver
        
        # Fetch the ride fare breakup
        fare_breakup = RideFareSnapshot.objects.filter(ride=ride_detail.ride).last()  # Get the latest snapshot
        
        # Serializing data for the response
        ride_detail_data = RideDetailsForRidersSerializer(ride_detail).data
        user = driver.user
        user_data = UserSerializer(user).data if user else {}
        fare_breakup_data = FareBreakupSerializer(fare_breakup).data if fare_breakup else {}
        
        # Combining everything into the response
        response_data = {
            'ride_details': ride_detail_data,
            'driver_details': user_data,
            'fare_breakup': fare_breakup_data,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    