from django.urls import path
from issues.views import * 

urlpatterns = [
    path('complaints/categories/', ComplaintCategoriesAPIView.as_view(), name='complaint-categories'),
    path('complaints/create/', RaiseComplaintAPIView.as_view(), name='raise-complaint'),    
    path('lost-items/create/', ReportLostItemAPIView.as_view(), name='report-lost-item'),
    path('list/<uuid:user_id>/', ListUserIssuesComplaints.as_view(), name='user_issues'),
    path('list/driver/<uuid:user_id>/', ListDriverIssuesComplaints.as_view(), name='driver_issues'),
    path('list/admin/<uuid:user_id>/', ListAdminIssuesComplaints.as_view(), name='admin_issues'),
    path('list/fleet_admin/<uuid:user_id>/', ListFleetAdminIssuesComplaints.as_view(), name='fleet_admin_issues'),
    path('complaints/<uuid:complaint_id>', UpdateComplaintAPIView.as_view(), name='update_complaint'),
    path('lost_item/<uuid:ticket_id>', UpdateLostItemTicketAPIView.as_view(), name='update_lost_item'),
]
