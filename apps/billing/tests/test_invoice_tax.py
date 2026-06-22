"""
Proves:
- exempt lines produce vat_paisa = 0
- taxable lines produce vat_paisa = int(line_total_paisa * 0.13)
- Invoice.recompute_totals() correctly buckets lines into exempt/taxable/vat header sums
- Invoice.delete() and CreditNote.delete() raise (immutability guard)
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.models import CreditNote, Invoice, InvoiceLine, compute_line_vat
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.partners.models import Customer, CustomerType


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def customer(db):
    return Customer.objects.create(name='Test Customer', type=CustomerType.RETAIL)


@pytest.fixture
def exempt_product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def taxable_product(db):
    return Product.objects.create(name='Processed Wings', uom=UoM.KG, tax_class=TaxClass.TAXABLE)


@pytest.fixture
def exempt_price(db, exempt_product):
    return Price.objects.create(
        product=exempt_product, tier=PriceTier.RETAIL,
        price_paisa=70000, valid_from='2024-01-01',
    )


@pytest.fixture
def taxable_price(db, taxable_product):
    return Price.objects.create(
        product=taxable_product, tier=PriceTier.RETAIL,
        price_paisa=80000, valid_from='2024-01-01',
    )


@pytest.fixture
def invoice(db, customer):
    return Invoice.objects.create(
        customer=customer,
        invoice_number='INV-0001',
        issued_at=timezone.now(),
    )


# ── compute_line_vat unit tests ───────────────────────────────────────────────

def test_exempt_line_vat_is_zero():
    assert compute_line_vat(100000, TaxClass.EXEMPT) == 0


def test_taxable_line_vat_is_13_percent():
    assert compute_line_vat(100000, TaxClass.TAXABLE) == 13000


def test_taxable_vat_truncates_sub_paisa():
    # 10001 * 0.13 = 1300.13 → truncates to 1300
    assert compute_line_vat(10001, TaxClass.TAXABLE) == 1300


def test_zero_line_total_gives_zero_vat():
    assert compute_line_vat(0, TaxClass.TAXABLE) == 0


# ── InvoiceLine integration tests ────────────────────────────────────────────

@pytest.mark.django_db
def test_exempt_invoice_line_stores_zero_vat(invoice, exempt_product, exempt_price):
    line_total = 140000  # 2kg × 70000p
    vat = compute_line_vat(line_total, TaxClass.EXEMPT)
    line = InvoiceLine.objects.create(
        invoice=invoice, product=exempt_product, price=exempt_price,
        tax_class=TaxClass.EXEMPT,
        qty_kg=Decimal('2.000'), unit_paisa=70000,
        line_total_paisa=line_total, vat_paisa=vat,
    )
    assert line.vat_paisa == 0


@pytest.mark.django_db
def test_taxable_invoice_line_stores_13_percent_vat(invoice, taxable_product, taxable_price):
    line_total = 80000  # 1kg × 80000p
    vat = compute_line_vat(line_total, TaxClass.TAXABLE)
    line = InvoiceLine.objects.create(
        invoice=invoice, product=taxable_product, price=taxable_price,
        tax_class=TaxClass.TAXABLE,
        qty_kg=Decimal('1.000'), unit_paisa=80000,
        line_total_paisa=line_total, vat_paisa=vat,
    )
    assert line.vat_paisa == 10400  # 80000 * 0.13


# ── Invoice.recompute_totals() ────────────────────────────────────────────────

@pytest.mark.django_db
def test_recompute_totals_buckets_exempt_and_taxable(
    invoice, exempt_product, exempt_price, taxable_product, taxable_price
):
    exempt_total  = 140000   # exempt line
    taxable_total = 80000    # taxable line
    exempt_vat    = compute_line_vat(exempt_total,  TaxClass.EXEMPT)
    taxable_vat   = compute_line_vat(taxable_total, TaxClass.TAXABLE)

    InvoiceLine.objects.create(
        invoice=invoice, product=exempt_product, price=exempt_price,
        tax_class=TaxClass.EXEMPT,
        qty_kg=Decimal('2.000'), unit_paisa=70000,
        line_total_paisa=exempt_total, vat_paisa=exempt_vat,
    )
    InvoiceLine.objects.create(
        invoice=invoice, product=taxable_product, price=taxable_price,
        tax_class=TaxClass.TAXABLE,
        qty_kg=Decimal('1.000'), unit_paisa=80000,
        line_total_paisa=taxable_total, vat_paisa=taxable_vat,
    )

    invoice.recompute_totals()
    invoice.refresh_from_db()

    assert invoice.exempt_paisa  == exempt_total
    assert invoice.taxable_paisa == taxable_total
    assert invoice.vat_paisa     == taxable_vat          # 10400
    assert invoice.total_paisa   == exempt_total + taxable_total + taxable_vat


@pytest.mark.django_db
def test_recompute_totals_all_exempt(invoice, exempt_product, exempt_price):
    InvoiceLine.objects.create(
        invoice=invoice, product=exempt_product, price=exempt_price,
        tax_class=TaxClass.EXEMPT,
        qty_kg=Decimal('3.000'), unit_paisa=70000,
        line_total_paisa=210000, vat_paisa=0,
    )
    invoice.recompute_totals()
    invoice.refresh_from_db()
    assert invoice.vat_paisa     == 0
    assert invoice.taxable_paisa == 0
    assert invoice.total_paisa   == 210000


# ── Immutability guards ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_invoice_delete_raises(invoice):
    with pytest.raises(RuntimeError, match='immutable'):
        invoice.delete()


@pytest.mark.django_db
def test_credit_note_delete_raises(invoice):
    cn = CreditNote.objects.create(
        invoice=invoice, reason='Test', amount_paisa=10000, issued_at=timezone.now(),
    )
    with pytest.raises(RuntimeError, match='immutable'):
        cn.delete()


# ── CBMS stub default ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_invoice_cbms_status_defaults_to_pending(invoice):
    from apps.billing.models import CbmsStatus
    assert invoice.cbms_status == CbmsStatus.PENDING
