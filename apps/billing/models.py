from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from apps.catalog.models import TaxClass
from apps.core.models import BaseModel

VAT_RATE = Decimal('13') / Decimal('100')


def compute_line_vat(line_total_paisa: int, tax_class: str) -> int:
    """
    VAT component of a VAT-INCLUSIVE line total, in integer paisa.

    Shelf prices already contain the 13% VAT (Nepal retail norm), so VAT is
    *extracted*, never added on top:
        base = floor(line_total × 100 / 113)
        vat  = line_total − base
    A Rs 100 (10000 paisa) taxable line → base 8849, vat 1151. Exempt lines have
    no VAT. Extracting (not adding) keeps the order total equal to the shelf price
    the customer actually pays.
    """
    if tax_class == TaxClass.TAXABLE:
        base = line_total_paisa * 100 // 113
        return line_total_paisa - base
    return 0


class CbmsStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SYNCED  = 'synced',  'Synced'
    FAILED  = 'failed',  'Failed'


class InvoiceSequence(models.Model):
    """
    Single-row counter behind server-side invoice numbering. A tax invoice
    number must be sequential and gap-averse, and must never be chosen by the
    client — IRD/CBMS reconciles against the sequence. Locked with
    select_for_update so two simultaneous invoices cannot mint the same number.
    """
    next_number = models.PositiveBigIntegerField(default=1)


def next_invoice_number() -> str:
    """
    Reserve and return the next invoice number (format INV-000001). The
    prefix / fiscal-year reset scheme is finalized with the real CBMS
    integration in Phase 2; the counter skips past any numbers already taken
    by pre-existing (historically client-supplied) invoices.
    """
    with transaction.atomic():
        seq, _ = InvoiceSequence.objects.select_for_update().get_or_create(pk=1)
        n = seq.next_number
        while Invoice.objects.filter(invoice_number=f'INV-{n:06d}').exists():
            n += 1
        seq.next_number = n + 1
        seq.save(update_fields=['next_number'])
        return f'INV-{n:06d}'


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
        """
        Rebuild exempt_paisa / taxable_paisa / vat_paisa / total_paisa from lines.

        Prices are VAT-inclusive, so a taxable line's line_total_paisa already
        contains its VAT. `taxable_paisa` is the ex-VAT base (line total − VAT),
        matching the IRD invoice presentation where Taxable + VAT = the inclusive
        amount. total_paisa therefore equals the sum of all inclusive line totals —
        the same figure as the order the customer paid, never VAT double-counted.
        """
        exempt = taxable = vat = 0
        for line in self.lines.all():
            if line.tax_class == TaxClass.TAXABLE:
                taxable += line.line_total_paisa - line.vat_paisa   # ex-VAT base
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
