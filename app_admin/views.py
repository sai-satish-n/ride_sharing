from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app_admin.models import KYCDetails, KYCStatusLookup
from app_admin.serializers import KYCDetailsSerializer, KYCUpdateSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

# View all KYC
class ViewAllKYC(APIView):
    def get(self, request):
        kycs = KYCDetails.objects.all().select_related("kyc_type", "kyc_status", "user", "driver")
        serializer = KYCDetailsSerializer(kycs, many=True)
        return Response(serializer.data)


# View pending KYC
class ViewPendingKYC(APIView):
    def get(self, request):
        pending_status = KYCStatusLookup.objects.get(kyc_status="PENDING_APPROVAL")
        kycs = KYCDetails.objects.filter(kyc_status=pending_status)
        serializer = KYCDetailsSerializer(kycs, many=True)
        return Response(serializer.data)


# View particular KYC by ID
class ViewKYC(APIView):
    def get(self, request, kyc_id):
        kyc = get_object_or_404(KYCDetails, kyc_id=kyc_id)
        serializer = KYCDetailsSerializer(kyc)
        return Response(serializer.data)


# Fetch all KYC for a user
class ViewUserKYC(APIView):
    def get(self, request):
        query = Q()
        user_id = request.data.get("user_id")
        tenant_id = request.data.get("tenant_id")
        driver_id = request.data.get("driver_id")
        if user_id:
            query &= Q(user_id=user_id)
        if tenant_id:
            query &= Q(tenant_id=tenant_id)
        if driver_id:
            query &= Q(driver_id=driver_id)
        
        kycs = KYCDetails.objects.filter(query)
        serializer = KYCDetailsSerializer(kycs, many=True)
        return Response(serializer.data)


# Accept KYC
class AcceptKYCView(APIView):
    def post(self, request):
        data = request.data
        kyc_id = data.get('kyc_id')
        kyc = get_object_or_404(KYCDetails, kyc_id=kyc_id)
        approved_status = KYCStatusLookup.objects.get(kyc_status="APPROVED")
        kyc.kyc_status = approved_status
        kyc.verified_at = timezone.now()
        kyc.rejected_reason = None
        kyc.save()
        serializer = KYCDetailsSerializer(kyc)
        return Response(serializer.data)


# Reject KYC
class RejectKYCView(APIView):
    def post(self, request):
        data = request.data
        kyc_id = data.get('kyc_id')
        kyc = get_object_or_404(KYCDetails, kyc_id=kyc_id)
        rejected_status = KYCStatusLookup.objects.get(kyc_status="REJECTED")
        kyc.kyc_status = rejected_status
        kyc.rejected_reason = request.data.get("rejected_reason", "No reason provided")
        kyc.save()
        serializer = KYCDetailsSerializer(kyc)
        return Response(serializer.data)


# Update KYC
class UpdateKYCView(APIView):
    def post(self, request, kyc_id):
        kyc = get_object_or_404(KYCDetails, kyc_id=kyc_id)
        serializer = KYCUpdateSerializer(kyc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(KYCDetailsSerializer(kyc).data)


# Search KYC
class SearchKYCView(APIView):
    def post(self, request):
        query = Q()
        user_id = request.data.get("user_id")
        tenant_id = request.data.get("tenant_id")
        driver_id = request.data.get("driver_id")
        kyc_status = request.data.get("kyc_status")
        kyc_type = request.data.get("kyc_type")

        if user_id:
            query &= Q(user_id=user_id)
        if tenant_id:
            query &= Q(tenant_id=tenant_id)
        if driver_id:
            query &= Q(driver_id=driver_id)
        if kyc_status:
            query &= Q(kyc_status__kyc_status=kyc_status)
        if kyc_type:
            query &= Q(kyc_type__kyc_type=kyc_type)

        kycs = KYCDetails.objects.filter(query)
        serializer = KYCDetailsSerializer(kycs, many=True)
        return Response(serializer.data)
