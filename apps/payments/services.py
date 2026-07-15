"""
Verification. The only place an intent may become VERIFIED.
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .gateways.base import GatewayError, PaymentGateway
from .gateways.fonepay import FonepayGateway
from .gateways.mock import MockGateway
from .models import Gateway, IntentStatus, PaymentIntent

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[PaymentGateway]] = {
    Gateway.FONEPAY: FonepayGateway,
    Gateway.MOCK: MockGateway,
}


def get_gateway(name: str) -> PaymentGateway:
    enabled = getattr(settings, 'PAYMENT_GATEWAYS', [Gateway.FONEPAY])
    if name not in enabled:
        raise GatewayError(f'Payment gateway {name!r} is not enabled.')
    return _REGISTRY[name]()


@transaction.atomic
def verify_intent(intent: PaymentIntent) -> PaymentIntent:
    """
    Ask the gateway what actually happened, and record it.

    Three things make this safe:

    1. The gateway is asked directly, keyed on our own PRN. No callback body, no
       client field, and no cashier action can assert that money arrived.
    2. The amount the gateway reports is compared against the amount we asked for.
       A mismatch is a hard failure — we never reconcile down to what was paid,
       because that is exactly how an underpayment becomes a completed sale.
    3. The intent row is locked and re-read. A verified intent is never re-verified,
       so a duplicated webhook or a double-tapped poll cannot move it twice.
    """
    intent = PaymentIntent.objects.select_for_update().get(pk=intent.pk)

    # Terminal states are terminal. Re-asking cannot resurrect or double-count them.
    if intent.status in (IntentStatus.VERIFIED, IntentStatus.CONSUMED,
                         IntentStatus.FAILED, IntentStatus.EXPIRED):
        return intent

    status = get_gateway(intent.gateway).fetch_status(intent)
    intent.raw_response = status.raw

    if not status.paid:
        # Still pending is not a failure — the customer may not have scanned yet.
        intent.failure_reason = status.failure_reason
        intent.save(update_fields=['raw_response', 'failure_reason', 'updated_at'])
        return intent

    if status.amount_paisa != intent.amount_paisa:
        # The gateway settled a different amount than we asked for. Do not accept it.
        intent.status = IntentStatus.FAILED
        intent.failure_reason = (
            f'Amount mismatch: asked {intent.amount_paisa} paisa, '
            f'gateway settled {status.amount_paisa} paisa.'
        )
        intent.gateway_ref = status.gateway_ref
        intent.save(update_fields=['status', 'failure_reason', 'gateway_ref',
                                   'raw_response', 'updated_at'])
        logger.error('PAYMENT AMOUNT MISMATCH prn=%s %s', intent.prn, intent.failure_reason)
        return intent

    intent.status = IntentStatus.VERIFIED
    intent.gateway_ref = status.gateway_ref
    intent.verified_at = timezone.now()
    intent.failure_reason = ''
    intent.save(update_fields=['status', 'gateway_ref', 'verified_at',
                               'failure_reason', 'raw_response', 'updated_at'])
    return intent


def consume_intent(intent: PaymentIntent, *, amount_paisa: int) -> PaymentIntent:
    """
    Spend a verified intent on exactly one Payment.

    Called from inside the checkout transaction, with the row locked, so two orders
    cannot claim the same payment: the second finds it already CONSUMED. Without this
    a single Rs 5,000 QR scan could pay for an unlimited number of baskets.
    """
    intent = PaymentIntent.objects.select_for_update().get(pk=intent.pk)

    if intent.status == IntentStatus.CONSUMED:
        raise ValueError(f'Payment {intent.prn} has already been used on another order.')
    if intent.status != IntentStatus.VERIFIED:
        raise ValueError(f'Payment {intent.prn} is not verified ({intent.status}).')
    if intent.amount_paisa != amount_paisa:
        raise ValueError(
            f'Payment {intent.prn} is for {intent.amount_paisa} paisa, '
            f'but the order line claims {amount_paisa} paisa.'
        )

    intent.status = IntentStatus.CONSUMED
    intent.save(update_fields=['status', 'updated_at'])
    return intent
