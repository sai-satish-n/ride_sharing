from django.db import models
import uuid
from authentication.models import User, Tenant
from drivers.models import Driver

class KYCTypeLookup(models.Model):
    kyc_type_id = models.SmallAutoField(primary_key=True)
    kyc_type = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "kyc_type_lookup"
        managed = False

    def __str__(self):
        return self.kyc_type


class KYCStatusLookup(models.Model):
    kyc_status_id = models.SmallAutoField(primary_key=True)
    kyc_status = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "kyc_status_lookup"
        managed = False

    def __str__(self):
        return self.kyc_status


class KYCDetails(models.Model):
    kyc_id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        db_column="user_id",
        null=True,
        blank=True
    )

    driver = models.ForeignKey(
        Driver,
        on_delete=models.DO_NOTHING,
        db_column="driver_id",
        null=True,
        blank=True
    )

    tenant_id = models.ForeignKey(
        Tenant,
        on_delete=models.DO_NOTHING,
        db_column="tenant_id",
        null=True,
        blank=True
    )

    kyc_type = models.ForeignKey(
        KYCTypeLookup,
        on_delete=models.DO_NOTHING,
        db_column="kyc_type_id"
    )

    kyc_status = models.ForeignKey(
        KYCStatusLookup,
        on_delete=models.DO_NOTHING,
        db_column="kyc_status_id"
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "kyc_details"
        managed = False

    def __str__(self):
        return f"KYC {self.kyc_id}"


class KYCMedia(models.Model):
    kyc_media_id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    kyc = models.ForeignKey(
        KYCDetails,
        on_delete=models.DO_NOTHING,
        db_column="kyc_id"
    )

    media_url = models.TextField()
    media_type = models.CharField(max_length=50)  # IMAGE, PDF, VIDEO, etc.
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kyc_media"
        managed = False

    def __str__(self):
        return f"Media {self.kyc_media_id} for KYC {self.kyc.kyc_id}"