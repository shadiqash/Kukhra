from django.contrib import admin

from .models import GoodsReceived, PurchaseOrder


class GoodsReceivedInline(admin.TabularInline):
    model         = GoodsReceived
    extra         = 0
    readonly_fields = ('received_at', 'received_by', 'lot', 'location', 'notes')
    can_delete    = False


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'supplier', 'status', 'total_paisa', 'created_at')
    list_filter   = ('status', 'supplier__type')
    search_fields = ('supplier__name',)
    readonly_fields = ('created_at', 'updated_at')
    inlines       = [GoodsReceivedInline]


@admin.register(GoodsReceived)
class GoodsReceivedAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'purchase_order', 'location', 'received_at', 'received_by', 'lot')
    list_filter   = ('location',)
    search_fields = ('purchase_order__supplier__name', 'lot__code')
    readonly_fields = ('created_at', 'updated_at')
