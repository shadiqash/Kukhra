from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import BaseModel
from apps.inventory.models import MovementType, StockMovement


class OrderSource(models.TextChoices):
    COUNTER   = 'counter',   'Counter'
    APP       = 'app',       'App'
    PHONE     = 'phone',     'Phone'
    WHOLESALE = 'wholesale', 'Wholesale'


class OrderStatus(models.TextChoices):
    PENDING   = 'pending',   'Pending'
    FULFILLED = 'fulfilled', 'Fulfilled'
    CANCELLED = 'cancelled', 'Cancelled'


class PaymentMethod(models.TextChoices):
    CASH   = 'cash',   'Cash'
    CARD   = 'card',   'Card'
    ESEWA  = 'esewa',  'eSewa'
    KHALTI = 'khalti', 'Khalti'


class CashierSession(BaseModel):
    counter               = models.ForeignKey('locations.Counter', on_delete=models.PROTECT, related_name='sessions')
    cashier               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cashier_sessions')
    opening_float_paisa   = models.PositiveBigIntegerField()
    closing_counted_paisa = models.PositiveBigIntegerField(null=True, blank=True)
    opened_at             = models.DateTimeField()
    closed_at             = models.DateTimeField(null=True, blank=True)

    def close(self, closing_counted_paisa: int) -> None:
        if self.closed_at is not None:
            raise RuntimeError(f'CashierSession #{self.pk} is already closed.')
        self.closing_counted_paisa = closing_counted_paisa
        self.closed_at = timezone.now()
        self.save(update_fields=['closing_counted_paisa', 'closed_at', 'updated_at'])

    def __str__(self):
        return f'Session #{self.pk} — {self.cashier} @ {self.counter} ({self.opened_at:%Y-%m-%d})'


class Order(BaseModel):
    """
    Single entry point for ALL sales regardless of channel (counter / app / phone / wholesale).
    Invoice is optional — only generated when a tax invoice is needed (step 8).
    """
    customer           = models.ForeignKey(
                             'partners.Customer', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='orders',
                         )
    fulfilled_location = models.ForeignKey('locations.Location', on_delete=models.PROTECT, related_name='orders')
    session            = models.ForeignKey(
                             CashierSession, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='orders',
                         )
    source             = models.CharField(max_length=20, choices=OrderSource.choices)
    status             = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_paisa        = models.PositiveBigIntegerField(default=0)

    @transaction.atomic
    def fulfill(self, user) -> None:
        """
        Marks the order fulfilled and creates one StockMovement(type=sale) per OrderLine.
        Each movement carries a negative qty — stock leaves the fulfilled_location.
        ref_id on the movements points back to this Order's pk.

        Lot is intentionally left null on sale movements for Phase 1.
        FIFO/LIFO lot allocation belongs in Phase 2.
        """
        if self.status != OrderStatus.PENDING:
            raise RuntimeError(
                f'Order #{self.pk} is {self.status!r}; only pending orders can be fulfilled.'
            )
        for line in self.lines.select_related('product'):
            StockMovement.objects.create(
                product=line.product,
                location=self.fulfilled_location,
                lot=None,
                type=MovementType.SALE,
                qty_kg=-line.qty_kg,
                qty_pieces=-line.qty_pieces,
                ref_id=self.pk,
                user=user,
            )
        self.status = OrderStatus.FULFILLED
        self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f'Order #{self.pk} [{self.source} / {self.status}] {self.total_paisa}p'


class OrderLine(BaseModel):
    order            = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='lines')
    product          = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='order_lines')
    price            = models.ForeignKey('catalog.Price',   on_delete=models.PROTECT, related_name='order_lines')
    qty_kg           = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0'))
    qty_pieces       = models.IntegerField(default=0)
    line_total_paisa = models.PositiveBigIntegerField()    # stored snapshot; caller computes from price × qty

    def __str__(self):
        return f'Line #{self.pk}: {self.product} ×{self.qty_kg}kg/{self.qty_pieces}pc = {self.line_total_paisa}p'


class Payment(BaseModel):
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    method       = models.CharField(max_length=20, choices=PaymentMethod.choices)
    amount_paisa = models.PositiveBigIntegerField()
    ref          = models.TextField(null=True, blank=True)   # external transaction ref (eSewa ID, card slip, etc.)

    def __str__(self):
        return f'Payment #{self.pk}: {self.method} {self.amount_paisa}p → Order #{self.order_id}'


class DailySalesRollup(models.Model):
    """
    Append-only nightly aggregate written by the nightly_rollup Celery task.
    One row per calendar date.  No BaseModel — no updated_at, no soft-delete.
    """
    date                 = models.DateField(unique=True)
    order_count          = models.PositiveIntegerField(default=0)
    total_revenue_paisa  = models.PositiveBigIntegerField(default=0)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'DailySalesRollup {self.date}: {self.order_count} orders, {self.total_revenue_paisa}p'
