from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.catalog.models import TaxClass
from apps.core.models import BaseModel

VAT_RATE = Decimal('13') / Decimal('100')


def compute_line_vat(line_total_paisa: int, tax_class: str) -> int:
    """13% VAT in integer paisa; truncates sub-paisa fractions. Returns 0 for exempt lines."""
    if tax_class == TaxClass.TAXABLE:
        return int(Decimal(line_total_paisa) * VAT_RATE)
    return 0


class CbmsStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SYNCED  = 'synced',  'Synced'
    FAILED  = 'failed',  'Failed'


class Invoice(BaseModel):
    """
    Optional — not every Order needs an Invoice (Rule 6).
    Header totals are derived from InvoiceLine rows via recompute_totals().
    Delete is blocked; reversal is done via CreditNote.
    CBMS sync is a stub — cbms_status is set here; IRD API call is Phase 2.
    """
    order    = models.OneToOneField(
        'sales.Order', null=True, blank=True,
        on_delete=models.PROTECT, related_name='invoice',
    )
    customer = models.ForeignKey(
        'partners.Customer', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='invoices',
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    issued_at      = models.DateTimeField()
    exempt_paisa   = models.PositiveBigIntegerField(default=0)
    taxable_paisa  = models.PositiveBigIntegerField(default=0)
    vat_paisa      = models.PositiveBigIntegerField(default=0)
    total_paisa    = models.PositiveBigIntegerField(default=0)
    cbms_status    = models.CharField(
        max_length=10, choices=CbmsStatus.choices, default=CbmsStatus.PENDING,
    )

    def delete(self, *args, **kwargs):
        raise RuntimeError(
            'Invoice rows are immutable and must never be deleted. '
            'Issue a CreditNote to reverse an invoice.'
        )

    def recompute_totals(self) -> None:
        """Rebuild exempt_paisa / taxable_paisa / vat_paisa / total_paisa from lines."""
        exempt = taxable = vat = 0
        for line in self.lines.all():
            if line.tax_class == TaxClass.TAXABLE:
                taxable += line.line_total_paisa
                vat     += line.vat_paisa
            else:
                exempt  += line.line_total_paisa
        self.exempt_paisa  = exempt
        self.taxable_paisa = taxable
        self.vat_paisa     = vat
        self.total_paisa   = exempt + taxable + vat
        self.save(update_fields=['exempt_paisa', 'taxable_paisa', 'vat_paisa', 'total_paisa', 'updated_at'])

    def __str__(self):
        return f'Invoice {self.invoice_number} — {self.total_paisa}p [{self.cbms_status}]'


class InvoiceLine(BaseModel):
    invoice    = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    order_line = models.ForeignKey(
        'sales.OrderLine', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='invoice_lines',
    )
    product    = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='invoice_lines')
    price      = models.ForeignKey('catalog.Price',   on_delete=models.PROTECT, related_name='invoice_lines')
    tax_class        = models.CharField(max_length=10, choices=TaxClass.choices)  # snapshot from Product.tax_class at invoice time
    qty_kg           = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0'))
    qty_pieces       = models.IntegerField(default=0)
    unit_paisa       = models.PositiveIntegerField()
    line_total_paisa = models.PositiveBigIntegerField()
    vat_paisa        = models.PositiveBigIntegerField(default=0)  # compute_line_vat(line_total_paisa, tax_class)

    def __str__(self):
        return f'InvoiceLine #{self.pk}: {self.product} — {self.line_total_paisa}p + {self.vat_paisa}p VAT'


class CreditNote(BaseModel):
    invoice      = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='credit_notes')
    reason       = models.TextField()
    amount_paisa = models.PositiveBigIntegerField()
    issued_at    = models.DateTimeField()
    issued_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True,
        on_delete=models.SET_NULL, related_name='credit_notes',
    )

    def delete(self, *args, **kwargs):
        raise RuntimeError('CreditNote rows are immutable and must never be deleted.')

    def __str__(self):
        return f'CreditNote #{self.pk} → Invoice {self.invoice_id} — {self.amount_paisa}p'
