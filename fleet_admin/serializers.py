from rest_framework import serializers
from rides.models import TenantRegion, VehicleType, Vehicle, RegionTypeLookup, State, Region, Country
from drivers.models import VehicleDriverAssignment, DriverFleetAssignment
from fleet_admin.models import Fleet


class TenantRegionSerializer(serializers.ModelSerializer):
    country_name = serializers.ReadOnlyField(source='region.country.country_name')
    state_name = serializers.ReadOnlyField(source='region.state.state_name')
    region_type_name = serializers.ReadOnlyField(source='region.region_type.region_type')
    region_name = serializers.ReadOnlyField(source='region.region_name')
    geo_boundary = serializers.ReadOnlyField(source='region.geo_boundary')
    is_surge_enabled = serializers.ReadOnlyField(source='region.is_surge_enabled')
    is_service_active = serializers.ReadOnlyField(source='is_active')
    created_at = serializers.ReadOnlyField(source='region.created_at')
    updated_at = serializers.ReadOnlyField(source='region.updated_at')
    country = serializers.ReadOnlyField(source='region.country.country_code')
    state = serializers.ReadOnlyField(source='region.state_id')
    region_type = serializers.ReadOnlyField(source='region.region_type_id')
    region_code = serializers.ReadOnlyField(source='region.region_code')
    

    class Meta:
        model = TenantRegion
        fields = [
            "region_nick_name",
            "region_code",
            "country_name",
            "state_name",
            "region_type_name",
            "region_name",
            "geo_boundary",
            "is_surge_enabled",
            "is_service_active",
            "created_at",
            "updated_at",
            "country",
            "state",
            "region_type",
            "tenant_region_id"
        ]





class VehicleTypeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='vehicle_type_id')
    name = serializers.CharField(source='vehicle_name')

    class Meta:
        model = VehicleType
        fields = ['id', 'name', 'vehicle_capacity', 'vehicle_category']


class CreateVehicleSerializer(serializers.ModelSerializer):
    is_default = serializers.BooleanField(write_only=True, required=False)
    class Meta:
        model = Vehicle
        fields = [
            'is_default',
            'vehicle_number',
            'vehicle_type',
            'vehicle_conditon',
            'fleet_tenant_id'
        ]
        read_only_fields = ['fleet_tenant_id',]



class CreateVehicleDriverAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleDriverAssignment
        fields = ['vehicle', 'driver', 'start_time', 'end_time']



class FleetSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.region_name', read_only=True)

    class Meta:
        model = Fleet
        fields = [
            'fleet_id',
            'fleet_name',
            'region',
            'region_name',
            'is_active',
            'created_at'
        ]


class DriverSearchResultSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    driver_id = serializers.UUIDField()
    first_name = serializers.CharField()
    last_name = serializers.CharField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    phone = serializers.CharField()

class AddDriverToFleetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverFleetAssignment
        fields = [
            'fleet',
            'driver',
            'tenant_id',
            'start_date'
        ]


