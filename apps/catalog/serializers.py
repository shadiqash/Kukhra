from django.db import IntegrityError
from rest_framework import serializers

from .models import Price, Product
from .services import PriceRotationError, rotate_price


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

    def validate(self, attrs):
        valid_to = attrs.get('valid_to')
        if valid_to is not None and valid_to < attrs['valid_from']:
            raise serializers.ValidationError(
                {'valid_to': 'valid_to must be on or after valid_from.'}
            )
        return attrs

    def create(self, validated_data):
        """
        A new *active* price (valid_to omitted) is a price change: the current
        active row for that (product, tier) is closed in the same transaction.
        Rows with valid_to set are historical backfill and insert as-is.
        """
        if validated_data.get('valid_to') is None:
            try:
                return rotate_price(
                    product=validated_data['product'],
                    tier=validated_data['tier'],
                    price_paisa=validated_data['price_paisa'],
                    valid_from=validated_data['valid_from'],
                )
            except PriceRotationError as exc:
                raise serializers.ValidationError({'valid_from': str(exc)})
            except IntegrityError:
                raise serializers.ValidationError(
                    'Another price change for this product and tier landed at the '
                    'same moment — retry to rotate on top of it.'
                )
        return super().create(validated_data)
