from django.contrib import admin

from .models import CreditNote, Invoice, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    model           = InvoiceLine
    extra           = 0
    readonly_fields = ('product', 'price', 'tax_class', 'qty_kg', 'qty_pieces',
                       'unit_paisa', 'line_total_paisa', 'vat_paisa')
    can_delete      = False


class CreditNoteInline(admin.TabularInline):
    model           = CreditNote
    extra           = 0
    readonly_fields = ('reason', 'amount_paisa', 'issued_at', 'issued_by')
    can_delete      = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'invoice_number', 'customer', 'issued_at',
                       'exempt_paisa', 'taxable_paisa', 'vat_paisa', 'total_paisa', 'cbms_status')
    list_filter     = ('cbms_status',)
    search_fields   = ('invoice_number', 'customer__name')
    readonly_fields = ('exempt_paisa', 'taxable_paisa', 'vat_paisa', 'total_paisa',
                       'created_at', 'updated_at')
    inlines         = [InvoiceLineInline, CreditNoteInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display    = ('pk', 'invoice', 'amount_paisa', 'issued_at', 'issued_by')
    readonly_fields = ('created_at', 'updated_at')

    def has_delete_permission(self, request, obj=None):
        return False
