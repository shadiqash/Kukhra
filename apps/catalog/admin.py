from django.contrib import admin

from .models import Price, Product


class PriceInline(admin.TabularInline):
    model         = Price
    extra         = 0
    readonly_fields = ('tier', 'price_paisa', 'valid_from', 'valid_to', 'created_at')
    can_delete    = False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('name', 'barcode', 'uom', 'is_weighed', 'tax_class')
    list_filter   = ('uom', 'tax_class', 'is_weighed')
    search_fields = ('name', 'barcode')
    inlines       = [PriceInline]


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display  = ('product', 'tier', 'price_paisa', 'valid_from', 'valid_to')
    list_filter   = ('tier', 'product__tax_class')
    search_fields = ('product__name',)
    readonly_fields = ('created_at', 'updated_at')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
