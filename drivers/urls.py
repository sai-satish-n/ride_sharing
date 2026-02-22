from django.urls import path
from drivers.views import VehicleDriverManagementAPIView

urlpatterns = [
    path('<uuid:user_id>/vehicles/', VehicleDriverManagementAPIView.as_view(), name='create-driver-vehicle'),
    path('<uuid:user_id>/vehicles/delete/<uuid:vehicle_id>', VehicleDriverManagementAPIView.as_view()),
]
