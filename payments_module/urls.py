from django.urls import path
from payments_module.views import *

urlpatterns = [
    # ---------------- Payments ----------------
    path("create/", PaymentCreateView.as_view()),
    path("complete/", PaymentCompleteView.as_view()),
    path("status/<uuid:payment_id>/", PaymentStatusView.as_view()),
    path("fetch/", PaymentFetchView.as_view()),
    path("gateway_event/", PaymentGatewayEventCreateView.as_view()),

    # ---------------- Pricing ----------------
    path("pricing/config/<uuid:region_id>/", PricingConfigView.as_view()),
    path("pricing/config/", PricingConfigCreateView.as_view()),
    path("pricing/calculate/", FareCalculateView.as_view()),
    path("pricing/surge/<uuid:region_id>/", SurgePricingView.as_view()),
    path("pricing/surge/", SurgePricingCreateView.as_view()),

    # ---------------- Settlements ----------------
    path("settlements/create/", SettlementCreateView.as_view()),
    path("settlements/fetch/", SettlementFetchView.as_view()),
    path("settlements/update/", SettlementUpdateView.as_view()),

    # ---------------- Wallet ----------------
    path("wallet/create/", CreateWalletView.as_view()),
    path("wallet/add/", WalletAddView.as_view()),
    path("wallet/pay/", WalletPayView.as_view()),
    path("wallet/balance/<uuid:user_id>/", WalletBalanceView.as_view()),
    path("wallet/transactions/fetch/", WalletTransactionFetchView.as_view()),
]