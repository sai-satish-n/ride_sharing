import uuid
from django.db import models
from drivers.models import Driver, Vehicle
from authentication.models import User, Tenant, TenantUser

class Country(models.Model):
    country_code = models.CharField(max_length=2, primary_key=True)
    country_name = models.CharField(max_length=100)
    currency_code = models.CharField(max_length=3)
    currency_symbol = models.CharField(max_length=10)
    minor_unit = models.CharField(max_length=10)
    default_timezone = models.CharField(max_length=50)
    tax_model = models.CharField(max_length=50)
    default_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    country_code_phone = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "country"
        managed = False

    def __str__(self):
        return self.country_name


class State(models.Model):
    state_code = models.UUIDField(primary_key=True, default=uuid.uuid4)
    country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, db_column="country_code")
    state_name = models.CharField(max_length=100)
    state_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    additional_fees = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "states"
        managed = False

    def __str__(self):
        return self.state_name


class RegionTypeLookup(models.Model):
    region_type_id = models.SmallAutoField(primary_key=True)
    region_type = models.CharField(max_length=20)

    class Meta:
        db_table = "region_type_lookup"
        managed = False

    def __str__(self):
        return self.region_type



class Region(models.Model):
    region_code = models.UUIDField(primary_key=True, default=uuid.uuid4)
    country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, db_column="country_code")
    state = models.ForeignKey(State, on_delete=models.DO_NOTHING, db_column="state_code", null=True, blank=True)
    region_name = models.CharField(max_length=100)
    region_type = models.ForeignKey(RegionTypeLookup, on_delete=models.DO_NOTHING, db_column="region_type_id", null=True, blank=True)
    geo_boundary = models.JSONField(null=True, blank=True)
    is_surge_enabled = models.BooleanField(default=True)
    is_service_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "regions"
        managed = False
        unique_together = ("country", "region_code")

    def __str__(self):
        return self.region_name


class TenantRegion(models.Model):
    tenant_region_id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.DO_NOTHING, db_column="tenant_id")
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column="region_code")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tenant_regions"
        managed = False

    def __str__(self):
        return f"{self.tenant} - {self.region}"


class RideStatusLookup(models.Model):
    ride_status_id = models.SmallAutoField(primary_key=True)
    ride_status = models.CharField(max_length=20)

    class Meta:
        db_table = "ride_status_lookup"
        managed = False

    def __str__(self):
        return self.ride_status


class Ride(models.Model):
    ride_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    driver = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, db_column="driver_id", null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.DO_NOTHING, db_column="vehicle_id", null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column="region_code")
    currency_code = models.CharField(max_length=3)
    timezone = models.CharField(max_length=50)
    ride_eta_seconds = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rides"
        managed = False

    def __str__(self):
        return str(self.ride_id)


class RideDetailsForRiders(models.Model):
    ride_detail_id = models.BigAutoField(primary_key=True)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    rider = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="rider_id")
    otp = models.IntegerField()
    from_location = models.CharField(max_length=20, null=True, blank=True)
    to_location = models.CharField(max_length=20, null=True, blank=True)
    ride_fare = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    ride_status = models.ForeignKey(RideStatusLookup, on_delete=models.DO_NOTHING, null=True, blank=True, db_column="ride_status")
    verification_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ride_details_for_riders"
        managed = False

    def __str__(self):
        return f"{self.ride} - {self.rider}"


class RideLocationLog(models.Model):
    log_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    driver = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, db_column="driver_id")
    latitude = models.TextField(null=True, blank=True)
    longitude = models.TextField(null=True, blank=True)
    heading_towards = models.TextField(null=True, blank=True)
    h3_index = models.CharField(max_length=20)
    speed = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ride_location_log"
        managed = False

    def __str__(self):
        return str(self.log_id)


class EventLog(models.Model):
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    ride_status = models.ForeignKey(RideStatusLookup, on_delete=models.DO_NOTHING, null=True, blank=True, db_column="ride_status_id")
    latitude = models.TextField(null=True, blank=True)
    longitude = models.TextField(null=True, blank=True)
    event_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_log"
        managed = False

    def __str__(self):
        return str(self.event_id)


class RidesDispatch(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.DO_NOTHING, primary_key=True, db_column="ride_id")
    dispatched_by = models.ForeignKey(TenantUser, on_delete=models.DO_NOTHING, db_column="dispatched_by")
    dispatching_reason = models.TextField(null=True, blank=True)
    dispatched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rides_dispatch"
        managed = False

    def __str__(self):
        return str(self.ride)


class RidesFeedback(models.Model):
    feedback_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    from_user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="feedback_from", db_column="from_user_id")
    to_user = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, related_name="feedback_to", db_column="to_user_id")
    tenant = models.ForeignKey(Tenant, on_delete=models.DO_NOTHING, db_column="tenant_id", blank=True, null=True)
    rating = models.IntegerField(null=True, blank=True)
    feedback_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rides_feedbacks"
        managed = False
        unique_together = ("ride", "from_user")

    def __str__(self):
        return f"Feedback {self.feedback_id}"


class RideCancellationLog(models.Model):
    cancellation_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    cancelled_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.DO_NOTHING)
    cancelled_by_driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.DO_NOTHING)
    reason = models.TextField(null=True, blank=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ride_cancellation_log"
        managed = True

    def __str__(self):
        return f"RideCancellationLog {self.ride}"
    

class DriverRideRejection(models.Model):
    rejection_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    driver = models.ForeignKey(Driver, on_delete=models.DO_NOTHING)
    rejected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "driver_ride_rejections"
        managed = True

    