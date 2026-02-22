from django.urls import path
from fleet_admin.views import *
urlpatterns = [
    path('tenant_regions/', ListTenantRegionsAPIView.as_view()),
    path('tenant_regions/add/', AddTenantRegionAPIView.as_view()),
    path('tenant_regions/<int:tenant_region_id>/update/', UpdateTenantRegionAPIView.as_view()),
    path('tenant_regions/<int:tenant_region_id>/delete/', RemoveTenantRegionAPIView.as_view()),
    path('vehicle-types', ListVehicleTypesAPIView.as_view()),
    path('vehicles/create/', CreateVehicleAPIView.as_view()),
    path('<uuid:user_id>/vehicles/delete/<uuid:vehicle_id>/', DeleteVehicleAPIView.as_view()),

    path('regions/create/', CreateRegionAPIView.as_view()),

    path('assignments/active/<uuid:user_id>/', ListActiveAssignmentsAPIView.as_view()),
    path('drivers/<uuid:user_id>/', ListTenantDriversAPIView.as_view()),
    path('vehicles/<uuid:user_id>/', ListTenantVehiclesAPIView.as_view()),
    path('assignments/create/', CreateAssignmentAPIView.as_view()),
    path('fleets/create/', CreateFleetAPIView.as_view()),
    path('fleets/list/<uuid:user_id>', ListFleetsAPIView.as_view()),
    path('fleets/<uuid:fleet_id>/drivers/', ListFleetDriversAPIView.as_view()),
    path('fleets/remove_driver/', RemoveDriverFromFleetAPIView.as_view()),
    path('fleets/add_driver/', AddDriverToFleetAPIView.as_view()),
    path('drivers/search/', SearchDriversAPIView.as_view(), name='search-drivers'),

    path('users/<uuid:user_id>/', FleetAdminListUsersAPIView.as_view()),
    path('user/roles/<uuid:user_id>/', FleetAdminListUserRolesAPIView.as_view()),
    path('user/role/assign/', FleetAdminAssignUserRoleAPIView.as_view()),
    path('user/role/remove/', FleetAdminRemoveUserRoleAPIView.as_view()),

    path('kyc/drivers/<uuid:user_id>/', FleetListDriversKYCAPIView.as_view()),
    path('kyc/drivers/<uuid:tenant_id>/media/<uuid:driver_id>', FleetViewDriverMediaAPIView.as_view()),
    path('kyc/<uuid:driver_id>/update-status/', FleetUpdateDriverKYCView.as_view()),
]
