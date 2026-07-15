"""
Gateway adapter interface.

Every gateway answers two questions and nothing else:
  - create_qr(intent)   → what should the customer scan?
  - fetch_status(intent) → did they actually pay, and how much?

fetch_status must talk to the gateway. It may never derive its answer from
anything the client sent us — that is the whole point of the abstraction.
"""
from dataclasses import dataclass, field


class GatewayError(RuntimeError):
    """The gateway could not be reached or returned something unusable."""


@dataclass(frozen=True)
class QrPayload:
    qr_string: str
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GatewayStatus:
    """
    The gateway's verdict.

    paid          — the gateway says this reference is settled.
    amount_paisa  — what the gateway says was actually paid. Compared against the
                    intent; a mismatch is rejected, never reconciled.
    gateway_ref   — the gateway's transaction id.
    """
    paid: bool
    amount_paisa: int | None
    gateway_ref: str | None
    raw: dict = field(default_factory=dict)
    failure_reason: str = ''


class PaymentGateway:
    name: str

    def create_qr(self, intent) -> QrPayload:
        raise NotImplementedError

    def fetch_status(self, intent) -> GatewayStatus:
        raise NotImplementedError
