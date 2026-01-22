from django.urls import path
from app_admin.views import *

urlpatterns = [
    path("view/all/", ViewAllKYC.as_view()),
    path("view/pending/", ViewPendingKYC.as_view()),
    path("view/<uuid:kyc_id>/", ViewKYC.as_view()),
    path("view/user/", ViewUserKYC.as_view()),
    path("accept/", AcceptKYCView.as_view()),
    path("reject/", RejectKYCView.as_view()),
    path("update/<uuid:kyc_id>/", UpdateKYCView.as_view()),
    path("search/", SearchKYCView.as_view()),
]
