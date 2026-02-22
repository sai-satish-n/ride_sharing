from django.db import models

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from rides.models import TenantRegion, Country, State, RegionTypeLookup, Region
import uuid

class CreateAndAssignRegionAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        data = request.data
        tenant_id = data.get('tenant_id') # From frontend/user context
        
        # 1. Create the Global Region
        try:
            # Get related objects
            country = Country.objects.get(country_code=data.get('country_code'))
            state = None
            if data.get('state_code'):
                state = State.objects.get(state_code=data.get('state_code'))
            
            region_type = RegionTypeLookup.objects.get(
                region_type_id=data.get('region_type_id')
            )

            # Create Global Region
            new_region = Region.objects.create(
                country=country,
                state=state,
                region_name=data.get('region_name'),
                region_type=region_type,
                is_surge_enabled=data.get('is_surge_enabled', True),
                is_service_active=data.get('is_service_active', True)
            )

            # 2. Create the Tenant Assignment (The link)
            tenant_region = TenantRegion.objects.create(
                tenant_id=tenant_id,
                region=new_region,
                is_active=True
            )

            return Response({
                "message": "Region created and assigned successfully",
                "region_code": new_region.region_code,
                "tenant_region_id": tenant_region.tenant_region_id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    
class Fleet(models.Model):
    fleet_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fleet_name = models.CharField(max_length=100)
    tenant = models.ForeignKey('authentication.Tenant', on_delete=models.CASCADE)
    # Linking fleet to a specific region assigned to that tenant
    region = models.ForeignKey('rides.Region', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fleets"
        unique_together = ('tenant', 'fleet_name')

    def __str__(self):
        return f"{self.fleet_name} ({self.region.region_name})"