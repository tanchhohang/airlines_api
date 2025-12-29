from django.contrib import admin
from .models import Sector, Airline, Passenger, Booking

admin.site.register(Sector)
admin.site.register(Airline)
admin.site.register(Passenger)
admin.site.register(Booking)