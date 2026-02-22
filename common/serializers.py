from rest_framework import serializers
from rides.models import Country, State, RegionTypeLookup, Region
from common.models import KYCDetails, KYCStatusLookup, KYCMedia


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'

class StateSerializer(serializers.ModelSerializer):
    # Display the country name in GET requests
    country_name = serializers.ReadOnlyField(source='country.country_name')
    
    class Meta:
        model = State
        fields = '__all__'

class RegionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionTypeLookup
        fields = '__all__'

class RegionSerializer(serializers.ModelSerializer):
    country_name = serializers.ReadOnlyField(source='country.country_name')
    state_name = serializers.ReadOnlyField(source='state.state_name')
    region_type_name = serializers.ReadOnlyField(source='region_type.region_type')

    class Meta:
        model = Region
        fields = '__all__'
        read_only_fields = ['region_code']





class CreateRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = [
            'country',
            'state',
            'region_name',
            'region_type',
            'geo_boundary',
            'is_surge_enabled',
            'is_service_active'
        ]


class KYCMediaSerializer(serializers.ModelSerializer):
    kyc_type = serializers.StringRelatedField()
    kyc_status = serializers.StringRelatedField()
    class Meta:
        model = KYCMedia
        fields = ["kyc_media_id", "media_url", "media_type", "uploaded_at", "kyc_type", "kyc_status", "rejected_reason"]


class KYCDetailsSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    tenant_id = serializers.UUIDField()
    driver = serializers.StringRelatedField()
    kyc_status = serializers.StringRelatedField()
    media = KYCMediaSerializer(
        source="kycmedia_set", 
        many=True, 
        read_only=True
    )

    class Meta:
        model = KYCDetails
        fields = [
            "kyc_id",
            "user",
            "driver",
            "tenant_id",
            "kyc_status",
            "submitted_at",
            "verified_at",
            "media",
        ]


class KYCUpdateSerializer(serializers.ModelSerializer):
    kyc_status = serializers.SlugRelatedField(
        slug_field='kyc_status', 
        queryset=KYCStatusLookup.objects.all(),
        required=False
    )
    
    class Meta:
        model = KYCDetails
        fields = ["kyc_status", "rejected_reason", "verified_at", "kyc_id", "user", "tenant_id",  "driver", "kyc_type"]
