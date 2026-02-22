from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from authentication.models import TenantUser
from issues.models import Complaint, LostItemTicket, TicketStatusLookup, ComplaintCategory
from issues.serializers import ComplaintSerializer, LostItemTicketSerializer, ComplaintListSerializer, ComplaintUpdateSerializer, LostItemTicketUpdateSerializer
from django.db.models import Q
from drivers.models import DriverFleetAssignment
from django.utils import timezone


# API to get complaint categories
class ComplaintCategoriesAPIView(APIView):
    def get(self, request, *args, **kwargs):
        categories = ComplaintCategory.objects.all()
        # Serialize the categories into JSON
        
        data = []
        # [category.category for category in categories]
        for category in categories:
            data.append({"id":category.category_id, "name": category.category})
        return Response(data)

# API to raise a complaint
class RaiseComplaintAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ComplaintSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            complaint = serializer.save()
            return Response({
                'message': 'Complaint raised successfully.',
                'complaint_id': complaint.complaint_id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# API to report a lost item
class ReportLostItemAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LostItemTicketSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save(ticket_status_id=1)  # Open status for lost item
            return Response({'message': 'Lost item ticket raised successfully.', 'ticket_id': ticket.ticket_id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ListUserIssuesComplaints(APIView):
    def get(self, request, user_id):
        # 🔹 Lost item tickets where user is involved
        lost_item_tickets = LostItemTicket.objects.filter(
            Q(raised_by_id=user_id) |
            Q(concerned_user_id=user_id)
        ).order_by('-created_at')

        # 🔹 Complaints raised by user
        complaints = Complaint.objects.filter(
            user_id=user_id
        ).order_by('-created_at')

        lost_item_serializer = LostItemTicketSerializer(
            lost_item_tickets,
            many=True
        )

        complaint_serializer = ComplaintListSerializer(
            complaints,
            many=True
        )

        return Response(
            {
                "missing_issues": lost_item_serializer.data,
                "complaints": complaint_serializer.data
            },
            status=status.HTTP_200_OK
        )


def get_issues_complaints(
    lost_item_filter: Q,
    complaint_filter: Q,
):
    lost_items = LostItemTicket.objects.filter(lost_item_filter).order_by('-created_at')
    complaints = Complaint.objects.filter(complaint_filter).order_by('-created_at')

    return {
        "missing_issues": LostItemTicketSerializer(lost_items, many=True).data,
        "complaints": ComplaintListSerializer(complaints, many=True).data,
    }


class ListDriverIssuesComplaints(APIView):
    def get(self, request, user_id):
        lost_item_filter = Q(concerned_driver_id__user_id=user_id)
        complaint_filter = Q(ride__driver__user_id=user_id)

        response_data = get_issues_complaints(lost_item_filter, complaint_filter)
        return Response(response_data, status=200)


class ListAdminIssuesComplaints(APIView):
    def get(self, request, user_id):
        lost_item_filter = Q()  # everything
        complaint_filter = Q()   # everything

        response_data = get_issues_complaints(lost_item_filter, complaint_filter)
        return Response(response_data, status=200)


class ListFleetAdminIssuesComplaints(APIView):
    def get(self, request, user_id):
        # 🔹 Get all drivers in fleets belonging to this tenant
        tenant = TenantUser.objects.filter(user_id = user_id).first()
        driver_ids = DriverFleetAssignment.objects.filter(
            tenant_id=tenant.tenant_id
        ).values_list('driver_id', flat=True)

        lost_item_filter = Q(concerned_driver_id__in=driver_ids)
        complaint_filter = Q(ride__driver__driver_id__in=driver_ids)

        response_data = get_issues_complaints(lost_item_filter, complaint_filter)
        return Response(response_data, status=200)


class UpdateComplaintAPIView(APIView):
    def post(self, request, complaint_id):
        try:
            complaint = Complaint.objects.get(complaint_id=complaint_id)
        except Complaint.DoesNotExist:
            return Response(
                {'error': 'Complaint not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ComplaintUpdateSerializer(
            complaint,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Complaint updated successfully.'},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateLostItemTicketAPIView(APIView):
    def post(self, request, ticket_id):
        try:
            ticket = LostItemTicket.objects.get(ticket_id=ticket_id)
        except LostItemTicket.DoesNotExist:
            return Response(
                {'error': 'Lost item ticket not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = LostItemTicketUpdateSerializer(
            ticket,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            ticket = serializer.save()

            # 🔹 Auto-close logic (optional but recommended)
            if (
                'ticket_status' in request.data
                and ticket.ticket_status
                and ticket.ticket_status.ticket_status == 'CLOSED'
                and not ticket.closed_at
            ):
                ticket.closed_at = timezone.now()
                ticket.save(update_fields=['closed_at'])

            return Response(
                {'message': 'Lost item ticket updated successfully.'},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)