from django.urls import path
from .views import *

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("login_multiple_role/", RoleSelectView.as_view(), name=""),
    path("refresh/", RefreshTokenView.as_view(), name="refresh_token"),
    path("logout/", LogoutView.as_view(), name="logout"),
]