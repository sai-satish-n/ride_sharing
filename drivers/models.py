import uuid
from django.db import models

# Create your models here.
class DriverStatusLookup(models.Model):
    driver_status_id = models.SmallAutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "driver_status_lookup"
        managed = False

    def __str__(self):
        return self.status_name
    
class Driver(models.Model):
    driver_id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.DO_NOTHING,
        db_column="user_id"
    )

    driving_licence_number = models.CharField(max_length=50)
    driver_rating = models.DecimalField(max_digits=6, decimal_places=4, null=True)

    driver_online_status = models.ForeignKey(
        DriverStatusLookup,
        on_delete=models.DO_NOTHING,
        db_column="driver_online_status",
        null=True
    )

    current_h3_index = models.BigIntegerField(null=True)
    last_location = models.TextField(null=True)
    location_updated_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "drivers"
        managed = False

    def __str__(self):
        return f"Driver {self.driver_id}"
    

class DriverFleetAssignment(models.Model):
    driver_fleet_assign_id = models.UUIDField(primary_key=True,default=uuid.uuid4)
    driver = models.ForeignKey(
        Driver,
        on_delete=models.DO_NOTHING,
        db_column="driver_id"
    )

    tenant_id = models.ForeignKey(
        "authentication.Tenant",
        on_delete=models.DO_NOTHING,
        db_column="tenant_id"
    )
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    class Meta:
        db_table = "driver_fleet_assignments"
        managed = False

class VehicleType(models.Model):
    vehicle_type_id = models.SmallAutoField(primary_key=True)
    vehicle_name = models.CharField(max_length=50)
    vehicle_capacity = models.IntegerField(null=True)
    vehicle_category = models.CharField(max_length=50)

    class Meta:
        db_table = "vehicle_types"
        managed = False

    def __str__(self):
        return self.vehicle_name

class Vehicle(models.Model):
    vehicle_id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    fleet_tenant_id = models.ForeignKey(
        "authentication.Tenant", 
        on_delete=models.DO_NOTHING, 
        db_column="fleet_tenant_id"
    )

    vehicle_number = models.CharField(max_length=20)

    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.DO_NOTHING,
        db_column="vehicle_type"
    )

    vehicle_conditon = models.TextField(null=True)

    class Meta:
        db_table = "vehicles"
        managed = False

    def __str__(self):
        return self.vehicle_number

class VehicleDriverAssignment(models.Model):
    vehicle_driver_assign_id = models.BigAutoField(primary_key=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.DO_NOTHING,
        db_column="vehicle_id"
    )

    driver = models.ForeignKey(
        Driver,
        on_delete=models.DO_NOTHING,
        db_column="driver_id"
    )

    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    class Meta:
        db_table = "vehicle_driver_assignments"
        managed = False
    