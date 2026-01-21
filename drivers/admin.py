from django.contrib import admin
from drivers.models import *


admin.site.register(DriverStatusLookup)
admin.site.register(Driver)
admin.site.register(DriverFleetAssignment)
admin.site.register(VehicleType)
admin.site.register(Vehicle)
admin.site.register(VehicleDriverAssignment)