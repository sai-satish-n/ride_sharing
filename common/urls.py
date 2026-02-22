from django.urls import path
from common.views import *

urlpatterns = [
    path("kyc/types/", KYCTypeListView.as_view()),
    path("kyc/upload/", KYCUploadView.as_view()),
    path("kyc/status/<uuid:user_id>/", KYCStatusDetailView.as_view()),

    path('countries/', CountryAPIView.as_view(), name='country-list-create'),
    path('countries/<str:pk>/', CountryAPIView.as_view(), name='country-detail'),

    path('states/', StateAPIView.as_view(), name='state-list-create'),
    path('states/<uuid:pk>/', StateAPIView.as_view(), name='state-detail'),

    path('regions/', RegionAPIView.as_view(), name='region-list-create'),
    path('regions/<uuid:pk>/', RegionAPIView.as_view(), name='region-detail'),

    path('region-types/', RegionTypeLookupView.as_view(), name='region-type-lookup'),
]
