from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drivers.models import Driver, VehicleDriverAssignment, Vehicle, VehicleType
from fleet_admin.serializers import CreateVehicleSerializer
from authentication.models import TenantUser, User
from django.db import transaction

class VehicleDriverManagementAPIView(APIView):
    def get(self, request, user_id):
        user = User.objects.get(user_id = user_id)
        try:
            # If Driver, filter by the driver's linked user
            driver = get_object_or_404(Driver, user=user)
            vehicles = VehicleDriverAssignment.objects.filter(driver=driver)
            # tenant_user = get_object_or_404(TenantUser, user=user)
            # vehicles = Vehicle.objects.filter(fleet_tenant_id=tenant_user.tenant)
        except Driver.DoesNotExist:
            raise ValueError()
            # If Fleet Admin, filter by tenant
            # tenant_user = get_object_or_404(TenantUser, user=user)
            # vehicles = Vehicle.objects.filter(tenant=tenant_user.tenant)

        # Assuming a simple serializer or manual mapping for brevity
        data = [{
            "id": v.vehicle.vehicle_id,
            "number": v.vehicle.vehicle_number,
            "type": v.vehicle.vehicle_type.vehicle_name if v.vehicle.vehicle_type else "N/A",
            "condition": v.vehicle.vehicle_conditon,
            "is_default": v.is_default
        } for v in vehicles]
        
        return Response(data)
    
    def post(self, request, user_id):
        # user_id = request.data.get("user_id")
        # is_default = request.data.get("is_default", False)


        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1️⃣ Fetch driver using user_id
        try:
            driver = Driver.objects.select_related("user").get(user_id=user_id)
        except Driver.DoesNotExist:
            return Response(
                {"error": "Driver not found for this user"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CreateVehicleSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            is_default = serializer.validated_data.pop('is_default')
            vehicle = serializer.save()

            if is_default:
                # Unset previous default vehicle for the driver
                VehicleDriverAssignment.objects.filter(
                    driver=driver,
                    is_default=True
                ).update(is_default=False)


            # Create new vehicle-driver assignment
            VehicleDriverAssignment.objects.create(
                vehicle=vehicle,
                driver=driver,
                start_time=timezone.now(),
                end_time=None,
                is_default= is_default
            )

        return Response(
            {
                "message": "Vehicle created and assigned to driver successfully",
                "vehicle_id": vehicle.vehicle_id
            },
            status=status.HTTP_201_CREATED
        )

    def delete(self, request, user_id, vehicle_id):
        
        vehicle_assignment = get_object_or_404(VehicleDriverAssignment, vehicle_id = vehicle_id)
        vehicle_assignment.delete()
        vehicle = get_object_or_404(Vehicle, vehicle_id=vehicle_id)
        if(vehicle.fleet_tenant_id):
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        vehicle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def patch(self, request, user_id):
        # user_id = request.data.get("user_id")
        vehicle_id = request.data.get("vehicle_id")

        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            driver = Driver.objects.select_related("user").get(user_id=user_id)
        except Driver.DoesNotExist:
            return Response(
                {"error": "Driver not found for this user"},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            # Unset previous default vehicle for the driver
            VehicleDriverAssignment.objects.filter(
                driver=driver,
                is_default=True
            ).update(is_default=False)

            # Set the new default vehicle
            VehicleDriverAssignment.objects.filter(
                driver=driver,
                vehicle_id=vehicle_id
            ).update(is_default=True)

        return Response(
            {"message": "Default vehicle updated successfully"},
            status=status.HTTP_200_OK
        )