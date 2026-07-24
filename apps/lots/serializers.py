from rest_framework import serializers

from .models import Lot, LotStatus

# Intake figures frozen once the lot has left 'arrival'.
FROZEN_AFTER_ARRIVAL = ('live_weight_kg', 'bird_count', 'accumulated_cost_paisa')


class LotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lot
        fields = [
            'id', 'code', 'source_type', 'supplier', 'arrival_location',
            'live_weight_kg', 'bird_count', 'accumulated_cost_paisa', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        # EF-10: a lot is a traceability record (Rule 5). Once it advances past
        # 'arrival' — by which point it may have produced StockMovement/GoodsReceived
        # rows — its intake weight, bird count, and cost are locked. Silently
        # rewriting the live weight of a received lot would break recall tracing.
        if self.instance is not None and self.instance.status != LotStatus.ARRIVAL:
            locked = {
                field: 'Locked once the lot has left arrival — this is a traceability record.'
                for field in FROZEN_AFTER_ARRIVAL
                if field in attrs and attrs[field] != getattr(self.instance, field)
            }
            if locked:
                raise serializers.ValidationError(locked)
        return attrs


class LotTransitionSerializer(serializers.Serializer):
    status = serializers.CharField()
