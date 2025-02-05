from django.contrib import admin
from . import models
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin

admin.site.register(models.Seat)

class BusSeatInline(admin.TabularInline):
    exclude = ['price']
    model = models.Bus_Seat

@admin.register(models.Bus)
class DisplayBus(admin.ModelAdmin):
    model = models.Bus
    list_display = ['license_plate', 'company']
    inlines = [BusSeatInline]

admin.site.register(models.Stop)

class RouteStopsInline(admin.TabularInline):
    model = models.Route_Stops
    extra = 0

class SeatPriceInline(admin.TabularInline):
    exclude = ['booked_seats']
    model = models.Route_Seat

@admin.register(models.Route)
class DisplayRoute(admin.ModelAdmin):
    model = models.Route
    list_display = ['bus', 'route_number', 'verified']
    inlines = [RouteStopsInline, SeatPriceInline]

admin.site.register(models.AdminUser)
admin.site.register(models.Wallet)
admin.site.register(models.Transaction)
admin.site.register(models.Booking)
admin.site.register(models.Ticket)
admin.site.register(models.OtpToken)


