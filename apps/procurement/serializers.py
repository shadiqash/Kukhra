from rest_framework import serializers

from .models import GoodsReceived, PurchaseOrder, PurchaseOrderStatus


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
        # received_by is stamped from the request when the receipt posts its lines —
        # a client must never attribute a receipt to someone else.
        read_only_fields = ['id', 'received_by', 'created_at', 'updated_at']

    def validate_purchase_order(self, po):
        """
        Reject the receipt up front rather than leaving an orphan document behind:
        the client creates the receipt, then posts its lines, so a PO that can never
        be received would otherwise strand a receipt row with no movements.
        """
        if po.status == PurchaseOrderStatus.CANCELLED:
            raise serializers.ValidationError(f'PO #{po.pk} was cancelled; its goods cannot be received.')
        if po.status == PurchaseOrderStatus.RECEIVED:
            raise serializers.ValidationError(f'PO #{po.pk} has already been received.')
        if po.status != PurchaseOrderStatus.SENT:
            raise serializers.ValidationError(
                f'PO #{po.pk} is still a draft — send it to the supplier before receiving goods.'
            )
        return po


class GoodsReceiveLineSerializer(serializers.Serializer):
    product    = serializers.IntegerField()
    qty_kg     = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0, default=0)
    qty_pieces = serializers.IntegerField(min_value=0, default=0)
    lot        = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if (attrs.get('qty_kg') or 0) == 0 and (attrs.get('qty_pieces') or 0) == 0:
            raise serializers.ValidationError('A receipt line must record some weight or some pieces.')
        return attrs
