import uuid
from django.db import models
from authentication.models import User, Tenant
from drivers.models import Driver, VehicleType
from rides.models import Ride, Region
from django.utils import timezone


class PricingConfig(models.Model):
    pricing_config_id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.DO_NOTHING, db_column="tenant_id")
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column="region_code")
    base_fare = models.DecimalField(max_digits=10, decimal_places=4)
    rate_per_km = models.DecimalField(max_digits=10, decimal_places=4)
    rate_per_min = models.DecimalField(max_digits=10, decimal_places=4)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.DO_NOTHING, db_column="vehicle_type", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pricing_config"
        managed = False


class SurgePricing(models.Model):
    surge_pricing_id = models.BigAutoField(primary_key=True)
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column="region_code")
    surge_multiplier = models.DecimalField(max_digits=10, decimal_places=4)
    effective_from = models.DateTimeField()
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "surge_pricing"
        managed = False


class SurgePricingLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    surge_pricing = models.ForeignKey(
        'SurgePricing',
        on_delete=models.DO_NOTHING,
        db_column='surge_pricing_id',
        related_name='logs'
    )
    
    old_multiplier = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    new_multiplier = models.DecimalField(max_digits=10, decimal_places=4)
    effective_from = models.DateTimeField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "surge_pricing_log"
        ordering = ['-created_at']

    def __str__(self):
        return f"SurgeLog[{self.log_id}] Region: {self.region_code} {self.old_multiplier} → {self.new_multiplier}"

class CurrencyConversion(models.Model):
    currency_code = models.ForeignKey(
        'rides.Country',
        on_delete=models.DO_NOTHING,
        db_column="currency_code",
        primary_key=True
    )
    conversion_rate_to_usd = models.DecimalField(max_digits=18, decimal_places=6)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "currency_conversion"
        verbose_name = "Currency Conversion"
        verbose_name_plural = "Currency Conversions"

    def __str__(self):
        return f"{self.currency_code} ({self.conversion_rate_to_usd} USD)"

class RideFareSnapshot(models.Model):
    ride_fare_snapshot_id = models.BigAutoField(primary_key=True)
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    rider = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="rider_id")
    base_fare = models.DecimalField(max_digits=10, decimal_places=4)
    distance_fare = models.DecimalField(max_digits=10, decimal_places=4)
    time_fare = models.DecimalField(max_digits=10, decimal_places=4)
    surge_multiplier = models.DecimalField(max_digits=10, decimal_places=4)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=4)
    final_fare = models.DecimalField(max_digits=10, decimal_places=4)
    currency = models.CharField(max_length=3, null=True, blank=True)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ride_fare_snapshot"
        managed = False


class PaymentStatusLookup(models.Model):
    status_id = models.SmallAutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "payment_status_lookup"
        managed = False

    def __str__(self):
        return self.status_name


class Payment(models.Model):
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant = models.ForeignKey(Tenant, on_delete=models.DO_NOTHING, db_column="tenant_id", null=True, blank=True)
    rider = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="rider_id", null=True, blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, db_column="driver_id")
    ride = models.ForeignKey(Ride, on_delete=models.DO_NOTHING, db_column="ride_id")
    amount_total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    payment_method = models.CharField(max_length=50, null=True, blank=True)  # cash, wallet, upi, etc
    payment_status = models.ForeignKey(PaymentStatusLookup, on_delete=models.DO_NOTHING, db_column="payment_status_id", null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "payments"
        managed = False
        unique_together = ("ride", "rider")


class PaymentGatewayEvent(models.Model):
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    payment = models.ForeignKey(Payment, on_delete=models.DO_NOTHING, db_column="payment_id")
    gateway_event = models.JSONField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_gateway_events"
        managed = False


class Settlement(models.Model):
    settlement_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    payment = models.ForeignKey(Payment, on_delete=models.DO_NOTHING, db_column="payment_id")
    tenant = models.ForeignKey(Tenant, on_delete=models.DO_NOTHING, db_column="tenant_id", null=True, blank=True)
    entity = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, db_column="entity_id", null=True, blank=True)
    settlement_type = models.CharField(max_length=20)  # driver | provider | partner
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    payment_status = models.ForeignKey(PaymentStatusLookup, on_delete=models.DO_NOTHING, db_column="payment_status_id", null=True, blank=True)
    payout_method = models.CharField(max_length=50, null=True, blank=True)
    payout_reference = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    setteled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "settlements"
        managed = False


class Wallet(models.Model):
    wallet_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_column="user_id")
    currency_code = models.CharField(max_length=3, null=True, blank=True)
    amount = models.DecimalField(max_digits=11, decimal_places=3, default=0.0)

    class Meta:
        db_table = "wallets"
        managed = False

    def __str__(self):
        return f"{self.user} - {self.currency_code}: {self.amount}"


class WalletTransaction(models.Model):
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    wallet = models.ForeignKey(Wallet, on_delete=models.DO_NOTHING, db_column="wallet_id")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=30, null=True, blank=True)  # credit, debit, refund etc
    reference_id = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wallet_transactions"
        managed = False

    def __str__(self):
        return f"{self.wallet.user} - {self.transaction_type} - {self.amount}"