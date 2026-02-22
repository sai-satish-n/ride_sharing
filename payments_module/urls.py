from django.urls import path
from payments_module.views import *

urlpatterns = [
    # ---------------- Payments ----------------
    path("status/<uuid:payment_id>/", PaymentStatusView.as_view()),
    path("fetch/", PaymentFetchView.as_view()),
    path("gateway_event/", PaymentGatewayEventCreateView.as_view()),    #not included in frontend

    # ---------------- Pricing ----------------
    path("pricing/config/<uuid:region_id>/", PricingConfigView.as_view()),      #not included in frontend
    path("pricing/config/", PricingConfigCreateView.as_view()),                 #not included in frontend
    path("pricing/surge/<uuid:region_id>/", SurgePricingView.as_view()),        #not included in frontend
    path("pricing/surge/", SurgePricingCreateView.as_view()),                   #not included in frontend

    # ---------------- Wallet ----------------
    path("wallet/create/", CreateWalletView.as_view()),
    path("wallet/add/", WalletAddView.as_view()),
    path("wallet/balance/<uuid:user_id>/", WalletBalanceView.as_view()),
    path("wallet/transactions/fetch/", WalletTransactionFetchView.as_view()),

    path("proceed_to_payment/", ProceedToPaymentView.as_view(), name="create_payment"),
    path("pay_with_wallet/", PayWithWalletView.as_view(), name="pay_with_wallet"),
    path("confirm_password/", ConfirmPasswordView.as_view(), name="confirm_password"),
    path("earnings/", EarningsView.as_view(), name="earnings"),
]