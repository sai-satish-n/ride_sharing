from django.utils import timezone
import uuid
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from authentication.models import User, UserRole, Role, TenantUser, Tenant, TenantStatusLookup, UserStatusLookup
from authentication.serializers import UserRegisterSerializer, LoginSerializer, UserProfileUpdateSerializer
from utils.auth_utils import *
from drivers.models import Driver, DriverStatusLookup

class RegisterView(APIView):
    permission_classes = []  # Allow unauthenticated users

    def post(self, request):
        serializer = UserRegisterSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid(raise_exception=True):
            user = serializer.save()

            # Step 2: Create a user role (Default role for normal user)
            user_role = Role.objects.get(role_name = "user")  # Assuming 1 is the "Normal User" role
            UserRole.objects.create(user=user, role=user_role)


            # Step 3: Handle Tenant registration
            tenant_data = request.data.get('tenant', {})
            if tenant_data:
                tenant_name = tenant_data.get('tenant_name')
                support_email = tenant_data.get('support_email', None)
                support_phone = tenant_data.get('support_phone', None)
                
                # Create the tenant record
                tenant = Tenant.objects.create(
                    tenant_name=tenant_name,
                    support_email=support_email,
                    support_phone=support_phone,
                    tenant_status=TenantStatusLookup.objects.get(status_name = "PENDING_VERIFICATION"),  # Assuming tenant status ID 1
                    verified_at=None  # Not yet verified; this can be updated later by app_admin
                )

                # Step 4: Create the TenantUser association
                TenantUser.objects.create(
                    user=user,
                    tenant=tenant,
                    tenant_role=user_role,  # Default role (e.g., "Normal User" for tenant)
                    status=UserStatusLookup.objects.get(status_name = "ACTIVE"),  # Status (user is "active", "pending", etc.)
                    joined_at=timezone.now()
                )

                user_role = Role.objects.get(role_name = "tenant")  # Assuming 1 is the "Normal User" role
                UserRole.objects.create(user=user, role=user_role, tenant_id=tenant.tenant_id)
                UserRole.objects.filter(user=user, role__role_name="user").delete()  # Remove previous user role
            else:
                print("No tenant data provided; skipping tenant creation.")
            
            # Step 5: Handle Driver registration (if applicable)
            if 'driving_licence_number' in request.data.get('driver', {}).keys():
                # If the user is registering as a driver
                driver_data = request.data.get('driver', {})
                driving_licence_number = driver_data.get('driving_licence_number')
                current_latitude = driver_data.get('current_latitude', 0.0)
                current_longitude = driver_data.get('current_longitude', 0.0)
                
                # Assuming the "driver_status" is 1 (Online) as default
                driver_status = DriverStatusLookup.objects.get(status_name = "active")  # Assuming driver status ID 1

                # Create the driver record
                Driver.objects.create(
                    user=user,
                    driving_licence_number=driving_licence_number,
                    driver_online_status=driver_status,
                    current_latitude=current_latitude,
                    current_longitude=current_longitude,
                    last_location="Not updated yet",  # You can update this later
                    location_updated_at=None
                )

                user_role = Role.objects.get(role_name = "driver")  # Assuming 1 is the "Normal User" role
                UserRole.objects.create(user=user, role=user_role)
            else:
                print("No driver data provided; skipping driver creation.")

            # Return success response
            return Response(
                {
                    "message": "User registered successfully",
                    "user_id": user.user_id,
                    "phone": user.phone,
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        roles = UserRole.objects.filter(user=user).select_related("role")

        if not roles.exists():
            return Response(
                {"error": "No roles assigned"}, status=status.HTTP_403_FORBIDDEN
            )

        # Single role → issue tokens
        if roles.count() == 1:
            role = roles.first().role

            access_token = generate_access_token(
                {"user_id": str(user.user_id), "role": role.role_id}
            )

            refresh_token = generate_refresh_token(
                {"user_id": str(user.user_id), "role": role.role_id}
            )

            encrypted_access = encrypt_jwt(access_token)
            encrypted_refresh = encrypt_jwt(refresh_token)

            response = Response(
                {
                    "access_token": encrypted_access,
                    "role": role.role_id,
                    "user": {
                        "user_id": user.user_id,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "phone": user.phone,
                        "phone_country_code": user.phone_country_code,
                    },
                }
            )

            response.set_cookie(
                "access_token",
                encrypted_access,
                httponly=True,
                secure=True,
                samesite="Strict",
                max_age=900,
            )

            # Refresh token in HttpOnly cookie
            response.set_cookie(
                key="refresh_token",
                value=encrypted_refresh,
                httponly=True,
                secure=True,
                samesite="Strict",
                max_age=7 * 24 * 60 * 60,
            )

            return response

        # Multiple roles → choose role
        session_id = str(uuid.uuid4())
        request.session[session_id] = str(user.user_id)

        return Response(
            {
                "message": "Multiple roles found",
                "login_session_id": session_id,
                "roles": [
                    {"id": r.role.role_id, "code": r.role.role_name} for r in roles
                ],
            }
        )


# pending - select multiple roles
class RoleSelectView(APIView):
    permission_classes = []

    def post(self, request):
        session_id = request.data.get("login_session_id")
        role_id = request.data.get("role_id")

        user_id = request.session.get(session_id)
        user = User.objects.get(user_id=user_id)

        if not user_id:
            return Response(
                {"error": "Invalid session"}, status=status.HTTP_401_UNAUTHORIZED
            )

        role = UserRole.objects.get(user_id=user_id, role_id=role_id).role

        access_token = generate_access_token(
            {"user_id": str(user_id), "role": role.role_id}
        )

        refresh_token = generate_refresh_token(
            {"user_id": str(user_id), "role": role.role_id}
        )

        encrypted_access = encrypt_jwt(access_token)
        encrypted_refresh = encrypt_jwt(refresh_token)

        response = Response(
            {
                "access_token": encrypted_access,
                "role": role.role_id,
                "user": {
                    "user_id": user.user_id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "phone_country_code": user.phone_country_code,
                },
            }
        )

        response.set_cookie(
            "access_token",
            encrypted_access,
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=900,
        )

        # Refresh token in HttpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=encrypted_refresh,
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=7 * 24 * 60 * 60,
        )

        return response



class RefreshTokenView(APIView):
    permission_classes = []

    def post(self, request):
        encrypted_refresh = request.COOKIES.get("refresh_token")

        if not encrypted_refresh:
            return Response(
                {"error": "Refresh token missing"}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh_token = decrypt_jwt(encrypted_refresh)
            payload = decode_jwt(refresh_token)

            if payload.get("type") != "refresh":
                raise Exception("Invalid token type")

            new_access = generate_access_token(
                {"user_id": payload["user_id"], "role": payload["role"]}
            )

            encrypted_access = encrypt_jwt(new_access)
            response = Response({"access_token": encrypted_access})

            response.delete_cookie("access_token")
            response.set_cookie(
                "access_token",
                encrypted_access,
                httponly=True,
                secure=True,
                samesite="Strict",
                max_age=900,
            )

            return response

        except Exception:
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    def post(self, request):
        response = Response({"message": "Logged out"})
        response.delete_cookie("refresh_token")
        response.delete_cookie("access_token")
        return response


class UpdateUserProfileView(APIView):
    permission_classes = []

    def patch(self, request):
        user = User.objects.get(user_id = request.data.get('user_id'))

        serializer = UserProfileUpdateSerializer(
            user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)