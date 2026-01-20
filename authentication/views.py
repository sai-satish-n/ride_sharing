import uuid
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from authentication.models import User, UserRole
from authentication.serializers import UserRegisterSerializer, LoginSerializer
from authentication.utils import *


class RegisterView(APIView):
    permission_classes = []  # Allow unauthenticated users

    def post(self, request):
        serializer = UserRegisterSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            user = serializer.save()
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

            response = Response({"access_token": encrypted_access, "role": role.role_id})

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
                "roles": [{"id": r.role.role_id, "code": r.role.role_name} for r in roles],
            }
        )


# pending - select multiple roles
class RoleSelectView(APIView):
    permission_classes = []

    def post(self, request):
        session_id = request.data.get("login_session_id")
        role_id = request.data.get("role_id")

        user_id = request.session.get(session_id)

        if not user_id:
            return Response(
                {"error": "Invalid session"}, status=status.HTTP_401_UNAUTHORIZED
            )

        role = UserRole.objects.get(user_id=user_id, role_id=role_id).role

        jwt_token = generate_jwt({"user_id": user_id, "role": role.role_id})

        encrypted_token = encrypt_jwt(jwt_token)

        del request.session[session_id]

        return Response({"token": encrypted_token, "role": role.role_id})


class TenantUserCreateAPIView(APIView):
    permission_classes = []

    def post(self, request):
        tenant = request.user_context.tenant
        role_id = request.data.get("role_id")

        user = User.objects.create_user(
            email=request.data["email"],
            password=request.data["password"],
            phone=request.data["phone"],
        )

        UserRole.objects.create(
            user=user, tenant=tenant, role_id=role_id, assigned_by=tenant
        )

        return Response({"message": "User created under tenant"}, status=201)


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
