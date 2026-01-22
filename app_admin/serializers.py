from rest_framework import serializers
from .models import KYCDetails, KYCMedia, KYCTypeLookup, KYCStatusLookup
from authentication.models import User
from drivers.models import Driver

class KYCMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCMedia
        fields = ["kyc_media_id", "media_url", "media_type", "uploaded_at"]


class KYCDetailsSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    tenant_id = serializers.UUIDField()
    driver = serializers.StringRelatedField()
    kyc_type = serializers.StringRelatedField()
    kyc_status = serializers.StringRelatedField()
    media = KYCMediaSerializer(source="kymedia_set", many=True, read_only=True)

    class Meta:
        model = KYCDetails
        fields = [
            "kyc_id",
            "user",
            "driver",
            "tenant_id",
            "kyc_type",
            "kyc_status",
            "submitted_at",
            "verified_at",
            "rejected_reason",
            "media",
        ]


class KYCUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDetails
        fields = ["kyc_status", "rejected_reason", "verified_at", "kyc_type", "user", "tenant_id"]
