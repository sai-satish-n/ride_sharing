from django.urls import path
from app_admin.views import *

urlpatterns = [
    path("view/pending/", ViewPendingKYC.as_view()),
    path("search/", SearchKYCView.as_view()),           #not included in frontend
    
    path('kyc/tenants/', ListTenantsKYCAPIView.as_view()),
    path('kyc/<uuid:tenant_id>/media/', ListKYCMediaAPIView.as_view()),
    path('kyc/<uuid:tenant_id>/update-status/', UpdateKYCView.as_view()),
    
    path('users/', ListUsersAPIView.as_view()),
    path('user/role/assign', AssignUserRoleAPIView.as_view()),
    path('user/role/remove', RemoveUserRoleAPIView.as_view()),
    path('user/roles/<uuid:user_id>/', ListUserRolesAPIView.as_view()),
    path('roles/list/all', ListAllRolesAPIView.as_view(), name='list-all-roles'),
]
