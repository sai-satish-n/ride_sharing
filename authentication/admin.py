from django.contrib import admin
from authentication.models import *


admin.site.register(User)
admin.site.register(TenantStatusLookup)
admin.site.register(Tenant)
admin.site.register(TenantUser)
admin.site.register(Role)
admin.site.register(EmergencyContact)
admin.site.register(UserRole)