from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import BaseModel


class MovementType(models.TextChoices):
    PRODUCTION = 'production', 'Production'
    TRANSFER   = 'transfer',   'Transfer'
    SALE       = 'sale',       'Sale'
    RETURN     = 'return',     'Return'
    WASTAGE    = 'wastage',    'Wastage'
    ADJUSTMENT = 'adjustment', 'Adjustment'


class TransferStatus(models.TextChoices):
    DISPATCHED = 'dispatched', 'Dispatched'
    RECEIVED   = 'received',   'Received'


class StockMovement(BaseModel):
    """
    Append-only ledger. current_stock(product, location) = SUM(qty_*) over all rows.
    Signed qty: positive = stock in, negative = stock out.
    Corrections are reversing rows — never edits or deletes.
    NOTE: queryset.update() bypasses the model save() guard; never call it on this table.
    """
    product    = models.ForeignKey('catalog.Product',    on_delete=models.PROTECT, related_name='movements')
    location   = models.ForeignKey('locations.Location', on_delete=models.PROTECT, related_name='movements')
    lot        = models.ForeignKey('lots.Lot',           on_delete=models.PROTECT,
                                   null=True, blank=True, related_name='movements')
    type       = models.CharField(max_length=20, choices=MovementType.choices)
    qty_kg     = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0'))
    qty_pieces = models.IntegerField(default=0)
    ref_id     = models.IntegerField(null=True, blank=True)   # FK to Order/StockTransfer/etc.; type field identifies the table
    user       = models.ForeignKey(
                     settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='stock_movements',
                 )

    class Meta:
        ordering = ['created_at']
        indexes  = [
            # Hot path for current_stock(product, location)
            models.Index(fields=['product', 'location'], name='inv_mov_prod_loc_idx'),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError(
                'StockMovement is append-only — edits are not allowed. '
                'Post a new reversing row instead.'
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError(
            'StockMovement rows must never be deleted. '
            'Post a new reversing row instead.'
        )

    def __str__(self):
        return (
            f'{self.get_type_display()} {self.qty_kg}kg/{self.qty_pieces}pc '
            f'@ {self.location_id} [{self.created_at:%Y-%m-%d %H:%M}]'
        )


class StockTransfer(BaseModel):
    """
    Transfer header. Line items live in StockMovement rows (ref_id=self.pk).
    Two-phase: dispatch creates transfer-out movements; confirm_receipt creates
    mirror transfer-in movements at to_location.
    """
    from_location = models.ForeignKey(
                        'locations.Location', on_delete=models.PROTECT, related_name='transfers_out',
                    )
    to_location   = models.ForeignKey(
                        'locations.Location', on_delete=models.PROTECT, related_name='transfers_in',
                    )
    status        = models.CharField(
                        max_length=20, choices=TransferStatus.choices, default=TransferStatus.DISPATCHED,
                    )
    dispatched_at = models.DateTimeField()
    received_at   = models.DateTimeField(null=True, blank=True)
    received_by   = models.ForeignKey(
                        settings.AUTH_USER_MODEL, null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='transfers_received',
                    )

    @transaction.atomic
    def dispatch(self, lines, user) -> None:
        """
        Creates one transfer-out StockMovement per line — negative qty, at from_location.
        Stock physically leaves the origin the moment the van departs, so the ledger
        records it here; it does not arrive anywhere until confirm_receipt(). The gap
        between the two is stock in transit.

        `lines` is an iterable of dicts: product, qty_kg, qty_pieces, lot (optional).

        Concurrency: takes a row-level lock on from_location before reading stock, so
        two dispatches of the same product cannot both pass the check and oversell —
        the same guarantee Order.fulfill() gives at an outlet.

        Raises RuntimeError('Insufficient stock …') if any line exceeds what is on hand.
        """
        from django.db.models import Sum
        from apps.locations.models import Location

        lines = list(lines)
        if not lines:
            raise RuntimeError('A transfer must carry at least one line.')

        location = Location.objects.select_for_update().get(pk=self.from_location_id)

        product_ids = [l['product'].pk for l in lines]
        stock_rows = (
            StockMovement.objects
            .filter(product_id__in=product_ids, location=location)
            .values('product_id')
            .annotate(total_kg=Sum('qty_kg'), total_pieces=Sum('qty_pieces'))
        )
        stock_kg     = {r['product_id']: r['total_kg']     for r in stock_rows}
        stock_pieces = {r['product_id']: r['total_pieces'] for r in stock_rows}

        # Demand is folded per product BEFORE the check. Two lines for the same
        # product must be compared against stock as their sum — checking each
        # against the same undecremented snapshot would let 60 kg + 60 kg both
        # pass against 100 kg on hand and drive the ledger negative.
        needed = {}
        for line in lines:
            product = line['product']
            entry = needed.setdefault(product.pk, {'product': product, 'kg': Decimal('0'), 'pieces': 0})
            entry['kg']     += line.get('qty_kg')     or Decimal('0')
            entry['pieces'] += line.get('qty_pieces') or 0

        shortfalls = []
        for pid, want in needed.items():
            product = want['product']
            if want['kg'] > Decimal('0'):
                have = stock_kg.get(pid) or Decimal('0')
                if have < want['kg']:
                    shortfalls.append(f'{product.name}: need {want["kg"]} kg, have {have} kg')
            if want['pieces'] > 0:
                have = stock_pieces.get(pid) or 0
                if have < want['pieces']:
                    shortfalls.append(f'{product.name}: need {want["pieces"]} pcs, have {have} pcs')
        if shortfalls:
            raise RuntimeError('Insufficient stock — ' + '; '.join(shortfalls))

        for line in lines:
            StockMovement.objects.create(
                product=line['product'],
                location=location,
                lot=line.get('lot'),
                type=MovementType.TRANSFER,
                qty_kg=-(line.get('qty_kg') or Decimal('0')),
                qty_pieces=-(line.get('qty_pieces') or 0),
                ref_id=self.pk,
                user=user,
            )

    def out_movements(self):
        """The transfer-out rows that constitute this transfer's line items."""
        return StockMovement.objects.filter(
            ref_id=self.pk,
            type=MovementType.TRANSFER,
            location=self.from_location,
        ).select_related('product', 'lot')

    @transaction.atomic
    def confirm_receipt(self, user, received_at=None) -> None:
        """
        Mirrors every transfer-out movement for this transfer as a positive
        transfer-in movement at to_location. Idempotency guard: raises if already received.

        The guard re-reads this row under a lock rather than trusting the in-memory
        status: two concurrent confirmations would both see 'dispatched' on their own
        instance and both mirror the movements, landing the stock twice. In an
        append-only ledger those duplicate rows could never be deleted, only reversed.
        The second caller now blocks here, then sees 'received' and is rejected.
        """
        locked = StockTransfer.objects.select_for_update().get(pk=self.pk)
        if locked.status == TransferStatus.RECEIVED:
            raise RuntimeError(f'StockTransfer #{self.pk} has already been received.')

        ts = received_at or timezone.now()

        for m in self.out_movements():
            StockMovement.objects.create(
                product_id=m.product_id,
                location=self.to_location,
                lot_id=m.lot_id,
                type=MovementType.TRANSFER,
                qty_kg=-m.qty_kg,         # negate the negative → positive
                qty_pieces=-m.qty_pieces,
                ref_id=self.pk,
                user=user,
            )

        self.status      = TransferStatus.RECEIVED
        self.received_at = ts
        self.received_by = user
        self.save(update_fields=['status', 'received_at', 'received_by', 'updated_at'])

    def __str__(self):
        return f'Transfer #{self.pk}: {self.from_location} → {self.to_location} [{self.status}]'
