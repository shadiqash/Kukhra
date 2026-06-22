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
    def confirm_receipt(self, user, received_at=None) -> None:
        """
        Mirrors every transfer-out movement for this transfer as a positive
        transfer-in movement at to_location. Idempotency guard: raises if already received.
        """
        if self.status == TransferStatus.RECEIVED:
            raise RuntimeError(f'StockTransfer #{self.pk} has already been received.')

        ts = received_at or timezone.now()

        out_movements = StockMovement.objects.filter(
            ref_id=self.pk,
            type=MovementType.TRANSFER,
            location=self.from_location,
        )
        for m in out_movements:
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
