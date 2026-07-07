from rest_framework import serializers

from .models import StockMovement, StockTransfer


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'location', 'lot', 'type',
            'qty_kg', 'qty_pieces', 'ref_id', 'user',
            'created_at',
        ]
        # `user` is stamped from the request in the viewset — a client must
        # never attribute a ledger row to someone else.
        read_only_fields = ['id', 'user', 'created_at']

    def update(self, instance, validated_data):
        raise serializers.ValidationError('StockMovement is append-only; updates are not permitted.')


class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = [
            'id', 'from_location', 'to_location', 'status',
            'dispatched_at', 'received_at', 'received_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'received_at', 'received_by', 'created_at', 'updated_at']
