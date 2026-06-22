"""
Proves: cbms_sync() marks PENDING invoices as SYNCED, respects
CBMS_SYNC_BATCH_SIZE, and leaves already-synced records untouched.
Note: CreditNote has no cbms_status field — the sync stub covers invoices only.
"""
import pytest
from django.test import override_settings
from django.utils import timezone

from apps.billing.models import CbmsStatus, Invoice
from apps.billing.tasks import cbms_sync


# ── Helpers ───────────────────────────────────────────────────────────────────

_counter = 0


def make_invoice(cbms_status=CbmsStatus.PENDING):
    global _counter
    _counter += 1
    return Invoice.objects.create(
        invoice_number=f'INV-{_counter}',
        issued_at=timezone.now(),
        cbms_status=cbms_status,
        total_paisa=10000,
    )


# ── Core behaviour ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_pending_invoice_is_synced():
    inv = make_invoice()
    cbms_sync()
    inv.refresh_from_db()
    assert inv.cbms_status == CbmsStatus.SYNCED


@pytest.mark.django_db
def test_already_synced_invoice_not_touched():
    inv = make_invoice(cbms_status=CbmsStatus.SYNCED)
    result = cbms_sync()
    assert inv.pk not in result['synced_invoices']


@pytest.mark.django_db
def test_result_lists_synced_invoice_ids():
    inv = make_invoice()
    result = cbms_sync()
    assert inv.pk in result['synced_invoices']


@pytest.mark.django_db
@override_settings(CBMS_SYNC_BATCH_SIZE=2)
def test_batch_size_limits_synced_count():
    for _ in range(5):
        make_invoice()
    result = cbms_sync()
    assert len(result['synced_invoices']) == 2
    assert Invoice.objects.filter(cbms_status=CbmsStatus.PENDING).count() == 3


@pytest.mark.django_db
def test_no_pending_returns_empty_list():
    result = cbms_sync()
    assert result['synced_invoices'] == []


@pytest.mark.django_db
def test_multiple_pending_invoices_all_synced():
    invs = [make_invoice() for _ in range(3)]
    result = cbms_sync()
    assert set(result['synced_invoices']) == {inv.pk for inv in invs}
    for inv in invs:
        inv.refresh_from_db()
        assert inv.cbms_status == CbmsStatus.SYNCED
