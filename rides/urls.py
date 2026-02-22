from django.urls import path
from .views import (
    BookRideView,
    AvailableRidesForDriverView,
    AcceptRideView,
    UpdateRideStatusView,
    RideLocationLogView,
    RejectRideView,
    ListPreviousRidesView,
    CheckVehiclesBeforeBooking,
    VerifyRideView,
    CancelRideByDriverView,
    CancelRideByRiderView,
    RideDetailView,
    ListPreviousRidesDriverView,
    AddExtraAmountAPIView,
)

urlpatterns = [
    path("check_vehicles/", CheckVehiclesBeforeBooking.as_view(), name="check-vehicles-before-booking"),
    path("book/", BookRideView.as_view()),
    path("available/", AvailableRidesForDriverView.as_view()),
    path("accept/", AcceptRideView.as_view()),
    path("verify_ride/", VerifyRideView.as_view(), name="verify_ride"),
    path("user_cancel_ride/", CancelRideByRiderView.as_view(), name="cancel_ride_by_rider"),
    path("driver_cancel_ride/", CancelRideByDriverView.as_view(), name="cancel_ride_by_driver"),
    path("status/", UpdateRideStatusView.as_view()),
    path('add_amount/', AddExtraAmountAPIView.as_view(), name='add-extra-amount'),
    path("location/", RideLocationLogView.as_view()),       #not included in frontend
    path("reject/", RejectRideView.as_view()),
    path("list_previous_rides/<uuid:user_id>/", ListPreviousRidesView.as_view()),
    path("list_previous_rides/driver/<uuid:user_id>/", ListPreviousRidesDriverView.as_view()),
    path("ride_details/<uuid:ride_id>/", RideDetailView.as_view()),
    path("status/<uuid:ride_id>/<uuid:user_id>", UpdateRideStatusView.as_view()),   #not included in frontend
]