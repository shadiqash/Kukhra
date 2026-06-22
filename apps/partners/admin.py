from django.contrib import admin

from .models import Customer, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display  = ('name', 'type', 'pan')
    list_filter   = ('type',)
    search_fields = ('name', 'pan')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ('name', 'type', 'credit_limit_paisa', 'pan')
    list_filter   = ('type',)
    search_fields = ('name', 'pan')
