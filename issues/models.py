import uuid
from django.db import models
from authentication.models import User, Tenant, TenantUser
from drivers.models import Driver
from rides.models import Ride, Region


class SOSContactType(models.Model):
    sos_contact_id = models.SmallAutoField(primary_key=True)
    sos_contact_type = models.TextField()

    class Meta:
        db_table = "sos_contact_types"
        managed = False

    def __str__(self):
        return self.sos_contact_type


class SOSSupportDetail(models.Model):
    sos_support_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    region = models.ForeignKey(
        Region, on_delete=models.DO_NOTHING, db_column="region_code", null=True, blank=True
    )
    sos_contact_name = models.CharField(max_length=50, null=True, blank=True)
    sos_contact_mobile = models.CharField(max_length=20, null=True, blank=True)
    sos_contact_type = models.ForeignKey(
        SOSContactType, on_delete=models.DO_NOTHING, db_column="sos_contact_type", null=True, blank=True
    )
    sos_contact_designation = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        db_table = "sos_support_details"
        managed = False

    def __str__(self):
        return self.sos_contact_name


class SOSAlertStatusLookup(models.Model):
    sos_alert_status_id = models.SmallAutoField(primary_key=True)
    sos_alert_status = models.TextField()  # SENT, ACKNOWLEDGED, RESOLVED

    class Meta:
        db_table = "sos_alert_status_lookup"
        managed = False

    def __str__(self):
        return self.sos_alert_status


class SOSAlert(models.Model):
    sos_alert_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="user_id", null=True, blank=True)
    latitude = models.TextField(null=True, blank=True)
    longitude = models.TextField(null=True, blank=True)
    status = models.ForeignKey(SOSAlertStatusLookup, on_delete=models.DO_NOTHING, db_column="status", null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.DO_NOTHING, db_column="tenant_id", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sos_alerts"
        managed = False

    def __str__(self):
        return str(self.sos_alert_id)


class NotificationStatusLookup(models.Model):
    notification_status_id = models.SmallAutoField(primary_key=True)
    notification_status = models.CharField(max_length=50)  # NOTIFIED, NOTIFICATION-PENDING

    class Meta:
        db_table = "notification_status_lookup"
        managed = False

    def __str__(self):
        return self.notification_status


class SOSUserNotification(models.Model):
    sos_alert = models.ForeignKey(SOSAlert, on_delete=models.DO_NOTHING, db_column="sos_alert_id")
    sos_contact_number = models.CharField(max_length=15)
    notification_status = models.ForeignKey(NotificationStatusLookup, on_delete=models.DO_NOTHING, db_column="notification_status", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sos_user_notifications"
        managed = False
        unique_together = ("sos_alert", "sos_contact_number")


class TicketStatusLookup(models.Model):
    ticket_status_id = models.SmallAutoField(primary_key=True)
    ticket_status = models.TextField()  # OPEN, PENDING, RESOLVED, ESCALATED

    class Meta:
        db_table = "ticket_status_lookup"
        managed = False

    def __str__(self):
        return self.ticket_status


class LostItemTicket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id", null=True, blank=True)
    ticket_status = models.ForeignKey(TicketStatusLookup, on_delete=models.DO_NOTHING, db_column="ticket_status", null=True, blank=True)
    raised_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="raised_by", related_name="lost_item_raised_by")
    concerned_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="concerned_user_id", related_name="lost_item_concerned_user")
    concerned_driver = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, db_column="concerned_driver_id", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lost_item_tickets"
        managed = False

    def __str__(self):
        return str(self.ticket_id)


class LostItemMedia(models.Model):
    lost_item_media_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ticket = models.ForeignKey(LostItemTicket, on_delete=models.DO_NOTHING, db_column="ticket_id")
    media_url = models.TextField()
    media_type = models.TextField()
    uploaded_by_role = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lost_item_media"
        managed = False


class LostItemNotification(models.Model):
    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    recipient = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="recipient_id")
    ticket = models.ForeignKey(LostItemTicket, on_delete=models.DO_NOTHING, db_column="ticket_id")
    ticket_status = models.ForeignKey(TicketStatusLookup, on_delete=models.DO_NOTHING, db_column="ticket_status", null=True, blank=True)
    notification_status = models.ForeignKey(NotificationStatusLookup, on_delete=models.DO_NOTHING, db_column="notification_status", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lost_item_notifications"
        managed = False


class PriorityLookup(models.Model):
    priority_id = models.SmallAutoField(primary_key=True)
    priority = models.CharField(max_length=20)  # CRITICAL, HIGH, MEDIUM, LOW

    class Meta:
        db_table = "priority_lookup"
        managed = False


class ComplaintCategory(models.Model):
    category_id = models.SmallAutoField(primary_key=True)
    category = models.CharField(max_length=30)  # SAFETY, BILLING, OTHER

    class Meta:
        db_table = "complaint_categories"
        managed = False


class SLAIssueType(models.Model):
    sla_issue_type_id = models.SmallAutoField(primary_key=True)
    sla_issue_type = models.TextField()  # SOS, COMPLAINT, LOST_ITEM

    class Meta:
        db_table = "sla_issue_types"
        managed = False


class SLAPolicy(models.Model):
    policy_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant = models.ForeignKey(Tenant, on_delete=models.DO_NOTHING, db_column="tenant_id")
    sla_issue_type = models.ForeignKey(SLAIssueType, on_delete=models.DO_NOTHING, db_column="sla_issue_type_id")
    priority = models.ForeignKey(PriorityLookup, on_delete=models.DO_NOTHING, db_column="priority_id")
    response_time_minutes = models.IntegerField()
    resolution_time_minutes = models.IntegerField()

    class Meta:
        db_table = "sla_policy"
        managed = False


class Complaint(models.Model):
    complaint_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="user_id")
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(ComplaintCategory, on_delete=models.DO_NOTHING, db_column="category")
    sla_policy = models.ForeignKey(SLAPolicy, on_delete=models.DO_NOTHING, db_column="sla_policy_id")
    complaint_status = models.ForeignKey(TicketStatusLookup, on_delete=models.DO_NOTHING, db_column="complaint_status_id", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints"
        managed = False


class ComplaintAssign(models.Model):
    complaint_assign_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    complaint = models.ForeignKey(Complaint, on_delete=models.DO_NOTHING, db_column="complaint_id")
    assigned_by = models.ForeignKey(TenantUser, on_delete=models.DO_NOTHING, db_column="assigned_by", related_name="assigned_by_user")
    assigned_to = models.ForeignKey(TenantUser, on_delete=models.DO_NOTHING, db_column="assigned_to", related_name="assigned_to_user")
    assigned_at = models.DateTimeField(auto_now_add=True)
    complaint_status = models.ForeignKey(TicketStatusLookup, on_delete=models.DO_NOTHING, db_column="complaint_status_id", null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaint_assign"
        managed = False


class ComplaintSLA(models.Model):
    sla_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    complaint = models.ForeignKey(Complaint, on_delete=models.DO_NOTHING, db_column="complaint_id")
    target_resolution_time = models.DateTimeField(null=True, blank=True)
    actual_resolved_time = models.DateTimeField(null=True, blank=True)
    response_deadline = models.DateTimeField(null=True, blank=True)
    sla_status = models.ForeignKey(TicketStatusLookup, on_delete=models.DO_NOTHING, db_column="sla_status_id", null=True, blank=True)

    class Meta:
        db_table = "complaints_sla"
        managed = False

