from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import Role
from apps.catalog.models import Product
from apps.lots.models import Lot

from .models import MovementType, StockMovement, StockTransfer


# sale / transfer / return are written only by their own transactions
# (order fulfil, transfer dispatch+receipt, order cancel), each with its own
# oversell and reconciliation guards. Forging one of those rows here would bypass
# all of them, so the manual ledger endpoint refuses them. Production-in (own
# slaughter output has no dedicated endpoint in Phase 1), stock-count adjustments,
# and wastage are the legitimate hand-posted rows.
MANUAL_MOVEMENT_TYPES = frozenset({
    MovementType.PRODUCTION, MovementType.ADJUSTMENT, MovementType.WASTAGE,
})

# Who may write stock off as wastage: managers/admins and the warehouse role that
# records production batches. (Procurement has no inventory-movement access at all
# per the role matrix; cashiers and outlet managers are read-only on inventory.)
WASTAGE_ROLES = frozenset({Role.MANAGER, Role.SUPERUSER, Role.WAREHOUSE})


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'location', 'lot', 'type',
            'qty_kg', 'qty_pieces', 'ref_id', 'user',
            'created_at',
        ]
        # `user` is stamped from the request in the viewset — a client must
        # never attribute a ledger row to someone else. `ref_id` too: a manual
        # correction is not allowed to impersonate an order/transfer document.
        read_only_fields = ['id', 'user', 'ref_id', 'created_at']

    def validate(self, attrs):
        mtype = attrs.get('type')
        if mtype not in MANUAL_MOVEMENT_TYPES:
            raise serializers.ValidationError({
                'type': (
                    f'The movement endpoint only accepts corrections '
                    f'({", ".join(sorted(MANUAL_MOVEMENT_TYPES))}); '
                    f'{mtype!r} rows are written by their own flows.'
                ),
            })

        # Wastage may be recorded by a manager/superuser or by the warehouse role —
        # the staff who record production batches and physically see spoilage.
        # Cashiers, outlet managers, procurement and customers may not.
        if mtype == MovementType.WASTAGE:
            user = getattr(self.context.get('request'), 'user', None)
            if getattr(user, 'role', None) not in WASTAGE_ROLES:
                raise serializers.ValidationError({
                    'type': 'Only a manager or warehouse (batch recorder) may post a wastage movement.',
                })

        qty_kg     = attrs.get('qty_kg')     or 0
        qty_pieces = attrs.get('qty_pieces') or 0
        if qty_kg == 0 and qty_pieces == 0:
            raise serializers.ValidationError('A movement must carry some weight or some pieces.')
        return attrs

    def update(self, instance, validated_data):
        raise serializers.ValidationError('StockMovement is append-only; updates are not permitted.')


class TransferLineSerializer(serializers.Serializer):
    """
    A transfer line is not its own table — it is the transfer-out StockMovement row.
    This serializer is the write shape for dispatch and the read shape for display.
    """
    product    = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    lot        = serializers.PrimaryKeyRelatedField(
                     queryset=Lot.objects.all(), required=False, allow_null=True,
                 )
    qty_kg     = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, default=Decimal('0'))
    qty_pieces = serializers.IntegerField(required=False, default=0)

    def validate(self, attrs):
        qty_kg     = attrs.get('qty_kg')     or Decimal('0')
        qty_pieces = attrs.get('qty_pieces') or 0
        if qty_kg < 0 or qty_pieces < 0:
            raise serializers.ValidationError(
                'Transfer quantities are entered positive; the ledger sign is applied server-side.'
            )
        if qty_kg == 0 and qty_pieces == 0:
            raise serializers.ValidationError('A line must move some weight or some pieces.')
        return attrs


class StockTransferSerializer(serializers.ModelSerializer):
    lines = TransferLineSerializer(many=True, write_only=True)
    items = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            'id', 'from_location', 'to_location', 'status',
            'dispatched_at', 'received_at', 'received_by',
            'lines', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'received_at', 'received_by', 'created_at', 'updated_at']

    def get_items(self, obj):
        """Line items, read back off the ledger with the sign flipped to positive."""
        return [
            {
                'product': m.product_id,
                'product_name': m.product.name,
                'lot': m.lot_id,
                'qty_kg': -m.qty_kg,
                'qty_pieces': -m.qty_pieces,
            }
            for m in obj.out_movements()
        ]

    def validate(self, attrs):
        if attrs.get('from_location') == attrs.get('to_location'):
            raise serializers.ValidationError('A transfer must move stock between two different locations.')
        if not attrs.get('lines'):
            raise serializers.ValidationError({'lines': 'A transfer must carry at least one line.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Header and its transfer-out movements are written together: a transfer that
        moves nothing must never exist, and an oversell must roll the header back too.
        """
        lines = validated_data.pop('lines')
        user = self.context['request'].user

        transfer = StockTransfer.objects.create(**validated_data)
        try:
            transfer.dispatch(lines, user=user)
        except RuntimeError as exc:
            raise serializers.ValidationError({'detail': str(exc)})
        return transfer
