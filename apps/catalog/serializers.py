from rest_framework import serializers

from .models import Price, Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'barcode', 'uom', 'is_weighed', 'tax_class', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = [
            'id', 'product', 'tier', 'price_paisa',
            'valid_from', 'valid_to',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
