from django.utils import timezone
from rest_framework import serializers

from .models import ProcessingRun


class ProcessingRunSerializer(serializers.ModelSerializer):
    # Defaults to "now" — worker devices record runs as they happen.
    run_at = serializers.DateTimeField(default=timezone.now)

    class Meta:
        model = ProcessingRun
        fields = [
            'id', 'lot', 'run_at',
            'input_weight_kg', 'output_weight_kg', 'operator',
            'created_at', 'updated_at',
        ]
        # `operator` is stamped from the request in the viewset.
        read_only_fields = ['id', 'operator', 'created_at', 'updated_at']
