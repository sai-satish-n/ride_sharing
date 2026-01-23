from django.urls import path
from .views import (
    BookRideView,
    AvailableRidesForDriverView,
    AcceptRideView,
    UpdateRideStatusView,
    RideLocationLogView,
    CancelRideView, 
    RejectRideView,
    ListPreviousRidesView,
)

urlpatterns = [
    path("book/", BookRideView.as_view()),
    path("available/", AvailableRidesForDriverView.as_view()),
    path("accept/", AcceptRideView.as_view()),
    path("status/", UpdateRideStatusView.as_view()),
    path("location/", RideLocationLogView.as_view()),
    path("reject/", RejectRideView.as_view()),
    path("cancel/", CancelRideView.as_view()),
    path("list_previous_rides/<uuid:user_id>", ListPreviousRidesView.as_view()),
    
]