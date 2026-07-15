import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Gateway(models.TextChoices):
    FONEPAY = 'fonepay', 'Fonepay QR'
    MOCK    = 'mock',    'Mock (test/demo)'
    # Digital payments taken before gateway verification existed. These were never
    # confirmed with any gateway — the cashier typed a reference and the system
    # believed them. Kept, and labelled, rather than deleted or silently blessed.
    LEGACY  = 'legacy',  'Legacy (unverified — pre-dates gateway checks)'


class IntentStatus(models.TextChoices):
    INITIATED = 'initiated', 'Awaiting payment'
    VERIFIED  = 'verified',  'Verified by gateway'
    CONSUMED  = 'consumed',  'Attached to an order'
    FAILED    = 'failed',    'Failed or rejected'
    EXPIRED   = 'expired',   'Expired'


class PaymentIntent(BaseModel):
    """
    A claim on money that has not been proved yet.

    Nothing in the sales ledger may reference an intent until the gateway itself
    confirms it — the customer's phone, the cashier's screen and any callback body
    are all untrusted. `verify()` asks the gateway what happened and is the only
    thing that may move an intent to VERIFIED.

    Lifecycle: initiated → verified → consumed (attached to exactly one Payment).
               initiated → failed / expired.
    """
    gateway      = models.CharField(max_length=20, choices=Gateway.choices)
    status       = models.CharField(
                       max_length=20, choices=IntentStatus.choices, default=IntentStatus.INITIATED,
                   )

    # What we asked the customer to pay. The gateway's reported amount is checked
    # against this and a mismatch is a hard failure — never trust a client-supplied total.
    amount_paisa = models.PositiveBigIntegerField()

    # Our reference, sent to the gateway (Fonepay calls this the PRN). Unique so a
    # gateway response can never be matched to two intents.
    prn          = models.CharField(max_length=64, unique=True, editable=False)

    # The gateway's own transaction id, known only after payment.
    gateway_ref  = models.CharField(max_length=128, null=True, blank=True)

    location     = models.ForeignKey(
                       'locations.Location', on_delete=models.PROTECT, related_name='payment_intents',
                   )
    session      = models.ForeignKey(
                       'sales.CashierSession', null=True, blank=True,
                       on_delete=models.PROTECT, related_name='payment_intents',
                   )
    # Null only for backfilled legacy rows, where no creator was ever recorded.
    created_by   = models.ForeignKey(
                       settings.AUTH_USER_MODEL, null=True, blank=True,
                       on_delete=models.PROTECT, related_name='payment_intents',
                   )

    qr_payload   = models.TextField(blank=True)     # what the customer scans
    raw_response = models.JSONField(null=True, blank=True)   # gateway's verbatim reply, for audit
    verified_at  = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'created_at'], name='pay_intent_status_idx')]

    def save(self, *args, **kwargs):
        if not self.prn:
            self.prn = uuid.uuid4().hex
        super().save(*args, **kwargs)

    @property
    def is_spendable(self) -> bool:
        """Verified, and not already attached to an order."""
        return self.status == IntentStatus.VERIFIED

    def __str__(self):
        return f'{self.get_gateway_display()} {self.amount_paisa}p [{self.status}] prn={self.prn}'
