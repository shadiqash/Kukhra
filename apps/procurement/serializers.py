from rest_framework import serializers

from .models import GoodsReceived, PurchaseOrder


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = ['id', 'supplier', 'status', 'total_paisa', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class GoodsReceivedSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceived
        fields = [
            'id', 'purchase_order', 'location', 'received_at',
            'received_by', 'lot', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GoodsReceiveLineSerializer(serializers.Serializer):
    product    = serializers.IntegerField()
    qty_kg     = serializers.DecimalField(max_digits=10, decimal_places=3, default=0)
    qty_pieces = serializers.IntegerField(default=0)
    lot        = serializers.IntegerField(required=False, allow_null=True)
