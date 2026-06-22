from django.contrib import admin

from .models import StockMovement, StockTransfer


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display    = ('created_at', 'type', 'product', 'location', 'lot', 'qty_kg', 'qty_pieces', 'ref_id', 'user')
    list_filter     = ('type', 'location', 'product')
    search_fields   = ('product__name', 'location__name', 'lot__code')
    readonly_fields = ('id', 'product', 'location', 'lot', 'type', 'qty_kg', 'qty_pieces', 'ref_id', 'user', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'from_location', 'to_location', 'status', 'dispatched_at', 'received_at', 'received_by')
    list_filter     = ('status', 'from_location', 'to_location')
    readonly_fields = ('status', 'received_at', 'received_by', 'created_at', 'updated_at')
