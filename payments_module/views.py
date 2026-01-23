from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from decimal import Decimal

from authentication.models import User
from drivers.models import VehicleType
from payments_module.models import Payment, PaymentStatusLookup, RideFareSnapshot, Wallet, WalletTransaction
from payments_module.serializers import *


#endpoints related to payments

class PaymentCreateView(APIView):
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pending_status = PaymentStatusLookup.objects.get(status_name="PENDING")

        payment = serializer.save(
            payment_status=pending_status,
            created_at=now()
        )

        return Response(
            PaymentStatusSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )


class PaymentCompleteView(APIView):
    def post(self, request):
        payment_id = request.data.get("payment_id")

        payment = Payment.objects.get(payment_id=payment_id)
        completed_status = PaymentStatusLookup.objects.get(status_name="COMPLETED")

        payment.payment_status = completed_status
        payment.save()

        return Response({"status": "COMPLETED"})


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

        return Response(
            PaymentStatusSerializer(payments, many=True).data
        )


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


class FareCalculateView(APIView):
    def post(self, request):
        serializer = FareCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # print("serialized data", data)

        pricing = PricingConfig.objects.filter(region_id=data["region_id"], vehicle_type = VehicleType.objects.get(vehicle_type_id = data["vehicle_type"]))
        # print("pricing_config object", pricing[0])
        surge = SurgePricing.objects.filter(region=pricing[0].region_id).last()

        surge_multiplier = surge.surge_multiplier if surge else Decimal("1.0")

        base = pricing[0].base_fare
        distance_fare = pricing[0].rate_per_km * data["distance_km"]
        time_fare = pricing[0].rate_per_min * data["duration_min"]

        total = (base + distance_fare + time_fare) * surge_multiplier

        snapshot = RideFareSnapshot.objects.create(
            ride_id=data["ride_id"],
            rider_id=data["rider_id"],
            base_fare=base,
            distance_fare=distance_fare,
            time_fare=time_fare,
            surge_multiplier=surge_multiplier,
            tax_amount=Decimal("0.0"),
            final_fare=total,
            currency="INR"
        )

        snapshot_serializer = RideFareSnapshotSerializer(snapshot)
        return Response({"final_fare": snapshot.final_fare, "breakdown": snapshot_serializer.data})
    

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


#endpoints related to Settlements

class SettlementCreateView(APIView):
    def post(self, request):
        serializer = SettlementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"created": True})


class SettlementFetchView(APIView):
    def post(self, request):
        serializer = SettlementFetchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        settlements = Settlement.objects.filter(**serializer.validated_data)
        return Response(settlements.values())


class SettlementUpdateView(APIView):
    def post(self, request):
        settlement_id = request.data.get("settlement_id")
        status_name = request.data.get("status")

        settlement = Settlement.objects.get(settlement_id=settlement_id)
        settlement.payment_status = PaymentStatusLookup.objects.get(
            status_name=status_name
        )
        settlement.save()

        return Response({"updated": True, "settlement_id": settlement_id , "status_name": status_name})


#endpoints related to wallets
class CreateWalletView(APIView):
    def post(self, request):
        user = User.objects.get(user_id = request.data["user_id"])

        wallet = Wallet.objects.create(
            user= user,
            currency_code = "IST",
            amount=0
        )
        wallet.save()

        return Response({"user_id": user.user_id , "wallet_id": wallet.wallet_id})

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


class WalletPayView(APIView):
    def post(self, request):
        serializer = WalletFetchSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        wallet = Wallet.objects.get(**serializer.validated_data)
        
        amount = Decimal(request.data["amount"])
        if amount <= 0:
            return Response({"error": "Can't pay negative amounts"})

        if wallet.amount < amount:
            return Response({"error": "Insufficient balance"}, status=400)

        wallet.amount -= amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type="debit"
        )
        return Response({"balance": wallet.amount, "user_id" :wallet.user.user_id, "wallet_id": wallet.wallet_id})


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
