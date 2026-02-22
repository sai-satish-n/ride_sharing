from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from common.models import KYCDetails, KYCStatusLookup
from app_admin.serializers import *
from django.db.models import Q
from django.utils import timezone, dateparse
from authentication.models import User, UserRole, Role
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from common.serializers import KYCDetailsSerializer
import uuid


# View pending KYC
class ViewPendingKYC(APIView):
    def get(self, request):
        pending_status = KYCStatusLookup.objects.get(kyc_status="PENDING_APPROVAL")
        kycs = KYCDetails.objects.filter(kyc_status=pending_status).distinct(
            "tenant_id"
        )
        serializer = KYCDetailsSerializer(kycs, many=True)
        return Response(serializer.data)


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


class ListUsersAPIView(APIView):
    def get(self, request):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        users = User.objects.all().order_by("-created_at")

        paginator = Paginator(users, limit)
        page_obj = paginator.get_page(page)

        serializer = AdminUserListSerializer(page_obj, many=True)

        return Response(
            {
                "count": paginator.count,
                "total_pages": paginator.num_pages,
                "current_page": page,
                "results": serializer.data,
            }
        )


class ListAllRolesAPIView(APIView):
    """
    Returns a list of all available roles in the system
    to populate admin dropdowns.
    """

    def get(self, request):
        # Fetching all roles from the master Role table
        roles = Role.objects.all().values("role_id", "role_name")
        return Response(list(roles), status=status.HTTP_200_OK)


class ListUserRolesAPIView(APIView):
    def get(self, request, user_id):
        # Use select_related to get the actual Role details in one query
        user_roles = UserRole.objects.filter(user_id=user_id).select_related("role")

        data = [
            {
                "role_id": ur.role.role_id,
                "role_name": ur.role.role_name,  # This provides the string name
                "tenant_id": ur.tenant_id,
            }
            for ur in user_roles
        ]

        return Response(data, status=200)  # This returns a clean list []


class AssignUserRoleAPIView(APIView):
    def post(self, request):
        serializer = AssignUserRoleSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data

        try:
            user = User.objects.get(user_id=data["user_id"])
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        try:
            role = Role.objects.get(role_id=data["role_id"])
        except Role.DoesNotExist:
            return Response({"error": "Role not found"}, status=404)

        tenant_id = data.get("tenant_id")

        tenant = None
        if tenant_id is not None:
            try:
                tenant = Tenant.objects.get(tenant_id=tenant_id)
            except Tenant.DoesNotExist:
                return Response({"error": "Tenant not found"}, status=404)

        # 🔒 Prevent duplicate role assignment
        if UserRole.objects.filter(user=user, role=role, tenant_id=tenant).exists():
            return Response({"error": "Role already assigned to user"}, status=400)

        UserRole.objects.create(
            user=user,
            role=role,
            tenant_id=tenant,
            assigned_by=tenant,
        )

        return Response({"message": "Role assigned successfully"}, status=201)


class RemoveUserRoleAPIView(APIView):
    def delete(self, request):
        user_id = request.data.get("user_id")
        role_id = request.data.get("role_id")
        tenant_id = request.data.get("tenant_id")

        if not user_id or not role_id:
            return Response({"error": "user_id and role_id are required"}, status=400)

        deleted, _ = UserRole.objects.filter(
            user_id=user_id, role_id=role_id, tenant_id=tenant_id
        ).delete()

        if deleted == 0:
            return Response({"error": "Role assignment not found"}, status=404)

        return Response({"message": "Role removed successfully"}, status=200)


class ListTenantsKYCAPIView(APIView):
    def get(self, request):
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))  # dynamic page size
        email = request.query_params.get("email")
        status = request.query_params.get("status")
        sort = request.query_params.get("sort", "newest")  # newest/oldest/verified
        start_date =request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        tenants = Tenant.objects.all()

        # Filter by email if provided
        if email:
            tenants = tenants.filter(support_email__icontains=email)

        # Filter by tenant_status name if provided
        # Filter by tenant KYC status
        if status and status != "ALL":
            tenant_ids_with_status = []
            for tenant in tenants:
                kycs = KYCDetails.objects.filter(tenant_id=tenant)
                if not kycs.exists():
                    tenant_status = "DOCUMENTS_NOT_SUBMITTED"
                elif any(k.kyc_status.kyc_status == "REJECTED" for k in kycs):
                    tenant_status = "REJECTED"
                elif all(k.kyc_status.kyc_status == "APPROVED" for k in kycs):
                    tenant_status = "VERIFIED"
                else:
                    tenant_status = "PENDING_APPROVAL"
                if tenant_status == status:
                    tenant_ids_with_status.append(tenant.tenant_id)
            tenants = tenants.filter(tenant_id__in=tenant_ids_with_status)

        if start_date:
            start_date = dateparse.parse_date(start_date)
            if start_date:
                tenants = tenants.filter(created_at__date__gte=start_date)

        if end_date:
            end_date = dateparse.parse_date(end_date)
            if end_date:
                tenants = tenants.filter(created_at__date__lte=end_date)

        # Sorting
        sort_mapping = {
            "newest": "-created_at",
            "oldest": "created_at",
            "verified": "-verified_at",  # descending verified_at
            "unverified": "vertified_at",  # ascending verified_at
        }

        sort_field = sort_mapping.get(sort, "-created_at")
        tenants = tenants.order_by(sort_field)

        # Pagination
        paginator = Paginator(tenants, limit)
        page_obj = paginator.get_page(page)

        results = []
        for tenant in page_obj:
            kycs = KYCDetails.objects.filter(tenant_id=tenant, driver_id__isnull=True)
            if not kycs.exists():
                kyc_status = "DOCUMENTS_NOT_SUBMITTED"
            elif any(k.kyc_status.kyc_status == "REJECTED" for k in kycs):
                kyc_status = "REJECTED"
            elif all(k.kyc_status.kyc_status == "APPROVED" for k in kycs):
                kyc_status = "VERIFIED"
            else:
                kyc_status = "PENDING_APPROVAL"

            results.append(
                {
                    "tenant_id": tenant.tenant_id,
                    "tenant_name": tenant.tenant_name,
                    "user_email": tenant.support_email,
                    "created_at": tenant.created_at,
                    "kyc_status": kyc_status,
                    "user": {
                        "first_name": tenant.tenant_name,
                        "last_name": (
                            tenant.verified_by_user.last_name
                            if tenant.verified_by_user
                            else ""
                        ),
                    },
                }
            )

        return Response({"count": paginator.count, "results": results})


class ListKYCMediaAPIView(APIView):
    def get(self, request, tenant_id):
        tenant = get_object_or_404(Tenant, tenant_id=tenant_id)
        kycs = (
            KYCDetails.objects.filter(tenant_id=tenant)
            .select_related(
                "kyc_status",
                "driver",
                "user",
                "tenant_id",
            )
            .prefetch_related(
                "kycmedia_set__kyc_type",  # include kyc_type of each media
                "kycmedia_set__kyc_status",
            )
        )
        # media = KYCMedia.objects.filter(kyc__in=kyc)
        media_list = []
        for kyc in kycs:
            for media in kyc.kycmedia_set.all().order_by("-uploaded_at"):
                media_list.append({
                    "kyc_media_id": str(media.kyc_media_id),
                    "kyc_type_id": media.kyc_type.kyc_type_id,
                    "kyc_type_name": media.kyc_type.kyc_type,
                    "kyc_status": media.kyc_status.kyc_status,
                    "media_url": media.media_url,
                    "media_type": media.media_type,
                    "rejected_reason": media.rejected_reason,
                    "uploaded_at": media.uploaded_at
                })

        # Sort globally by uploaded_at descending
        media_list.sort(key=lambda x: x["uploaded_at"], reverse=True)

        return Response({"results": media_list})


class UpdateKYCView(APIView):
    """
    Update KYC status (APPROVED/REJECTED) for tenant media.
    """

    def post(self, request, tenant_id):
        kyc_media_id = request.data.get("kyc_media_id")
        status = request.data.get("status")
        rejected_reason = request.data.get("rejected_reason", "")

        try:
            kyc_media_id = uuid.UUID(kyc_media_id)
        except (ValueError, TypeError):
            return Response({"error": "Invalid KYC Media ID"}, status=400)

        media = get_object_or_404(KYCMedia, kyc_media_id=kyc_media_id)

        if status == "REJECTED":
            rejected_status = KYCStatusLookup.objects.get(kyc_status="REJECTED")
            media.kyc_status = rejected_status
            media.rejected_reason = rejected_reason
            media.verified_at = None
        else:  # APPROVED / VERIFIED
            approved_status = KYCStatusLookup.objects.get(kyc_status="APPROVED")
            media.kyc_status = approved_status
            media.rejected_reason = None
            media.verified_at = timezone.now()

        media.save()

        # Check if all media approved → mark KYCDetails as verified
        kyc_detail = media.kyc
        total_docs = kyc_detail.kycmedia_set.count()
        approved_docs = kyc_detail.kycmedia_set.filter(kyc_status__kyc_status="APPROVED").count()

        if approved_docs==2:
            kyc_detail.kyc_status = approved_status
            kyc_detail.verified_at = timezone.now()
            kyc_detail.save()
            global_status = "ACTIVE"
            message = "All documents approved. Tenant KYC now VERIFIED."
        else:
            global_status = "PENDING"
            message = "Document approved. More documents pending."
        
        return Response({
            "message": message,
            "kyc_status": media.kyc_status.kyc_status,
            "global_status": global_status,
            "rejected_reason": media.rejected_reason
        }, status=200)