from rest_framework import serializers

from .models import CashierSession, Order, OrderLine, Payment


class CashierSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashierSession
        fields = [
            'id', 'counter', 'cashier',
            'opening_float_paisa', 'closing_counted_paisa',
            'opened_at', 'closed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'closed_at', 'created_at', 'updated_at']


class CloseSessionSerializer(serializers.Serializer):
    closing_counted_paisa = serializers.IntegerField(min_value=0)


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = [
            'id', 'order', 'product', 'price',
            'qty_kg', 'qty_pieces', 'line_total_paisa',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'method', 'amount_paisa', 'ref', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderSerializer(serializers.ModelSerializer):
    lines    = OrderLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'fulfilled_location', 'session',
            'source', 'status', 'total_paisa',
            'lines', 'payments',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
