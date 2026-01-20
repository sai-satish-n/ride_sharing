from rest_framework import serializers
from authentication.models import User
import uuid
from django.contrib.auth.hashers import make_password, check_password

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "phone_country_code",
            "password",
        ]
        read_only_fields = ["user_id"]

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone number already registered.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User.objects.create(
            user_id=uuid.uuid4(),
            password_hash=make_password(password),
            is_email_verified=False,
            is_phone_verified=False,
            created_at=self.context["request"]._request.timestamp
            if hasattr(self.context["request"]._request, "timestamp")
            else None,
            **validated_data
        )

        return user

class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField()

    def validate(self, data):
        phone = data.get("phone")
        email = data.get("email")
        password = data["password"]

        if not phone and not email:
            raise serializers.ValidationError(
                "Phone or Email is required."
            )

        try:
            user = User.objects.get(
                phone=phone if phone else None
            ) if phone else User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        if not check_password(password, user.password_hash):
            raise serializers.ValidationError("Invalid credentials")

        data["user"] = user
        return data
