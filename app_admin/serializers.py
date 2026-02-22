from rest_framework import serializers
from authentication.models import User, Tenant, TenantStatusLookup

class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'user_id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'is_email_verified',
            'is_phone_verified',
            'phone_country_code',
            'user_status',
            'created_at'
        ]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'user_id',
            'first_name',
            'last_name',
            'email',
            'user_status',
            'is_email_verified',
            'is_phone_verified'
        ]


class TenantListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'


class AssignUserRoleSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role_id = serializers.IntegerField()
    tenant_id = serializers.UUIDField(required=False, allow_null=True)


class TenantStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantStatusLookup
        fields = ['tenant_status_id', 'status_name']

