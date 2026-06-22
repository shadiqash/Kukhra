from rest_framework import serializers

from .models import CreditNote, Invoice, InvoiceLine


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'invoice', 'order_line', 'product', 'price',
            'tax_class', 'qty_kg', 'qty_pieces',
            'unit_paisa', 'line_total_paisa', 'vat_paisa',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'order', 'customer', 'invoice_number',
            'issued_at', 'exempt_paisa', 'taxable_paisa', 'vat_paisa', 'total_paisa',
            'cbms_status', 'lines',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'exempt_paisa', 'taxable_paisa', 'vat_paisa', 'total_paisa',
            'cbms_status', 'created_at', 'updated_at',
        ]


class CreditNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNote
        fields = [
            'id', 'invoice', 'reason', 'amount_paisa',
            'issued_at', 'issued_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
