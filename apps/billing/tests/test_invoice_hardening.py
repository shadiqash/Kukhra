"""
Invoice/credit-note hardening (review finding H4): tax documents are numbered
and timestamped by the server, freeze once submitted to CBMS, and must be
arithmetically consistent.
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.billing.models import CbmsStatus, Invoice, next_invoice_number
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='inv_hard_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL, price_paisa=75000, valid_from='2026-01-01',
    )


def api(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.mark.django_db
def test_invoice_number_is_server_generated(manager):
    res = api(manager).post('/api/invoices/', {
        'invoice_number': 'FAKE-999', 'issued_at': '2020-01-01T00:00:00Z',
    }, format='json')
    assert res.status_code == 201, res.data
    assert res.data['invoice_number'] != 'FAKE-999'
    assert res.data['invoice_number'].startswith('INV-')
    # issued_at was not backdated to 2020
    assert res.data['issued_at'][:4] == str(timezone.now().year)


@pytest.mark.django_db
def test_invoice_numbers_are_sequential(manager):
    first = api(manager).post('/api/invoices/', {}, format='json').data['invoice_number']
    second = api(manager).post('/api/invoices/', {}, format='json').data['invoice_number']
    assert int(second.split('-')[1]) == int(first.split('-')[1]) + 1


@pytest.mark.django_db
def test_sequence_skips_existing_numbers(manager):
    # A legacy invoice already holds the number the counter would mint next.
    nxt = next_invoice_number()          # e.g. INV-000001
    n = int(nxt.split('-')[1])
    Invoice.objects.create(invoice_number=f'INV-{n + 1:06d}', issued_at=timezone.now())
    res = api(manager).post('/api/invoices/', {}, format='json')
    assert res.status_code == 201
    assert res.data['invoice_number'] == f'INV-{n + 2:06d}'


@pytest.mark.django_db
def test_lines_frozen_after_cbms_sync(manager, product, price):
    inv = Invoice.objects.create(
        invoice_number='INV-SYNCED', issued_at=timezone.now(), cbms_status=CbmsStatus.SYNCED,
    )
    res = api(manager).post('/api/invoice-lines/', {
        'invoice': inv.pk, 'product': product.pk, 'price': price.pk,
        'qty_kg': '1.000', 'unit_paisa': 75000, 'line_total_paisa': 75000,
    }, format='json')
    assert res.status_code == 400
    assert 'frozen' in str(res.data)


@pytest.mark.django_db
def test_line_arithmetic_enforced(manager, product, price):
    inv = Invoice.objects.create(invoice_number='INV-ARITH', issued_at=timezone.now())
    res = api(manager).post('/api/invoice-lines/', {
        'invoice': inv.pk, 'product': product.pk, 'price': price.pk,
        'qty_kg': '2.000', 'unit_paisa': 75000, 'line_total_paisa': 1,
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_line_unit_must_match_price(manager, product, price):
    inv = Invoice.objects.create(invoice_number='INV-UNIT', issued_at=timezone.now())
    res = api(manager).post('/api/invoice-lines/', {
        'invoice': inv.pk, 'product': product.pk, 'price': price.pk,
        'qty_kg': '1.000', 'unit_paisa': 10, 'line_total_paisa': 10,
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_credit_note_stamped_and_capped(manager):
    inv = Invoice.objects.create(
        invoice_number='INV-CN', issued_at=timezone.now(), total_paisa=100000,
    )
    res = api(manager).post('/api/credit-notes/', {
        'invoice': inv.pk, 'reason': 'returned goods', 'amount_paisa': 60000,
        'issued_by': 99999,   # ignored — stamped from the request
    }, format='json')
    assert res.status_code == 201, res.data
    assert res.data['issued_by'] == manager.pk

    # A second note may not push cumulative credit past the invoice total.
    res = api(manager).post('/api/credit-notes/', {
        'invoice': inv.pk, 'reason': 'more returns', 'amount_paisa': 60000,
    }, format='json')
    assert res.status_code == 400
    assert 'exceed' in str(res.data)
