from rest_framework import serializers

from .models import Counter, Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'type', 'lat', 'lng', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = ['id', 'location', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
