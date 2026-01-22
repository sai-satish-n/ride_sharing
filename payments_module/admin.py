from django.contrib import admin
from payments_module.models import *

admin.site.register(PricingConfig)
admin.site.register(SurgePricing)
admin.site.register(RideFareSnapshot)
admin.site.register(PaymentStatusLookup)
admin.site.register(Payment)
admin.site.register(PaymentGatewayEvent)
admin.site.register(Settlement)
admin.site.register(Wallet)
admin.site.register(WalletTransaction)