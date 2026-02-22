from rest_framework.views import APIView
from rest_framework.response import Response
from fleet_admin.serializers import *
from rest_framework import status
from authentication.models import (
    TenantUser,
    User,
    UserRole,
    Role,
    UserStatusLookup,
)
from django.core.paginator import Paginator
from rides.models import TenantRegion, Country, Vehicle
from drivers.models import DriverFleetAssignment, Driver
from fleet_admin.models import Fleet
from django.utils.timezone import now
from django.db.models import Q
from app_admin.serializers import AdminUserListSerializer
from common.serializers import CountrySerializer, StateSerializer, RegionSerializer, CreateRegionSerializer, RegionTypeSerializer
from common.models import KYCDetails, KYCStatusLookup, KYCMedia
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.utils import IntegrityError
from django.utils.dateparse import parse_date
import uuid


class ListTenantRegionsAPIView(APIView):
    def get(self, request):
        tenant_id = request.query_params.get("tenant_id")
        is_active = request.query_params.get("is_active")
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        qs = TenantRegion.objects.select_related(
            "tenant",
            "region",
            "region__country",
            "region__state",
            "region__region_type",
        )

        tenant = TenantUser.objects.get(user__user_id=tenant_id)

        if tenant_id:
            qs = TenantRegion.objects.filter(tenant=tenant.tenant.tenant_id, deleted_at__isnull =True)
        if is_active in ["true", "false"]:
            qs = qs.filter(is_active=(is_active == "true"))

        paginator = Paginator(qs.order_by("-tenant_region_id"), limit)
        page_obj = paginator.get_page(page)

        serializer = TenantRegionSerializer(page_obj, many=True)

        return Response({"count": paginator.count, "results": serializer.data})


# Create your views here.
class AddTenantRegionAPIView(APIView):
    def post(self, request):
        tenant_id = request.data.get("tenant_id")
        region_id = request.data.get("region_code")
        region_nick_name = request.data.get("region_nick_name")

        if not tenant_id or not region_id:
            return Response(
                {"error": "tenant_id and region_id are required"}, status=400
            )

        exists = TenantRegion.objects.filter(
            tenant_id=tenant_id, region_id=region_id
        ).exists()

        if exists:
            return Response({"error": "Region already assigned to tenant"}, status=400)

        tenant = TenantUser.objects.get(user_id=tenant_id)
        tenant_region = TenantRegion.objects.create(
            tenant_id=tenant.tenant.tenant_id, 
            region_id=region_id, 
            is_active=True,
            region_nick_name = region_nick_name,
        )

        serializer = TenantRegionSerializer(tenant_region)
        return Response(serializer.data, status=201)


class UpdateTenantRegionAPIView(APIView):
    def patch(self, request, tenant_region_id):
        """Update the active status or the underlying region details."""
        tenant_region = get_object_or_404(
            TenantRegion, tenant_region_id=tenant_region_id
        )

        # Update Global Region Details
        tenant_region.region_nick_name = request.data.get(
            "region_nick_name", tenant_region.region_nick_name
        )
        # Update Tenant Specific Link
        tenant_region.is_active = request.data.get(
            "is_service_active", tenant_region.is_active
        )

        tenant_region.save()

        return Response({"message": "Region updated successfully"})


class RemoveTenantRegionAPIView(APIView):
    def delete(self, request, tenant_region_id):
        try:
            tenant_region = TenantRegion.objects.filter(
                tenant_region_id=tenant_region_id
            ).update(is_active=False, deleted_at = timezone.now())
        except TenantRegion.DoesNotExist:
            return Response({"error": "Tenant region not found"}, status=404)

        # tenant_region.update(is_active = False)
        return Response({"message": "Tenant region removed successfully"}, status=204)


class ListVehicleTypesAPIView(APIView):
    def get(self, request):
        vehicle_types = VehicleType.objects.all().order_by("vehicle_name")
        serializer = VehicleTypeSerializer(vehicle_types, many=True)
        return Response(serializer.data)


class CreateVehicleAPIView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 🔹 Find tenant for fleet admin
        try:
            tenant_user = TenantUser.objects.select_related("tenant").get(
                user_id=user_id
            )
        except TenantUser.DoesNotExist:
            return Response(
                {"error": "Fleet admin is not associated with any tenant"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CreateVehicleSerializer(data=request.data)

        if serializer.is_valid():
            # serializer.validated_data.pop("is_default")
            serializer.save(fleet_tenant_id=tenant_user.tenant)
            return Response(
                {"message": "Vehicle registered successfully"},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteVehicleAPIView(APIView):
    def delete(self, request, user_id, vehicle_id):

        vehicle_assignment = VehicleDriverAssignment.objects.filter(
            vehicle_id=vehicle_id
        )
        for assignment in vehicle_assignment:
            assignment.delete()

        vehicle = get_object_or_404(Vehicle, vehicle_id=vehicle_id)
        vehicle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListCountriesAPIView(APIView):
    def get(self, request):
        countries = Country.objects.all().order_by("country_name")
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)


class ListRegionTypesAPIView(APIView):
    def get(self, request):
        types = RegionTypeLookup.objects.all().order_by("region_type")
        serializer = RegionTypeSerializer(types, many=True)
        return Response(serializer.data)


class ListStatesAPIView(APIView):
    def get(self, request):
        country_code = request.query_params.get("country")

        if not country_code:
            return Response({"error": "country is required"}, status=400)

        states = State.objects.filter(country_id=country_code).order_by("state_name")
        serializer = StateSerializer(states, many=True)
        return Response(serializer.data)

class ListRegionsAPIView(APIView):
    def get(self, request):
        country_code = request.query_params.get("country")
        state_code = request.query_params.get("state")
        
        if not all([country_code,state_code]):
            return Response({"error": "country and state codes are required"}, status=400)


        countries = Region.objects.filter(country_id=country_code, state_id = state_code).order_by("region_name")
        serializer = RegionSerializer(countries, many=True)
        return Response(serializer.data)

class CreateRegionAPIView(APIView):
    def post(self, request):
        serializer = CreateRegionSerializer(data=request.data)

        if serializer.is_valid():
            region = serializer.save()
            return Response(
                {
                    "message": "Region created successfully",
                    "region_id": region.region_code,
                },
                status=201,
            )

        return Response(serializer.errors, status=400)


class TenantRegionManagementAPIView(APIView):
    def get(self, request, user_id):
        # We find the tenant associated with the user_id
        tenant_user = get_object_or_404(TenantUser, user_id=user_id)
        regions = TenantRegion.objects.filter(tenant=tenant_user.tenant).order_by(
            "-tenant_region_id"
        )

        # Paginated response or simple list
        data = [
            {
                "tenant_region_id": r.tenant_region_id,
                "region": r.region.ride_id,
                "region_name": r.region.region_name,
                "country": r.region.country.country_name,
                "country_code": r.region.country.country_code,
                "state": r.region.state.name if r.region.state else None,
                "state_code": r.region.state.id if r.region.state else None,
                "region_type": r.region.region_type.name,
                "region_type_id": r.region.region_type.id,
                "is_active": r.is_active,
            }
            for r in regions
        ]

        return Response({"results": data})

    def delete(self, request, tenant_region_id):
        tenant_region = get_object_or_404(
            TenantRegion, tenant_region_id=tenant_region_id
        )
        tenant_region.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListActiveAssignmentsAPIView(APIView):
    def get(self, request, user_id):
        # 1️⃣ Resolve tenant from user
        try:
            tenant_user = TenantUser.objects.get(user_id=user_id)
        except TenantUser.DoesNotExist:
            return Response(
                {"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND
            )

        tenant = tenant_user.tenant

        # 2️⃣ Get active vehicle-driver assignments for this tenant
        assignments = VehicleDriverAssignment.objects.filter(
            vehicle__fleet_tenant_id=tenant,
            # end_time__isnull=True
        ).select_related("vehicle", "driver", "driver__user")

        # 3️⃣ Shape response EXACTLY as frontend expects
        data = [
            {
                "vehicle_driver_assign_id": a.vehicle_driver_assign_id,
                "vehicle_number": a.vehicle.vehicle_number,
                "driver_name": f"{a.driver.user.first_name} {a.driver.user.last_name}",
                "end_time": a.end_time,  # frontend formats it
            }
            for a in assignments
        ]

        return Response(data, status=status.HTTP_200_OK)


class ListTenantDriversAPIView(APIView):
    def get(self, request, user_id):
        try:
            tenant_user = TenantUser.objects.get(user_id=user_id)
        except TenantUser.DoesNotExist:
            return Response({"error": "Tenant not found"}, status=404)

        drivers = (
            Driver.objects.filter(
                driverfleetassignment__tenant_id=tenant_user.tenant,
                driverfleetassignment__end_date__isnull=True,
            )
            .select_related("user")
            .distinct()
        )

        data = [
            {
                "driver_id": d.driver_id,
                "name": f"{d.user.first_name} {d.user.last_name}",
                "rating": d.driver_rating,
            }
            for d in drivers
        ]

        return Response(data)


class ListTenantVehiclesAPIView(APIView):
    def get(self, request, user_id):
        try:
            tenant_user = TenantUser.objects.get(user_id=user_id)
        except TenantUser.DoesNotExist:
            return Response({"error": "Tenant not found"}, status=404)

        vehicles = Vehicle.objects.filter(
            fleet_tenant_id=tenant_user.tenant
        ).select_related("vehicle_type")

        data = [
            {
                "id": v.vehicle_id,
                "number": v.vehicle_number,
                "type": v.vehicle_type.vehicle_name if v.vehicle_type else "N/A",
                "condition": v.vehicle_conditon,
            }
            for v in vehicles
        ]

        return Response(data)


class CreateAssignmentAPIView(APIView):
    def post(self, request):
        serializer = CreateVehicleDriverAssignmentSerializer(data=request.data)

        if serializer.is_valid():
            try:
                serializer.save()
            except IntegrityError:
                return Response({"message": "Assignment already assigned"}, status=201)
            return Response({"message": "Assignment created successfully"}, status=201)

        return Response(serializer.errors, status=400)


class CreateFleetAPIView(APIView):
    def post(self, request):
        # We expect tenant_id, region_id, and fleet_name
        tenant_id = request.data.get("tenant_id")
        region_id = request.data.get("region_id")
        fleet_name = request.data.get("fleet_name")

        if not all([tenant_id, region_id, fleet_name]):
            return Response({"error": "Missing required fields"}, status=400)

        tenant = TenantUser.objects.get(user__user_id=tenant_id)

        fleet = Fleet.objects.create(
            tenant_id=tenant.tenant.tenant_id,
            region_id=region_id,
            fleet_name=fleet_name,
        )
        return Response(
            {"message": "Fleet created", "fleet_id": fleet.fleet_id}, status=201
        )


class ListFleetsAPIView(APIView):
    def get(self, request, user_id):
        tenant = TenantUser.objects.get(user_id=user_id)
        fleets = Fleet.objects.filter(
            tenant_id=tenant.tenant.tenant_id, is_active=True
        ).select_related("region")

        serializer = FleetSerializer(fleets, many=True)
        return Response(serializer.data)


class ListFleetDriversAPIView(APIView):
    def get(self, request, fleet_id):
        assignments = DriverFleetAssignment.objects.filter(
            fleet_id=fleet_id, end_date__isnull=True
        ).select_related("driver", "driver__user")

        data = [
            {
                "driver_id": a.driver.driver_id,
                "name": f"{a.driver.user.first_name} {a.driver.user.last_name}",
                "licence_number": a.driver.driving_licence_number,
                "rating": a.driver.driver_rating,
                "start_date": a.start_date,
            }
            for a in assignments
        ]

        return Response(data)


class SearchDriversAPIView(APIView):
    def post(self, request):
        query = request.data.get("query")
        tenant_id = request.data.get("tenant_id")

        if not query or not tenant_id:
            return Response(
                {"error": "query and tenant_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔎 Find users by email OR phone
        users = User.objects.filter(
            Q(email__icontains=query) | Q(phone__icontains=query)
        )

        if not users.exists():
            return Response([], status=status.HTTP_200_OK)


        # 🎭 Driver role lookup
        try:
            driver_roles = Role.objects.filter(
                Q(role_name="driver", role_scope="SELF") | Q(role_name="driver", role_scope="TENANT")
            )
        except Role.DoesNotExist:
            return Response(
                {"error": "Driver role not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        driver_role_self = driver_roles.get(role_scope="SELF")
        driver_role_tenant = driver_roles.get(role_scope="TENANT")

        # 👤 Users who are drivers
        driver_users = UserRole.objects.filter(
            user__in=users,
            role__in=[driver_role_self, driver_role_tenant]
        ).values_list("user_id", flat=True)

        drivers = Driver.objects.filter(user_id__in=driver_users)

        results = []

        for driver in drivers:
            # 🚫 Skip if already actively assigned to any fleet
            if DriverFleetAssignment.objects.filter(
                driver=driver, end_date__isnull=True
            ).exists():
                continue

            user = driver.user
            results.append(
                {
                    "user_id": user.user_id,
                    "driver_id": driver.driver_id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                }
            )

        serializer = DriverSearchResultSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddDriverToFleetAPIView(APIView):
    def post(self, request):
        fleet_id = request.data.get("fleet_id")
        driver_id = request.data.get("driver_id")
        tenant_id = request.data.get("tenant_id")

        if not fleet_id or not driver_id or not tenant_id:
            return Response(
                {"error": "fleet_id, driver_id and tenant_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = TenantUser.objects.get(user_id=tenant_id)
        # 🔒 Validate fleet belongs to tenant
        if not Fleet.objects.filter(
            fleet_id=fleet_id, tenant_id=tenant.tenant.tenant_id, is_active=True
        ).exists():
            return Response(
                {"error": "Fleet does not belong to tenant or is inactive"},
                status=status.HTTP_403_FORBIDDEN,
            )


        driver = Driver.objects.get(user_id=driver_id)
        # 🚫 Check if driver already assigned to this fleet
        if DriverFleetAssignment.objects.filter(
            fleet_id=fleet_id, driver_id=driver.driver_id, end_date__isnull=True
        ).exists():
            return Response(
                {"error": "Driver already assigned to this fleet"},
                status=status.HTTP_400_BAD_REQUEST,
            )


        # 🔁 Close any existing active fleet assignment for driver
        existing_assignment = DriverFleetAssignment.objects.filter(
            driver_id=driver_id, end_date__isnull=True,
        ).first()

        if existing_assignment:
            existing_assignment.end_date = now().date()
            existing_assignment.save(update_fields=["end_date"])

        payload = {
            "fleet": fleet_id,
            "driver": driver.driver_id,
            "tenant_id": tenant.tenant.tenant_id,
            "start_date": request.data.get("start_date") or now().date(),
        }


        serializer = AddDriverToFleetSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        role = Role.objects.get(role_name="driver", role_scope="TENANT")

        tenant_user = TenantUser.objects.create(
            user_id=driver_id,
            tenant_id=tenant.tenant_id,
            tenant_role=role,
            status=UserStatusLookup.objects.get(status_name="ACTIVE"),
            joined_at=timezone.now(),
        )
        user_role, _ = UserRole.objects.get_or_create(
            user_id = driver_id,
            tenant_id = tenant.tenant_id,
            role = role,
            assigned_by_id=tenant.tenant_id,
        )

        
        tenant_user.save()
        # user_role.save()



        return Response(
            {"message": "Driver added to fleet successfully"},
            status=status.HTTP_201_CREATED,
        )


class RemoveDriverFromFleetAPIView(APIView):
    def post(self, request):
        fleet_id = request.data.get("fleet_id")
        driver_id = request.data.get("driver_id")

        if not fleet_id or not driver_id:
            return Response(
                {"error": "fleet_id and driver_id are required"}, status=400
            )

        try:
            assignment = DriverFleetAssignment.objects.get(
                fleet_id=fleet_id, driver_id=driver_id, end_date__isnull=True
            )
        except DriverFleetAssignment.DoesNotExist:
            return Response({"error": "Active assignment not found"}, status=404)

        assignment.end_date = now().date()
        assignment.save(update_fields=["end_date"])

        

        # TenantUser.objects.delete()

        return Response({"message": "Driver removed from fleet successfully"})


def get_tenant_from_user(user_id):
    try:
        return TenantUser.objects.filter(user_id=user_id).first().tenant
    except TenantUser.DoesNotExist:
        return None


class FleetAdminListUsersAPIView(APIView):
    def get(self, request, user_id):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        tenant = get_tenant_from_user(user_id)
        if not tenant:
            return Response({"error": "Invalid tenant"}, status=403)

        users = (
            User.objects.filter(tenantuser__tenant=tenant)
            .distinct()
            .order_by("-created_at")
        )

        paginator = Paginator(users, limit)
        page_obj = paginator.get_page(page)

        serializer = AdminUserListSerializer(page_obj, many=True)

        return Response(
            {
                "count": paginator.count,
                "total_pages": paginator.num_pages,
                "current_page": page,
                "results": serializer.data,
            }
        )


class FleetAdminListUserRolesAPIView(APIView):
    def get(self, request, user_id):
        tenant = get_tenant_from_user(user_id)
        if not tenant:
            return Response({"error": "Unauthorized"}, status=403)

        user_roles = UserRole.objects.filter(user_id=user_id).select_related("role")

        data = [
            {
                "role_id": ur.role.role_id,
                "role_name": ur.role.role_name,
                "tenant_id": ur.tenant_id,
                "is_removable": ur.role.role_name == "fleet_admin",
            }
            for ur in user_roles
        ]

        return Response(data, status=200)


class FleetAdminAssignUserRoleAPIView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        role_id = request.data.get("role_id")
        tenant_id = request.data.get("tenant_id")

        tenant = get_tenant_from_user(tenant_id)
        if not tenant:
            return Response({"error": "Unauthorized"}, status=403)

        try:
            if role_id == 3:
                role = Role.objects.get(role_id=6)
            else:
                role = Role.objects.get(role_id=role_id)
        except Role.DoesNotExist:
            return Response({"error": "Role not found"}, status=404)

        # 🚫 Hard restriction
        if role.role_name not in ["fleet_admin", "driver"]:
            return Response(
                {"error": "Fleet admin and driver role can only be assigned"},
                status=403,
            )

        if UserRole.objects.filter(
            user_id=user_id, role=role, tenant_id=tenant.tenant_id
        ).exists():
            return Response({"error": "Role already assigned"}, status=400)

        UserRole.objects.create(
            user_id=user_id, role=role, tenant_id=tenant.tenant_id, assigned_by=tenant
        )



        return Response({"message": "Fleet admin role assigned"}, status=201)


class FleetAdminRemoveUserRoleAPIView(APIView):
    def delete(self, request):
        user_id = request.data.get("user_id")
        role_id = request.data.get("role_id")
        tenant_id = request.data.get("tenant_id")

        try:
            role = Role.objects.get(role_id=role_id)
        except Role.DoesNotExist:
            return Response({"error": "Role not found"}, status=404)

        # 🚫 Cannot remove admin
        if role.role_name == "admin":
            return Response({"error": "Cannot remove admin role"}, status=403)

        if role.role_name not in ["fleet_admin", "driver"]:
            return Response(
                {"error": "Only fleet_admin and driver roles can be removed"},
                status=403,
            )

        deleted, _ = UserRole.objects.filter(
            user_id=user_id, role=role, tenant_id=tenant_id
        ).delete()

        

        if deleted == 0:
            return Response({"error": "Role assignment not found"}, status=404)

        if not UserRole.objects.filter(user_id=user_id, tenant_id=tenant_id).exists():
            TenantUser.objects.filter(tenant_id=tenant_id, user_id = user_id).delete()

        if role.role_name == "driver":
            driver = Driver.objects.get(user_id=user_id)
            DriverFleetAssignment.objects.filter(
                driver_id=driver.driver_id,
                end_date__isnull=True,
                tenant_id=tenant_id,
            ).update(end_date=now().date())


        return Response(
            {"message": "Fleet admin removed, reverted to driver"}, status=200
        )


class FleetBaseAPIView(APIView):
    """
    Helper to get the tenant_id for the logged-in Fleet Admin.
    """

    def get_tenant(self, user):
        tenant_user = TenantUser.objects.filter(user=user).first()
        return tenant_user.tenant


class FleetListDriversKYCAPIView(FleetBaseAPIView):
    """
    List KYC for drivers belonging ONLY to this fleet admin's tenant.
    """

    def get(self, request, user_id):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))  # dynamic page size
        email = request.query_params.get("email")
        status = request.query_params.get("status")
        sort = request.query_params.get("sort", "newest")
        start_date =request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        
        user = User.objects.get(user_id=user_id)
        driver = self.get_tenant(user)
        

        
        driver_user_ids = UserRole.objects.filter(
            tenant_id=driver.tenant_id,
            role_id=6
        ).values_list("user_id", flat=True)

        
        # Step 3: Get drivers for those users
        drivers = Driver.objects.filter(
            user_id__in=driver_user_ids
        ).select_related("user")

        if email:
            drivers = drivers.filter(user__email__icontains=email)

        if status and status != "ALL":
            driver_ids_with_status = []
            for driver in drivers:
                kycs = KYCDetails.objects.filter(driver=driver)
                if not kycs.exists():
                    tenant_status = "DOCUMENTS_NOT_SUBMITTED"
                elif any(k.kyc_status.kyc_status == "REJECTED" for k in kycs):
                    tenant_status = "REJECTED"
                elif all(k.kyc_status.kyc_status == "APPROVED" for k in kycs):
                    tenant_status = "VERIFIED"
                else:
                    tenant_status = "PENDING_APPROVAL"
                if tenant_status == status:
                    driver_ids_with_status.append(driver.driver_id)
            drivers = drivers.filter(driver_id__in=driver_ids_with_status)

        if start_date:
            start_date = parse_date(start_date)
            if start_date:
                drivers = drivers.filter(created_at__date__gte=start_date)

        if end_date:
            end_date = parse_date(end_date)
            if end_date:
                drivers = drivers.filter(created_at__date__lte=end_date)


        
        sort_mapping = {
            "newest": "-created_at",
            "oldest": "created_at",
            "verified": "-vertified_at",  # descending verified_at
            "unverified": "vertified_at",  # ascending verified_at
        }
        sort_field = sort_mapping.get(sort, "-created_at")
        drivers = drivers.order_by(sort_field)
        
        paginator = Paginator(drivers, limit)
        page_obj = paginator.get_page(page)

        # serializer = DriverSerializer(page_obj, many=True)
        # return Response({
        #     "count": paginator.count,
        #     "results": serializer.data
        # })
        drivers_with_kyc_status = []
        for driver in page_obj:
            # Get KYC details for the driver
            kycs = KYCDetails.objects.filter(driver=driver)

            # Determine the KYC status for the driver
            if not kycs.exists():
                kyc_status = "DOCUMENTS_NOT_SUBMITTED"
            elif any(k.kyc_status.kyc_status == "REJECTED" for k in kycs):
                kyc_status = "REJECTED"
            elif all(k.kyc_status.kyc_status == "APPROVED" for k in kycs):
                kyc_status = "VERIFIED"
            else:
                kyc_status = "PENDING_APPROVAL"

            # Append driver data along with KYC status
            drivers_with_kyc_status.append({
                "driver_id": driver.driver_id,
                "user": {
                    "user_id": driver.user.user_id,
                    "first_name": driver.user.first_name,
                    "last_name": driver.user.last_name,
                    "email": driver.user.email,
                    "phone": driver.user.phone,
                },
                "driving_licence_number": driver.driving_licence_number,
                "driver_rating": driver.driver_rating,
                # "driver_online_status": driver.driver_online_status,
                "current_latitude": driver.current_latitude,
                "current_longitude": driver.current_longitude,
                "last_location": driver.last_location,
                "location_updated_at": driver.location_updated_at,
                "created_at": driver.created_at,
                "kyc_status": kyc_status  # Add KYC status
            })

        return Response({
            "count": paginator.count,
            "results": drivers_with_kyc_status  # Return results with KYC status
        })
 

class FleetViewDriverMediaAPIView(FleetBaseAPIView):
    """
    Fetches the actual media (Images/Docs) for a specific driver
    after verifying they belong to the admin's tenant.
    """

    def get(self, request, tenant_id, driver_id):
        user = User.objects.get(user_id=tenant_id)
        tenant = self.get_tenant(user)

        # Security check: Ensure the KYC record belongs to this tenant
        driver = get_object_or_404(Driver, driver_id=driver_id)

        driver_role_exists = UserRole.objects.filter(
            user=driver.user,
            tenant_id=tenant.tenant_id,
            role_id=6
        ).exists()

        if not driver_role_exists:
            return Response(
                {"error": "Driver does not belong to your tenant"},
                status=status.HTTP_403_FORBIDDEN
            )
        kyc_detail = KYCDetails.objects.filter(
            driver=driver,
            # tenant_id=tenant
        ).prefetch_related(
            "kycmedia_set__kyc_type",
            "kycmedia_set__kyc_status"
        ).first()

        if not kyc_detail:
            return Response({"results": []})

        media_data = []
        for media in kyc_detail.kycmedia_set.all().order_by("-uploaded_at"):
            media_data.append({
                "kyc_media_id": media.kyc_media_id,
                "kyc_type_id": media.kyc_type.kyc_type_id,
                "kyc_type_name": media.kyc_type.kyc_type,
                "kyc_status": media.kyc_status.kyc_status,
                "media_url": media.media_url,
                "media_type": media.media_type,
                "rejected_reason": media.rejected_reason,
                "uploaded_at": media.uploaded_at
            })

        return Response({"results": media_data})


class FleetUpdateDriverKYCView(FleetBaseAPIView):

    def post(self, request, driver_id):
        user_id = request.data.get("user_id")
        kyc_media_id = request.data.get("kyc_media_id")
        rejected_reason = request.data.get("rejected_reason")

        
        try:
            kyc_media_id = uuid.UUID(kyc_media_id)
        except (ValueError, TypeError):
            return Response({"error": "Invalid KYC Media ID"}, status=400)
        
        media = get_object_or_404(
            KYCMedia,
            kyc_media_id=kyc_media_id,
        )

        if rejected_reason:
            rejected_status = KYCStatusLookup.objects.get(
                kyc_status="REJECTED"
            )
            media.kyc_status = rejected_status
            media.rejected_reason = rejected_reason
            media.verified_at = None
            media.save()

        else:
            approved_status = KYCStatusLookup.objects.get(
                kyc_status="APPROVED"
            )
            media.kyc_status = approved_status
            media.rejected_reason = None
            media.verified_at = timezone.now()
            media.save()


        kyc_detail = media.kyc
        approved_docs = kyc_detail.kycmedia_set.filter(
            kyc_status__kyc_status="APPROVED"
        ).count()

        if approved_docs==3:
            print("in approving block")
            kyc_detail.kyc_status= approved_status
            kyc_detail.verified_at = timezone.now()
            kyc_detail.save()
            global_status = "ACTIVE"
            message = "All documents approved. Driver is now ACTIVE."
        else:
            global_status = "PENDING"
            message = "Document approved. More documents pending."

        return Response({
            "message": message,
            "kyc_status": media.kyc_status.kyc_status,
            "global_status": global_status,
            "rejected_reason": media.rejected_reason
        }, status=status.HTTP_200_OK)



