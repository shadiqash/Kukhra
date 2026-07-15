"""
Invoice header totals must roll up from their lines, and VAT / tax_class must be
derived server-side from the product — never taken from the client.
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.billing.models import Invoice
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='inv_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def taxable_product(db):
    return Product.objects.create(name='Taxable Good', uom=UoM.PIECE, tax_class=TaxClass.TAXABLE)


@pytest.fixture
def exempt_product(db):
    return Product.objects.create(name='Exempt Good', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def taxable_price(db, taxable_product):
    return Price.objects.create(
        product=taxable_product, tier=PriceTier.RETAIL, price_paisa=50000, valid_from='2024-01-01',
    )


@pytest.fixture
def exempt_price(db, exempt_product):
    return Price.objects.create(
        product=exempt_product, tier=PriceTier.RETAIL, price_paisa=30000, valid_from='2024-01-01',
    )


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_header_totals_and_vat_derived(manager, taxable_product, exempt_product, taxable_price, exempt_price):
    inv = api(manager).post('/api/invoices/', {
        'invoice_number': 'REG-001', 'issued_at': timezone.now().isoformat(),
    }, format='json')
    assert inv.status_code == 201
    inv_id = inv.data['id']

    # taxable line — client tries to under-report VAT and mislabel as exempt
    line = api(manager).post('/api/invoice-lines/', {
        'invoice': inv_id, 'product': taxable_product.pk, 'price': taxable_price.pk,
        'tax_class': 'exempt', 'qty_pieces': 2,
        'unit_paisa': 50000, 'line_total_paisa': 100000, 'vat_paisa': 0,
    }, format='json')
    assert line.status_code == 201
    # server overrode both from the product; VAT extracted from the inclusive total
    # 100000 inclusive → vat = 100000 − floor(100000×100/113) = 11505
    assert line.data['tax_class'] == 'taxable'
    assert line.data['vat_paisa'] == 11505

    # exempt line
    api(manager).post('/api/invoice-lines/', {
        'invoice': inv_id, 'product': exempt_product.pk, 'price': exempt_price.pk,
        'qty_kg': '1.000', 'unit_paisa': 30000, 'line_total_paisa': 30000,
    }, format='json')

    check = api(manager).get(f'/api/invoices/{inv_id}/')
    # taxable base = 100000 − 11505 = 88495; exempt = 30000; total reconciles to
    # the inclusive amount 100000 + 30000 = 130000 (VAT not added on top)
    assert check.data['taxable_paisa'] == 88495
    assert check.data['exempt_paisa'] == 30000
    assert check.data['vat_paisa'] == 11505
    assert check.data['total_paisa'] == 130000

    inv_obj = Invoice.objects.get(pk=inv_id)
    assert inv_obj.total_paisa == 130000
