from django.contrib import admin
from rides.models import *

admin.site.register(Country)
admin.site.register(State)
admin.site.register(RegionTypeLookup)
admin.site.register(Region)
admin.site.register(TenantRegion)
admin.site.register(RideStatusLookup)
admin.site.register(Ride)
admin.site.register(RideDetailsForRiders)
admin.site.register(RideLocationLog)
admin.site.register(EventLog)
admin.site.register(RidesDispatch)
admin.site.register(RidesFeedback)