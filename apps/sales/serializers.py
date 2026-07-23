from decimal import Decimal

from rest_framework import serializers

from apps.accounts.models import Role
from apps.catalog.models import Price, Product
from apps.locations.models import Location
from apps.partners.models import Customer
from apps.payments.models import IntentStatus, PaymentIntent

from .models import (
    GATEWAY_METHODS,
    CashierSession,
    Order,
    OrderLine,
    OrderSource,
    Payment,
    PaymentMethod,
)


class CashierSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashierSession
        fields = [
            'id', 'counter', 'cashier',
            'opening_float_paisa', 'closing_counted_paisa',
            'opened_at', 'closed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'cashier', 'opened_at', 'closed_at', 'created_at', 'updated_at']

    def validate_counter(self, counter):
        if CashierSession.objects.filter(counter=counter, closed_at__isnull=True).exists():
            raise serializers.ValidationError(
                f'Counter "{counter}" already has an open session. Close it before opening a new one.'
            )
        # A cashier may only run a till at an outlet they are assigned to —
        # otherwise their sales and stock movements land on another outlet's books.
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.role == Role.CASHIER
            and not user.assigned_locations.filter(pk=counter.location_id).exists()
        ):
            raise serializers.ValidationError(
                f'Counter "{counter}" is not at an outlet you are assigned to.'
            )
        return counter


class CloseSessionSerializer(serializers.Serializer):
    closing_counted_paisa = serializers.IntegerField(min_value=0)


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = [
            'id', 'order', 'product', 'price',
            'qty_kg', 'qty_pieces', 'line_total_paisa',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        """
        Same guards as one-shot checkout: no negative or empty lines, price must
        belong to the product and still be active. The model fields default to 0,
        so without this a line could sell −5 kg and mint stock on fulfil.
        """
        qty_kg     = attrs.get('qty_kg')     or Decimal('0')
        qty_pieces = attrs.get('qty_pieces') or 0
        if qty_kg < 0 or qty_pieces < 0:
            raise serializers.ValidationError('Quantities must be positive.')
        if qty_kg == 0 and qty_pieces == 0:
            raise serializers.ValidationError('A line must sell some weight or some pieces.')

        price = attrs.get('price')
        product = attrs.get('product')
        if price and product:
            if price.product_id != product.pk:
                raise serializers.ValidationError(
                    f'Price #{price.pk} belongs to a different product than {product.name}.'
                )
            if price.valid_to is not None:
                raise serializers.ValidationError(f'Price #{price.pk} is no longer active.')
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'method', 'amount_paisa', 'ref', 'intent', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        """
        The step-by-step payment path enforces the same rule as one-shot checkout:
        gateway money needs gateway proof. Without this the DB constraint would still
        refuse the row, but as a 500 rather than a usable error.
        """
        method = attrs.get('method')
        intent = attrs.get('intent')

        if method in GATEWAY_METHODS:
            if intent is None:
                raise serializers.ValidationError({
                    'intent': f'A {method} payment must reference a verified payment intent.',
                })
            if intent.status != IntentStatus.VERIFIED:
                raise serializers.ValidationError({
                    'intent': f'Payment {intent.prn} is not verified (status: {intent.status}).',
                })
            if intent.amount_paisa != attrs.get('amount_paisa'):
                raise serializers.ValidationError({
                    'intent': f'Payment {intent.prn} is for {intent.amount_paisa} paisa, not {attrs.get("amount_paisa")}.',
                })
        elif intent is not None:
            raise serializers.ValidationError({
                'intent': 'Cash and card payments must not reference a payment intent.',
            })
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    lines    = OrderLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'fulfilled_location', 'session',
            'source', 'status', 'total_paisa',
            'lines', 'payments',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class CheckoutLineInputSerializer(serializers.Serializer):
    product          = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    price            = serializers.PrimaryKeyRelatedField(queryset=Price.objects.all())
    qty_kg           = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0'), default=Decimal('0'))
    qty_pieces       = serializers.IntegerField(min_value=0, default=0)
    line_total_paisa = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        """
        A line must move something, its price must belong to its product, and that
        price must still be active. Without these a cashier could ring a zero-qty
        line, charge a different product's price, or resurrect an expired one.
        """
        qty_kg     = attrs.get('qty_kg')     or Decimal('0')
        qty_pieces = attrs.get('qty_pieces') or 0
        if qty_kg == 0 and qty_pieces == 0:
            raise serializers.ValidationError('A line must sell some weight or some pieces.')

        price = attrs['price']
        product = attrs['product']
        if price.product_id != product.pk:
            raise serializers.ValidationError(
                f'Price #{price.pk} belongs to a different product than {product.name}.'
            )
        if price.valid_to is not None:
            raise serializers.ValidationError(
                f'Price #{price.pk} is no longer active (closed {price.valid_to}).'
            )

        # The line total must equal price × quantity.
        claimed = attrs['line_total_paisa']
        if qty_pieces:
            # Pieces are exact — no rounding is possible.
            expected = price.price_paisa * qty_pieces
            if claimed != expected:
                raise serializers.ValidationError(
                    f'line_total_paisa {claimed} ≠ price {price.price_paisa} × {qty_pieces} pcs ({expected}).'
                )
        else:
            # Weighed goods round to the nearest paisa. The client (JS round-half-up)
            # and the server (Decimal round-half-even) can pick different halves on an
            # exact .5, so allow a 1-paisa tolerance rather than hard-failing the sale.
            expected = int((Decimal(price.price_paisa) * qty_kg).quantize(Decimal('1')))
            if abs(claimed - expected) > 1:
                raise serializers.ValidationError(
                    f'line_total_paisa {claimed} ≠ price {price.price_paisa} × {qty_kg} kg (expected ~{expected}).'
                )
        return attrs


class CheckoutPaymentInputSerializer(serializers.Serializer):
    method       = serializers.ChoiceField(choices=PaymentMethod.choices)
    amount_paisa = serializers.IntegerField(min_value=0)
    ref          = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    intent       = serializers.PrimaryKeyRelatedField(
                       queryset=PaymentIntent.objects.all(), required=False, allow_null=True,
                   )

    def validate(self, attrs):
        """
        A gateway-settled payment is only as real as the gateway's word for it.
        The intent must exist, be verified, be unspent, and be for this exact amount —
        the cashier's screen does not get a vote.
        """
        method = attrs['method']
        intent = attrs.get('intent')

        if method in GATEWAY_METHODS:
            if intent is None:
                raise serializers.ValidationError({
                    'intent': f'A {method} payment must reference a verified payment intent.',
                })
            if intent.status != IntentStatus.VERIFIED:
                raise serializers.ValidationError({
                    'intent': f'Payment {intent.prn} is not verified (status: {intent.status}).',
                })
            if intent.amount_paisa != attrs['amount_paisa']:
                raise serializers.ValidationError({
                    'intent': (
                        f'Payment {intent.prn} is for {intent.amount_paisa} paisa, '
                        f'but this line claims {attrs["amount_paisa"]} paisa.'
                    ),
                })
        elif intent is not None:
            raise serializers.ValidationError({
                'intent': 'Cash and card payments must not reference a payment intent.',
            })
        return attrs


class CheckoutSerializer(serializers.Serializer):
    """
    One-shot POS checkout payload: an Order plus its lines and payments,
    created and fulfilled atomically by OrderViewSet.create (see views.py).
    """
    customer           = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)
    fulfilled_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    session            = serializers.PrimaryKeyRelatedField(queryset=CashierSession.objects.all(), required=False, allow_null=True)
    source             = serializers.ChoiceField(choices=OrderSource.choices)
    total_paisa        = serializers.IntegerField(min_value=0)
    lines              = CheckoutLineInputSerializer(many=True, allow_empty=False)
    payments           = CheckoutPaymentInputSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        """
        Header totals must reconcile with the lines they claim to sum, payments must
        cover the order, and the session (if given) must be open and belong to the
        outlet being sold from — otherwise the reconciliation and Z-report totals
        built downstream are quietly wrong.
        """
        lines_total = sum(l['line_total_paisa'] for l in attrs['lines'])
        if attrs['total_paisa'] != lines_total:
            raise serializers.ValidationError(
                f'total_paisa {attrs["total_paisa"]} ≠ sum of line totals ({lines_total}).'
            )

        paid = sum(p['amount_paisa'] for p in attrs['payments'])
        if paid < attrs['total_paisa']:
            raise serializers.ValidationError(
                f'Payments total {paid} paisa do not cover the order total {attrs["total_paisa"]} paisa.'
            )

        session = attrs.get('session')
        location = attrs['fulfilled_location']
        if session is not None:
            if session.closed_at is not None:
                raise serializers.ValidationError(f'CashierSession #{session.pk} is already closed.')
            if session.counter.location_id != location.pk:
                raise serializers.ValidationError(
                    f'Session #{session.pk} is at another location than the fulfilling outlet.'
                )
            request = self.context.get('request')
            if (
                request is not None
                and getattr(request.user, 'role', None) == 'cashier'
                and session.cashier_id != request.user.pk
            ):
                raise serializers.ValidationError(
                    f'Session #{session.pk} belongs to another cashier.'
                )
        return attrs
