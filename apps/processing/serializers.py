from rest_framework import serializers

from .models import ProcessingRun


class ProcessingRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingRun
        fields = [
            'id', 'lot', 'run_at',
            'input_weight_kg', 'output_weight_kg', 'operator',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
