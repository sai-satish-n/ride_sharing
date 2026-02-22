from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from common.models import KYCDetails, KYCStatusLookup, KYCTypeLookup, KYCMedia
from rides.models import Driver, Region, Country, State, RegionTypeLookup
from authentication.models import TenantUser
from common.serializers import CountrySerializer, StateSerializer, RegionSerializer, RegionTypeSerializer
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.utils import timezone


class KYCUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        user_id = request.data.get("user_id")
        user_type = request.data.get("user_type")  # 'driver' or 'tenant'

        # Define document mappings based on your KYC_TYPE_LOOKUP IDs
        if user_type == 'driver':
            type_mapping = {'aadhaar': 2, 'pan': 1, 'driving_license': 3}
        else:
            type_mapping = {'aadhaar': 2, 'business_docs': 4}

        status_pending = KYCStatusLookup.objects.get(kyc_status="PENDING_APPROVAL")

        if user_type == "tenant":
            tenant_user = TenantUser.objects.get(user_id=user_id)

            kyc_detail, _ = KYCDetails.objects.get_or_create(
                user_id=user_id,
                tenant_id_id=tenant_user.tenant_id,
                defaults={"kyc_status": status_pending}
            )

        elif user_type == "driver":
            driver = Driver.objects.get(user_id=user_id)

            kyc_detail, _ = KYCDetails.objects.get_or_create(
                driver_id=driver.driver_id,
                defaults={"kyc_status": status_pending}
            )
        else:
            return Response({"error": "Invalid user type"}, status=400)
        
        kyc_detail.kyc_status = status_pending
        kyc_detail.verified_at = None
        kyc_detail.save()

        for key, type_id in type_mapping.items():
            file_obj = request.FILES.get(key)

            if not file_obj:
                continue

            # Remove old media of same type
            KYCMedia.objects.filter(
                kyc=kyc_detail,
                kyc_type_id=type_id
            ).delete()

            path = default_storage.save(
                f"kyc/{user_type}/{user_id}/{key}_{file_obj.name}",
                file_obj
            )

            KYCMedia.objects.create(
                kyc=kyc_detail,
                kyc_type_id=type_id,
                kyc_status=status_pending,
                media_url=path,
                media_type=file_obj.content_type,
                rejected_reason=None
            )

        return Response({"status": "Success"}, status=201)


class KYCTypeListView(APIView):
    def get(self, request):
        types = KYCTypeLookup.objects.all().values("kyc_type_id", "kyc_type")
        return Response(types)


class KYCStatusDetailView(APIView):
    def get(self, request, user_id):
        user_type = request.query_params.get("user_type", "driver")

        try:
            if user_type == "driver":
                driver = Driver.objects.get(user_id=user_id)
                kyc_detail = KYCDetails.objects.select_related(
                    "kyc_status"
                ).prefetch_related(
                    "kycmedia_set__kyc_type",
                    "kycmedia_set__kyc_status"
                ).get(driver_id=driver.driver_id)

            elif user_type == "tenant":
                tenant_user = TenantUser.objects.get(user_id=user_id)
                kyc_detail = KYCDetails.objects.select_related(
                    "kyc_status"
                ).prefetch_related(
                    "kycmedia_set__kyc_type",
                    "kycmedia_set__kyc_status"
                ).get(
                    user_id=user_id,
                    tenant_id=tenant_user.tenant_id
                )
            else:
                return Response({"error": "Invalid user type"}, status=400)

        except (Driver.DoesNotExist, TenantUser.DoesNotExist, KYCDetails.DoesNotExist):
            return Response({"error": "KYC not found"}, status=404)

        latest_docs = {}

        for media in kyc_detail.kycmedia_set.all().order_by("-uploaded_at"):
            type_id = media.kyc_type_id
            if type_id not in latest_docs:
                latest_docs[type_id] = media

        data = []
        for media in latest_docs.values():
            data.append({
                "kyc_id": kyc_detail.kyc_id,
                "kyc_type_id": media.kyc_type.kyc_type_id,
                "kyc_type_name": media.kyc_type.kyc_type,
                "kyc_status_name": media.kyc_status.kyc_status,
                "submitted_at": media.uploaded_at,
                "rejected_reason": media.rejected_reason,
                "existing_media_url": media.media_url,
            })

        return Response(data)




# --- COUNTRY CRUD ---
class CountryAPIView(APIView):
    def get(self, request, pk=None):
        get_all = request.query_params.get("all")
        
        if pk:
            country = get_object_or_404(Country, country_code=pk)
            serializer = CountrySerializer(country)
            return Response(serializer.data)
        
        countries = Country.objects.all()
        if not get_all:
            countries = Country.objects.filter(deleted_at__isnull=True)
        
        countries = countries.order_by("country_name")
        
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CountrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        country = get_object_or_404(Country, country_code=pk)
        serializer = CountrySerializer(country, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        country = get_object_or_404(Country, country_code=pk)
        # country.delete()
        country.deleted_at = timezone.now()
        country.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- STATE CRUD ---
class StateAPIView(APIView):
    def get(self, request, pk=None):
        country_code = request.query_params.get("country_code")
        get_all = request.query_params.get("all")
        
        
        if pk:
            state = get_object_or_404(State, state_code=pk)
            return Response(StateSerializer(state).data)
        
        states = State.objects.all()

        if country_code:
            states = states.filter(country_id=country_code)

        if not get_all:
            states = states.filter(deleted_at__isnull=True)

        return Response(StateSerializer(states, many=True).data)

    def post(self, request):
        serializer = StateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def put(self, request, pk):
        state = get_object_or_404(State, state_code=pk)
        serializer = StateSerializer(state, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        state = get_object_or_404(State, state_code=pk)
        # state.delete()
        state.deleted_at = timezone.now()
        state.save()
        return Response(status=204)


# --- REGION CRUD ---
class RegionAPIView(APIView):
    def get(self, request, pk=None):
        get_all = request.query_params.get("all")
        
        if pk:
            region = get_object_or_404(Region, region_code=pk)
            return Response(RegionSerializer(region).data)

        # Filtering for frontend dropdown logic
        state_code = request.query_params.get("state_code")
        
        regions = Region.objects.all().select_related(
            "country", "state", "region_type"
        )

        if state_code:
            regions = regions.filter(state_id=state_code)

        if not get_all:
            regions = regions.filter(deleted_at__isnull=True)

        return Response(RegionSerializer(regions, many=True).data)

    def post(self, request):
        serializer = RegionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def put(self, request, pk):
        region = get_object_or_404(Region, region_code=pk)
        serializer = RegionSerializer(region, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        region = get_object_or_404(Region, region_code=pk)
        # region.delete()
        region.deleted_at = timezone.now()
        region.save()
        return Response(status=204)


# --- LOOKUPS ---
class RegionTypeLookupView(APIView):
    def get(self, request):
        types = RegionTypeLookup.objects.all()
        return Response(RegionTypeSerializer(types, many=True).data)