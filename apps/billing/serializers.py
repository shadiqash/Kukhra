from decimal import Decimal

from rest_framework import serializers

from apps.sales.serializers import validate_line_total

from .models import CbmsStatus, CreditNote, Invoice, InvoiceLine


class InvoiceLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'invoice', 'order_line', 'product', 'product_name', 'price',
            'tax_class', 'qty_kg', 'qty_pieces',
            'unit_paisa', 'line_total_paisa', 'vat_paisa',
            'created_at', 'updated_at',
        ]
        # tax_class snapshots the product and vat is computed from it — both are
        # decided server-side, never taken from the client. Otherwise a caller could
        # label a taxable good exempt, or under-report VAT, on the tax document itself.
        read_only_fields = ['id', 'product_name', 'tax_class', 'vat_paisa', 'created_at', 'updated_at']

    def validate(self, attrs):
        """
        H4: an invoice line is part of a tax document — its arithmetic must be
        internally consistent and its parent must still be amendable.
        """
        invoice = attrs.get('invoice')
        if invoice is not None and invoice.cbms_status != CbmsStatus.PENDING:
            raise serializers.ValidationError(
                f'Invoice {invoice.invoice_number} has already been submitted to CBMS '
                f'({invoice.cbms_status}); its lines are frozen. Issue a credit note instead.'
            )

        qty_kg     = attrs.get('qty_kg')     or Decimal('0')
        qty_pieces = attrs.get('qty_pieces') or 0
        if qty_kg < 0 or qty_pieces < 0:
            raise serializers.ValidationError('Quantities must be positive.')
        if qty_kg == 0 and qty_pieces == 0:
            raise serializers.ValidationError('A line must bill some weight or some pieces.')

        price = attrs.get('price')
        product = attrs.get('product')
        if price and product and price.product_id != product.pk:
            raise serializers.ValidationError(
                f'Price #{price.pk} belongs to a different product than {product.name}.'
            )
        if price and attrs.get('unit_paisa') != price.price_paisa:
            raise serializers.ValidationError(
                f'unit_paisa {attrs.get("unit_paisa")} ≠ referenced price ({price.price_paisa}).'
            )
        if price:
            validate_line_total(price, qty_kg, qty_pieces, attrs['line_total_paisa'])
        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    lines        = InvoiceLineSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, default=None)
    customer_pan  = serializers.CharField(source='customer.pan',  read_only=True, default=None)

    class Meta:
        model = Invoice
        fields = [
            'id', 'order', 'customer', 'customer_name', 'customer_pan', 'invoice_number',
            'issued_at', 'exempt_paisa', 'taxable_paisa', 'vat_paisa', 'total_paisa',
            'cbms_status', 'lines',
            'created_at', 'updated_at',
        ]
        # invoice_number comes off the server-side sequence and issued_at is
        # stamped at creation (H4): a tax document may be neither renumbered
        # nor backdated by the client.
        read_only_fields = [
            'id', 'customer_name', 'customer_pan', 'invoice_number', 'issued_at',
            'exempt_paisa', 'taxable_paisa', 'vat_paisa', 'total_paisa',
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
        # issued_by is stamped from the request and issued_at at creation —
        # a reversal document records who actually issued it, when.
        read_only_fields = ['id', 'issued_at', 'issued_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Cumulative credit against an invoice must never exceed what it billed."""
        invoice = attrs['invoice']
        already = sum(cn.amount_paisa for cn in invoice.credit_notes.all())
        if already + attrs['amount_paisa'] > invoice.total_paisa:
            raise serializers.ValidationError(
                f'Credit {attrs["amount_paisa"]} paisa would exceed the invoice: '
                f'{invoice.total_paisa} paisa billed, {already} paisa already credited.'
            )
        return attrs
