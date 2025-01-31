from django.contrib import admin
from . import models
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin

class WalletInline(admin.StackedInline):
    model = models.Wallet
    max_num = 1
    can_delete = False

class UserAdmin(AuthUserAdmin):
 inlines = [WalletInline]

# unregister old user admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

class BusSeatInline(admin.TabularInline):
    model = models.Bus_Seat

@admin.register(models.Bus)
class DisplayBus(admin.ModelAdmin):
    model = models.Bus
    list_display = ['license_plate', 'company']
    inlines = [BusSeatInline]

admin.site.register(models.Stop)
admin.site.register(models.Seat)
admin.site.register(models.AdminUser)
admin.site.register(models.Wallet)

