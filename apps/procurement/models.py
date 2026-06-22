from django.conf import settings
from django.db import models, transaction

from apps.core.models import BaseModel
from apps.inventory.models import MovementType, StockMovement


class PurchaseOrderStatus(models.TextChoices):
    DRAFT     = 'draft',     'Draft'
    SENT      = 'sent',      'Sent to Supplier'
    RECEIVED  = 'received',  'Fully Received'
    CANCELLED = 'cancelled', 'Cancelled'


class PurchaseOrder(BaseModel):
    supplier    = models.ForeignKey('partners.Supplier', on_delete=models.PROTECT, related_name='purchase_orders')
    status      = models.CharField(max_length=20, choices=PurchaseOrderStatus.choices, default=PurchaseOrderStatus.DRAFT)
    total_paisa = models.PositiveBigIntegerField(default=0)   # integer paisa — never float
    notes       = models.TextField(blank=True)

    def __str__(self):
        return f'PO #{self.pk} — {self.supplier} [{self.status}]'


class GoodsReceived(BaseModel):
    """
    Records a physical receipt event. Call .receive(user, lines) to create
    the corresponding StockMovement(type=production) rows and advance the PO.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='goods_received')
    location       = models.ForeignKey('locations.Location', on_delete=models.PROTECT, related_name='goods_received')
    received_at    = models.DateTimeField()
    received_by    = models.ForeignKey(
                         settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                         related_name='goods_received',
                     )
    # Populated for live-bird POs; null for feed/medicine.
    lot            = models.ForeignKey(
                         'lots.Lot', null=True, blank=True,
                         on_delete=models.PROTECT, related_name='goods_received',
                     )
    notes          = models.TextField(blank=True)

    @transaction.atomic
    def receive(self, user, lines: list) -> list:
        """
        Create StockMovement(type=production) for each received line item.

        lines: list of dicts —
            product    (catalog.Product, required)
            qty_kg     (Decimal, default 0)
            qty_pieces (int, default 0)
            lot        (lots.Lot or None) — per-line override; falls back to self.lot

        Returns the list of created StockMovements.
        Marks the PO as received (all-or-nothing for Phase 1).
        """
        movements = []
        for line in lines:
            m = StockMovement.objects.create(
                product=line['product'],
                location=self.location,
                lot=line.get('lot') or self.lot,
                type=MovementType.PRODUCTION,
                qty_kg=line.get('qty_kg', 0),
                qty_pieces=line.get('qty_pieces', 0),
                ref_id=self.pk,
                user=user,
            )
            movements.append(m)

        self.purchase_order.status = PurchaseOrderStatus.RECEIVED
        self.purchase_order.save(update_fields=['status', 'updated_at'])
        return movements

    def __str__(self):
        return f'GR #{self.pk} — {self.purchase_order} @ {self.location}'
