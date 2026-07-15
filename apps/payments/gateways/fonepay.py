"""
Fonepay dynamic-QR adapter.

Two calls:
  QR generation — DV = HMAC_SHA512(secret, "amount,prn,merchantCode,remarks1,remarks2")
  Status check  — DV = HMAC_SHA512(secret, "prn,merchantCode")

The status call is authoritative. We never mark money received because a callback
said so, or because the cashier's screen said so — we ask Fonepay directly, keyed
on our own PRN, and compare the amount they report against the amount we asked for.

The secret never leaves the server.
"""
import base64
import hashlib
import hmac
import logging
from decimal import Decimal

import requests
from django.conf import settings

from .base import GatewayError, GatewayStatus, PaymentGateway, QrPayload

logger = logging.getLogger(__name__)

TIMEOUT = 15   # seconds; a cashier is standing at a till waiting for this


def _config():
    cfg = getattr(settings, 'FONEPAY', {}) or {}
    missing = [k for k in ('MERCHANT_CODE', 'USERNAME', 'PASSWORD', 'SECRET_KEY', 'BASE_URL') if not cfg.get(k)]
    if missing:
        raise GatewayError(f'Fonepay is not configured: missing {", ".join(missing)}.')
    return cfg


def _dv(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha512).hexdigest()


def _rupees(paisa: int) -> str:
    """Fonepay talks in rupees. Convert exactly — Decimal, never float."""
    return str((Decimal(paisa) / Decimal(100)).quantize(Decimal('0.01')))


def _paisa(rupees) -> int:
    return int((Decimal(str(rupees)) * 100).to_integral_value())


class FonepayGateway(PaymentGateway):
    name = 'fonepay'

    def create_qr(self, intent) -> QrPayload:
        cfg = _config()
        amount = _rupees(intent.amount_paisa)
        remarks1 = f'Everfresh {intent.location_id}'
        remarks2 = intent.prn[:8]

        message = f'{amount},{intent.prn},{cfg["MERCHANT_CODE"]},{remarks1},{remarks2}'
        payload = {
            'amount': amount,
            'remarks1': remarks1,
            'remarks2': remarks2,
            'prn': intent.prn,
            'merchantCode': cfg['MERCHANT_CODE'],
            'dataValidation': _dv(cfg['SECRET_KEY'], message),
            'username': cfg['USERNAME'],
            'password': cfg['PASSWORD'],
        }
        data = self._post('thirdPartyDynamicQrDownload', payload, cfg)

        qr = data.get('qrMessage') or data.get('qrString') or ''
        if not qr:
            raise GatewayError('Fonepay returned no QR payload.')
        return QrPayload(qr_string=qr, raw=data)

    def fetch_status(self, intent) -> GatewayStatus:
        cfg = _config()
        message = f'{intent.prn},{cfg["MERCHANT_CODE"]}'
        payload = {
            'prn': intent.prn,
            'merchantCode': cfg['MERCHANT_CODE'],
            'dataValidation': _dv(cfg['SECRET_KEY'], message),
            'username': cfg['USERNAME'],
            'password': cfg['PASSWORD'],
        }
        data = self._post('thirdPartyDynamicQrGetStatus', payload, cfg)

        # Fonepay reports success in `paymentStatus`; anything else is not money.
        paid = str(data.get('paymentStatus', '')).lower() == 'success'
        amount = data.get('amount')
        return GatewayStatus(
            paid=paid,
            amount_paisa=_paisa(amount) if amount not in (None, '') else None,
            gateway_ref=data.get('fonepayTraceId') or data.get('traceId'),
            raw=data,
            failure_reason='' if paid else str(data.get('paymentStatus') or 'not settled'),
        )

    def _post(self, path: str, payload: dict, cfg: dict) -> dict:
        auth = base64.b64encode(f'{cfg["USERNAME"]}:{cfg["PASSWORD"]}'.encode()).decode()
        url = f'{cfg["BASE_URL"].rstrip("/")}/{path}'
        try:
            res = requests.post(
                url, json=payload, timeout=TIMEOUT,
                headers={'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'},
            )
        except requests.RequestException as exc:
            logger.warning('Fonepay %s unreachable: %s', path, exc)
            raise GatewayError('Could not reach Fonepay. Take another payment method.') from exc

        if res.status_code >= 400:
            logger.warning('Fonepay %s returned %s: %s', path, res.status_code, res.text[:400])
            raise GatewayError(f'Fonepay rejected the request ({res.status_code}).')

        try:
            return res.json()
        except ValueError as exc:
            raise GatewayError('Fonepay returned a malformed response.') from exc
