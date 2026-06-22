from django.contrib import admin

from .models import CashierSession, Order, OrderLine, Payment


class OrderLineInline(admin.TabularInline):
    model         = OrderLine
    extra         = 0
    readonly_fields = ('product', 'price', 'qty_kg', 'qty_pieces', 'line_total_paisa')
    can_delete    = False


class PaymentInline(admin.TabularInline):
    model         = Payment
    extra         = 0
    readonly_fields = ('method', 'amount_paisa', 'ref')
    can_delete    = False


@admin.register(CashierSession)
class CashierSessionAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'cashier', 'counter', 'opened_at', 'closed_at', 'opening_float_paisa', 'closing_counted_paisa')
    list_filter   = ('counter__location', 'cashier')
    readonly_fields = ('closed_at', 'closing_counted_paisa', 'created_at', 'updated_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'source', 'status', 'fulfilled_location', 'customer', 'total_paisa', 'created_at')
    list_filter   = ('source', 'status', 'fulfilled_location')
    search_fields = ('customer__name',)
    readonly_fields = ('status', 'created_at', 'updated_at')
    inlines       = [OrderLineInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'order', 'method', 'amount_paisa', 'ref')
    list_filter   = ('method',)
    search_fields = ('ref',)
