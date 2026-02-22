from rest_framework import serializers
from payments_module.models import Payment, PaymentGatewayEvent,PricingConfig, SurgePricing, Settlement, RideFareSnapshot


class PaymentStatusSerializer(serializers.ModelSerializer):
    payment_status = serializers.CharField(source="payment_status.status_name")

    class Meta:
        model = Payment
        fields = ["payment_id", "payment_status", "amount_total", "currency", "payment_method"]


class PaymentFetchSerializer(serializers.Serializer):
    ride_id = serializers.UUIDField(required=False)
    user_id = serializers.UUIDField(required=False)
    driver_id = serializers.UUIDField(required=False)


class PaymentGatewayEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGatewayEvent
        fields = ["payment", "gateway_event"]


class PricingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingConfig
        fields = "__all__"


class SurgePricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurgePricing
        fields = "__all__"


class RideFareSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideFareSnapshot
        fields = "__all__"



class WalletFetchSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    wallet_id = serializers.UUIDField()

class WalletTransactionFetchSerializer(serializers.Serializer):
    wallet_id = serializers.UUIDField()
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
