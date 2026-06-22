from rest_framework import serializers

from .models import Lot


class LotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lot
        fields = [
            'id', 'code', 'source_type', 'supplier', 'arrival_location',
            'live_weight_kg', 'bird_count', 'accumulated_cost_paisa', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class LotTransitionSerializer(serializers.Serializer):
    status = serializers.CharField()
