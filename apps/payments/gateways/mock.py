"""
Mock gateway — for tests and for demoing the QR flow without live merchant credentials.

It is deliberately controllable: a test (or a demo operator) decides what the
"gateway" reports, so the verification logic can be exercised against a gateway
that lies — reporting the wrong amount, or reporting unpaid.

Never enable this in production. `settings.PAYMENT_GATEWAYS` gates it.
"""
from .base import GatewayStatus, PaymentGateway, QrPayload

# prn → what the gateway will claim on the next fetch_status().
_LEDGER: dict[str, GatewayStatus] = {}


def settle(prn: str, amount_paisa: int, gateway_ref: str = 'MOCK-TXN'):
    """Pretend the customer paid this amount."""
    _LEDGER[prn] = GatewayStatus(
        paid=True, amount_paisa=amount_paisa, gateway_ref=gateway_ref, raw={'paymentStatus': 'success'},
    )


def fail(prn: str, reason: str = 'cancelled by user'):
    _LEDGER[prn] = GatewayStatus(
        paid=False, amount_paisa=None, gateway_ref=None,
        raw={'paymentStatus': 'failed'}, failure_reason=reason,
    )


def reset():
    _LEDGER.clear()


class MockGateway(PaymentGateway):
    name = 'mock'

    def create_qr(self, intent) -> QrPayload:
        return QrPayload(qr_string=f'MOCKQR:{intent.prn}:{intent.amount_paisa}', raw={'mock': True})

    def fetch_status(self, intent) -> GatewayStatus:
        # Unpaid until someone settles it — the default is "no money arrived".
        return _LEDGER.get(
            intent.prn,
            GatewayStatus(paid=False, amount_paisa=None, gateway_ref=None,
                          raw={'paymentStatus': 'pending'}, failure_reason='awaiting payment'),
        )
