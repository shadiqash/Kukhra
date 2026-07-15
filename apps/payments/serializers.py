from rest_framework import serializers

from apps.locations.models import Location
from apps.sales.models import CashierSession

from .models import Gateway, PaymentIntent


class PaymentIntentCreateSerializer(serializers.Serializer):
    """
    The amount is set here, server-side, and is what the customer is asked to pay.
    It is never re-read from the client at checkout — that is the whole point.
    """
    gateway            = serializers.ChoiceField(choices=Gateway.choices)
    amount_paisa       = serializers.IntegerField(min_value=1)
    fulfilled_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    session            = serializers.PrimaryKeyRelatedField(
                             queryset=CashierSession.objects.all(), required=False, allow_null=True,
                         )


class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'gateway', 'status', 'amount_paisa', 'prn', 'gateway_ref',
            'qr_payload', 'verified_at', 'failure_reason', 'created_at',
        ]
        # Everything about an intent is decided by the server and the gateway.
        # A client may create one and read it; it may never write to one.
        read_only_fields = fields
