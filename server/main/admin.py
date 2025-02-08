from django.contrib import admin
from . import models

from django.db.models import Q

admin.site.register(models.Seat)

class BusSeatInline(admin.TabularInline):
    exclude = ['price']
    model = models.Bus_Seat

@admin.register(models.Bus)
class DisplayBus(admin.ModelAdmin):
    model = models.Bus
    list_display = ['license_plate', 'company']
    inlines = [BusSeatInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__user=request.user)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'company':
            kwargs['queryset'] = models.AdminUser.objects.filter(user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
    actions = ['export_csv']

    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        for route in queryset:
            response['Content-Disposition'] = f'attachment; filename="{route._str_()}.csv"'

            writer = csv.writer(response)
            writer.writerow(['Date', 'Seat Type', 'Start Stop', 'End Stop', 'Booked By', 'Name', 'Age', 'Email', 'Gender'])
            tickets = models.Ticket.objects.filter(booking__start_stop__route=route).order_by('booking__date')
            for ticket in tickets:
                writer.writerow([ticket.booking.date, ticket.seat_type, ticket.booking.start_stop.stop.name, ticket.booking.end_stop.stop.name, ticket.booking.user.email, ticket.name, ticket.age, ticket.email, ticket.gender])
        
        return response
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(bus__company__user=request.user)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'bus':
            kwargs['queryset'] = models.Bus.objects.filter(company__user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed, protected = \
            super().get_deleted_objects(objs, request)
        return deleted_objects, model_count, set(), protected

@admin.register(models.AdminUser)
class DisplayAdminUser(admin.ModelAdmin):
    model = models.AdminUser
    list_display = ['company_name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    
@admin.register(models.Transaction)
class DisplayTransaction(admin.ModelAdmin):

    model = models.Transaction

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(Q(sendingID=models.Wallet.objects.filter(user = request.user).first()) | Q(receivingID=models.Wallet.objects.filter(user = request.user).first()))

@admin.register(models.Wallet)
class DisplayWallet(admin.ModelAdmin):
    model = models.Wallet

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

@admin.register(models.Booking)
class DisplayBooking(admin.ModelAdmin):
    model = models.Booking

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(bus__company__user=request.user)

@admin.register(models.Ticket)
class DisplayTicket(admin.ModelAdmin):
    model = models.Ticket

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(booking__bus__company__user=request.user)


admin.site.register(models.OtpToken)


