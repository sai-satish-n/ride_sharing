from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from decimal import Decimal

from authentication.models import User, Tenant, TenantUser
from drivers.models import DriverFleetAssignment
from payments_module.models import (
    Payment,
    PaymentStatusLookup,
    RideFareSnapshot,
    Wallet,
    WalletTransaction,
    PricingConfig,
    SurgePricing,
    CurrencyConversion,
)
from payments_module.serializers import *
from rides.models import Ride, RideDetailsForRiders, RideStatusLookup, Country

from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Count, F
from dotenv import load_dotenv
from os import getenv
from utils.ride_utils import haversine_distance

load_dotenv()
WAIT_TIME_THRESHOLD = getenv("WAIT_TIME_THRESHOLD", 3)
TAX_PERCENTAGE = Decimal(getenv("TAX_PERCENTAGE", "0.05"))
APP_COMMISSION_PERCENTAGE = Decimal(getenv("APP_COMMISSION_PERCENTAGE", "0.20"))
APP_COMMISSION_FROM_TENANT_PERCENTAGE = Decimal(
    getenv("APP_COMMISSION_FROM_TENANT_PERCENTAGE", "0.75")
)
APP_COMMISSION_FROM_DRIVER_PERCENTAGE = Decimal(
    getenv("APP_COMMISSION_FROM_DRIVER_PERCENTAGE", "0.25")
)
TENANT_PERCENTAGE = Decimal(getenv("TENANT_PERCENTAGE", "0.25"))
DRIVER_PERCENTAGE = Decimal(getenv("DRIVER_PERCENTAGE", "0.75"))


def calculate_ride_fare(
    driver_id, ride_detail: RideDetailsForRiders, tenant: Tenant = None
):
    """
    Calculate fare based on ride details, pricing config, surge, distance, and wait time.
    """

    lat, lng = map(float, ride_detail.from_location.split(", "))
    drop_lat, drop_lng = map(float, ride_detail.to_location.split(","))
    distance_km = haversine_distance(lat, lng, drop_lat, drop_lng)
    wait_minutes = 0

    # Wait time is time between driver_reached_at and ride_started_at
    if ride_detail.driver_reached_at and ride_detail.ride_started_at:
        wait_duration = ride_detail.ride_started_at - ride_detail.driver_reached_at
        wait_minutes = max(0, wait_duration.total_seconds() / 60 - WAIT_TIME_THRESHOLD)

    # Get pricing config
    pricing_config = (
        PricingConfig.objects.filter(
            tenant=tenant,
            region=ride_detail.ride.region,
            vehicle_type=ride_detail.vehicle_type,
        )
        .order_by("-updated_at")
        .first()
    )

    if not pricing_config:
        pricing_config = (
            PricingConfig.objects.filter(
                region=ride_detail.ride.region,
                vehicle_type=ride_detail.vehicle_type,
            )
            .order_by("-updated_at")
            .first()
        )

    if not pricing_config:

        raise ValueError("Pricing config not found")

    base_fare = ride_detail.ride_fare
    distance_fare = Decimal(distance_km) * pricing_config.rate_per_km
    time_fare = Decimal(wait_minutes) * pricing_config.rate_per_min

    # Check for active surge pricing
    now = timezone.now()
    surge = (
        SurgePricing.objects.filter(
            region=ride_detail.ride.region, effective_from__lte=now, expires_at__gte=now
        )
        .order_by("-effective_from")
        .first()
    )

    surge_multiplier = surge.surge_multiplier if surge else Decimal("1.0")

    # subtotal = base_fare + time_fare
    # tax_amount = subtotal * TAX_PERCENTAGE
    final_fare_without_tax = base_fare + time_fare
    tax_amount = final_fare_without_tax * TAX_PERCENTAGE
    final_fare = final_fare_without_tax + tax_amount

    user = User.objects.get(user_id=driver_id)
    currency_code = Country.objects.get(
        country_code_phone=user.phone_country_code
    ).currency_code

    # Insert fare snapshot
    snapshot = RideFareSnapshot.objects.create(
        ride=ride_detail.ride,
        rider=ride_detail.rider,
        base_fare=base_fare,
        distance_fare=distance_fare,
        time_fare=time_fare,
        surge_multiplier=surge_multiplier,
        tax_amount=tax_amount,
        final_fare=final_fare,
        currency=currency_code,
    )

    return final_fare, snapshot


class PaymentStatusView(APIView):
    def get(self, request, payment_id):
        payment = Payment.objects.get(payment_id=payment_id)
        return Response(PaymentStatusSerializer(payment).data)


class PaymentFetchView(APIView):
    def post(self, request):
        serializer = PaymentFetchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        filters = serializer.validated_data
        payments = Payment.objects.filter(**filters)

        return Response(PaymentStatusSerializer(payments, many=True).data)


class PaymentGatewayEventCreateView(APIView):
    def post(self, request):
        serializer = PaymentGatewayEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(received_at=now())
        return Response({"created": True})


#endpoints related to pricing

class PricingConfigView(APIView):
    def get(self, request, region_id):
        config = PricingConfig.objects.get(region_id=region_id)
        return Response(PricingConfigSerializer(config).data)


class PricingConfigCreateView(APIView):
    def post(self, request):
        serializer = PricingConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class SurgePricingView(APIView):
    def get(self, request, region_id):
        surge = SurgePricing.objects.filter(region_id=region_id).last()
        return Response(SurgePricingSerializer(surge).data)


class SurgePricingCreateView(APIView):
    def post(self, request):
        serializer = SurgePricingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CreateWalletView(APIView):
    def post(self, request):
        user = User.objects.get(user_id=request.data["user_id"])
        currency_code = request.data.get("currency_code") or "INR"

        wallet = Wallet.objects.create(user=user, currency_code=currency_code, amount=0)
        wallet.save()

        return Response({"user_id": user.user_id, "wallet_id": wallet.wallet_id})


class WalletAddView(APIView):
    def post(self, request):
        

        serializer = WalletFetchSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(**serializer.validated_data)

        wallet.amount += Decimal(request.data["amount"])
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=request.data["amount"],
            transaction_type="credit"
        )
        return Response({"balance": wallet.amount})

class WalletBalanceView(APIView):
    def get(self, request, user_id):

        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=400
            )

        wallet_results = Wallet.objects.filter(user_id=user_id).values()

        return Response({"wallets_data": list(wallet_results)})


class WalletTransactionFetchView(APIView):
    def post(self, request):
        serializer = WalletTransactionFetchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qs = WalletTransaction.objects.filter(
            wallet_id=serializer.validated_data["wallet_id"]
        )
        if "start_date" in serializer.validated_data:
            qs = qs.filter(created_at__gte=serializer.validated_data["start_date"])
        if "end_date" in serializer.validated_data:
            qs = qs.filter(created_at__lte=serializer.validated_data["end_date"])

        return Response(qs.values())


def currency_conversion(rider_id, ride_fare_snapshot: RideFareSnapshot):
    user = User.objects.get(user_id=rider_id)
    to_currency_code = Country.objects.get(
        country_code_phone=user.phone_country_code
    ).currency_code
    from_currency_code = ride_fare_snapshot.currency

    if from_currency_code == to_currency_code:
        return lambda amount: amount

    currencies = CurrencyConversion.objects.filter(
        currency_code__in=[from_currency_code, to_currency_code]
    )

    conversion_map = {c.currency_code_id: c.conversion_rate_to_usd for c in currencies}

    from_conversion_rate = conversion_map.get(from_currency_code)
    to_conversion_rate = conversion_map.get(to_currency_code)

    def convert(amount):
        return (amount * from_conversion_rate) / to_conversion_rate

    return convert, from_currency_code, to_currency_code


class ProceedToPaymentView(APIView):
    def get(self, request):

        ride_id = request.query_params.get("ride_id")
        rider_id = request.query_params.get("rider_id")

        try:
            ride_details_for_rider = RideDetailsForRiders.objects.get(
                ride_id=ride_id, rider_id=rider_id
            )

            ride_fare_snapshot = RideFareSnapshot.objects.filter(
                ride=ride_details_for_rider.ride,
                rider_id=ride_details_for_rider.rider_id,
            ).last()
            payment = Payment.objects.filter(
                ride=ride_details_for_rider.ride, rider=ride_details_for_rider.rider
            ).last()

           
            convert, from_currency_code, to_currency_code = currency_conversion(
                rider_id=rider_id, ride_fare_snapshot=ride_fare_snapshot
            )

            fare_breakup = {
                "payment_id": payment.payment_id if payment else None,
                "base_fare": convert(ride_fare_snapshot.base_fare),
                "distance_fare": convert(ride_fare_snapshot.distance_fare),
                "time_fare": convert(ride_fare_snapshot.time_fare),
                "surge_multiplier": ride_fare_snapshot.surge_multiplier,
                "tax_amount": convert(ride_fare_snapshot.tax_amount),
                "final_fare": convert(ride_fare_snapshot.final_fare),
                "currency": to_currency_code,
            }

            return Response(fare_breakup)
        except Ride.DoesNotExist:
            return Response({"error": "Ride not found"}, status=404)

    def post(self, request):
        ride_id = request.data.get("ride_id")
        rider_id = request.data.get("rider_id")
        user_id = request.data.get("user_id")

        if not ride_id:
            return Response(
                {"error": "ride_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        """
        Calculate fare and create payment with pending status.
        """
        try:
            ride_detail = RideDetailsForRiders.objects.get(
                ride_id=ride_id, rider_id=rider_id
            )
            RideDetailsForRiders.objects.filter(ride_id=ride_id).update(
                ride_ended_at=timezone.now(),
                ride_status=RideStatusLookup.objects.get(ride_status="PAYMENT_PENDING"),
            )
        except RideDetailsForRiders.DoesNotExist:
            return Response({"error": "Ride detail not found"}, status=404)

        # Calculate fare
        driver_assignment = DriverFleetAssignment.objects.filter(
            driver__user__user_id=user_id
        )
        tenant = (
            driver_assignment.first().tenant_id if driver_assignment.exists() else None
        )
        driver_id = driver_assignment.first().driver.user.user_id
        final_fare, snapshot = calculate_ride_fare(
            driver_id, ride_detail, tenant=tenant
        )

        # Get pending payment status
        pending_status = PaymentStatusLookup.objects.get(status_name="PENDING")

        convert, from_currency_code, to_currency_code = currency_conversion(
            rider_id=rider_id,
            ride_fare_snapshot=RideFareSnapshot.objects.get(
                ride_id=ride_id, rider_id=rider_id
            ),
        )

        # Create payment
        payment = Payment.objects.create(
            tenant=tenant,
            rider=ride_detail.rider,
            driver=ride_detail.ride.driver,
            ride=ride_detail.ride,
            amount_total=convert(final_fare.quantize(Decimal("0.01"))),
            currency=to_currency_code,
            payment_status=pending_status,
            created_at=timezone.now(),
        )

        return Response(
            {
                "payment_id": payment.payment_id,
                "ride_id": ride_detail.ride.ride_id,
                "final_fare": float(final_fare),
                "payment_status": pending_status.status_name,
                "snapshot_id": snapshot.ride_fare_snapshot_id,
                "from_currency_code": from_currency_code,
            }
        )


class PayWithWalletView(APIView):
    def post(self, request):
        payment_id = request.data.get("payment_id")
        ride_id = request.data.get("ride_id")
        rider_id = request.data.get("rider_id")

        if not payment_id:
            return Response(
                {"error": "payment_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        """
        Pay a pending payment from wallet.
        Handles full payment, partial payment, insufficient funds.
        """
        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        wallet = Wallet.objects.filter(user=payment.rider).last()
        if not wallet:
            return Response({"error": "Wallet not found"}, status=404)

        with transaction.atomic():
            if wallet.amount >= payment.amount_total:
                # Full payment
                statuses = PaymentStatusLookup.objects.filter(
                    status_name__in=["COMPLETED", "PENDING"]
                )

                status_map = {s.status_name: s for s in statuses}

                completed_status = status_map["COMPLETED"]
                pending_status = status_map["PENDING"]

                wallet.amount -= payment.amount_total
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=payment.amount_total,
                    transaction_type="debit",
                    reference_id=str(payment.payment_id),
                )
                payment.payment_status = completed_status

                RideDetailsForRiders.objects.filter(
                    ride_id=ride_id, rider_id=rider_id
                ).update(
                    ride_status=RideStatusLookup.objects.get(ride_status="COMPLETED")
                )
                payment.save()

                gross_amount = payment.amount_total
                currency = payment.currency if hasattr(payment, "currency") else "INR"
                app_total_commission_amount = gross_amount * APP_COMMISSION_PERCENTAGE
                has_tenant = bool(payment.tenant_id)


                if has_tenant:
                    app_commission_from_tenant = (
                        app_total_commission_amount
                        * APP_COMMISSION_FROM_TENANT_PERCENTAGE
                    )
                    app_commission_from_driver = (
                        app_total_commission_amount
                        * APP_COMMISSION_FROM_DRIVER_PERCENTAGE
                    )
                else:
                    app_commission_from_tenant = Decimal("0.00")
                    app_commission_from_driver = app_total_commission_amount


                tenant_gross_amount = (
                    gross_amount * TENANT_PERCENTAGE if has_tenant else Decimal("0.00")
                )
                tenant_tax_amount = tenant_gross_amount * TAX_PERCENTAGE
                tenant_net_amount = (
                    tenant_gross_amount - tenant_tax_amount - app_commission_from_tenant
                )

                driver_gross_amount = (
                    gross_amount * DRIVER_PERCENTAGE if has_tenant else gross_amount
                )
                driver_tax_amount = driver_gross_amount * TAX_PERCENTAGE
                driver_net_amount = (
                    driver_gross_amount - driver_tax_amount - app_commission_from_driver
                )

                # ---- Driver Earnings ----

                if has_tenant:
                    Settlement.objects.create(
                        payment=payment,
                        tenant_id=payment.tenant_id,
                        entity=None,
                        settlement_type="tenant",
                        gross_amount=tenant_gross_amount,
                        commission_amount=app_commission_from_tenant,
                        tax_amount=tenant_tax_amount,
                        net_amount=tenant_net_amount,
                        currency=currency,
                        payment_status=pending_status,
                        payout_method=payment.payment_method,
                    )

                # -------- DRIVER SETTLEMENT --------
                Settlement.objects.create(
                    payment=payment,
                    tenant_id=payment.tenant_id,
                    entity_id=payment.driver_id,
                    settlement_type="driver",
                    gross_amount=driver_gross_amount,
                    commission_amount=app_commission_from_driver,
                    tax_amount=driver_tax_amount,
                    net_amount=driver_net_amount,
                    currency=currency,
                    payment_status=pending_status,
                    payout_method=payment.payment_method,
                )


                return Response(
                    {
                        "message": "Payment completed",
                        "paid_amount": float(payment.amount_total),
                    }
                )

            else:
                return Response({"error": "Insufficient wallet balance"}, status=400)


class ConfirmPasswordView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        password = request.data.get("password")

        user = get_object_or_404(User, user_id=user_id)

        if not check_password(password, user.password_hash):
            return Response({"error": "Incorrect password"}, status=400)

        return Response({"message": "Password confirmed"}, status=200)


class EarningsView(APIView):
    def get(self, request):
        user = User.objects.get(user_id=request.query_params.get("user_id"))
        role = request.query_params.get("role")  # 'driver' or 'fleet_admin'

        if role == "driver":

            settlements_qs = Settlement.objects.filter(
                settlement_type="driver",
                entity__user=user
            ).select_related("payment_status")

            settlements = (
                settlements_qs
                .values(
                    "payment__ride_id",
                    "net_amount",
                    "gross_amount",
                    "commission_amount",
                    "tax_amount",
                    "currency",
                    "payment_status__status_name",
                    "created_at",
                )
                .order_by("-created_at")
            )

            # total_sum = earnings.aggregate(Sum("final_fare"))["final_fare__sum"] or 0
            total_sum = (
                settlements_qs.aggregate(Sum("net_amount"))["net_amount__sum"]
                or 0
            )

            currency = settlements_qs.values_list("currency", flat=True).first()

            return Response(
                {
                    "type": "individual",
                    "total_earnings": total_sum,
                    "history": list(settlements),
                    "currency": currency
                }
            )

        elif role == "fleet_admin":
            # Get aggregate for the entire tenant
            try:
                tenant_user = TenantUser.objects.filter(user=user).first()
                tenant = tenant_user.tenant
            except TenantUser.DoesNotExist:
                return Response({"error": "Tenant not found"}, status=404)

            # Aggregate by driver
            driver_ids = DriverFleetAssignment.objects.filter(
                tenant_id=tenant
            ).values_list("driver_id", flat=True)


            driver_aggregates = (
                Settlement.objects
                .filter(
                    settlement_type="driver",
                    tenant=tenant
                )
                .values(
                    first_name=F("entity__user__first_name"),
                    last_name=F("entity__user__last_name"),
                    currency_code=F("currency"),
                )
                .annotate(
                    total_earned=Sum("net_amount"),
                    ride_count=Count("payment"),
                )
                .order_by("-total_earned")
            )

            conversion_map = {
                c.currency_code.country_code: c.conversion_rate_to_usd
                for c in CurrencyConversion.objects.select_related("currency_code")
            }

            driver_data = []

            for row in driver_aggregates:
                rate = conversion_map.get(row["currency_code"], Decimal("1"))
                row["total_earned_usd"] = row["total_earned"] * rate
                driver_data.append(row)

            tenant_status_summary = (
                Settlement.objects.filter(
                    settlement_type="tenant", 
                    tenant=tenant
                )
                .values(
                    status=F("payment_status__status_name"),
                    currency_code=F("currency")
                )
                .annotate(total_amount=Sum("net_amount"))
            )

            tenant_totals = (
                Settlement.objects
                .filter(settlement_type="tenant", tenant=tenant)
                .values(currency_code=F("currency"))
                .annotate(total_amount=Sum("net_amount"))
            )

            total_fleet_usd = Decimal("0.00")

            for row in tenant_totals:
                rate = conversion_map.get(row["currency_code"], Decimal("1"))
                total_fleet_usd += row["total_amount"] * rate

            return Response(
                {
                    "type": "aggregate",
                    "total_earnings": total_fleet_usd,
                    "driver_breakdown": driver_data,
                    "tenant_settlement_status_summary": list(tenant_status_summary),
                }
            )
        
        elif role == "app_admin":
        # Get all tenants for the app admin
            tenants = Tenant.objects.all()

            # Driver breakdown per tenant
            driver_aggregates = (
                Settlement.objects.filter(settlement_type="driver", tenant__in=tenants)
                .values(
                    tenant_name=F("tenant__tenant_name"),
                    first_name=F("entity__user__first_name"),
                    last_name=F("entity__user__last_name"),
                    currency_code=F("currency"),
                )
                .annotate(
                    total_earned=Sum("net_amount"),
                    ride_count=Count("payment")
                )
                .order_by("-total_earned")
            )

            conversion_map = {
                c.currency_code.country_code: c.conversion_rate_to_usd
                for c in CurrencyConversion.objects.select_related("currency_code")
            }

            driver_data = []
            for row in driver_aggregates:
                rate = conversion_map.get(row["currency_code"], Decimal("1"))
                row["total_earned_usd"] = row["total_earned"] * rate
                driver_data.append(row)

            # App admin's own commission settlements
            admin_settlements = Settlement.objects.all().values(
                currency_code = F("currency"),
                status=F("payment_status__status_name"),
            ).annotate(total_amount=Sum("commission_amount"))

            admin_total_usd = Decimal("0.00")
            for row in admin_settlements:
                rate = conversion_map.get(row["currency_code"], Decimal("1"))
                admin_total_usd += row["total_amount"] * rate

            currencies = list(admin_settlements.values_list("currency_code", flat=True).distinct())
            currency = currencies[0] if currencies else None

            return Response({
                "type": "app_admin",
                "driver_breakdown": driver_data,
                "total_earnings": admin_total_usd,
                # "currency": currency
                "tenant_settlement_status_summary": list(admin_settlements),
            })

        # ----------------------------------------
        # UNKNOWN ROLE
        # ----------------------------------------
        else:
            return Response({"error": "Invalid role"}, status=400)
