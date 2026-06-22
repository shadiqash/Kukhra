"""
QA — Angle 4: Tax correctness.
VAT is exactly 13% of taxable_paisa using integer truncation.
exempt_paisa + taxable_paisa + vat_paisa == total_paisa always.
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.models import Invoice, InvoiceLine, compute_line_vat
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.locations.models import Counter, Location, LocationType
from apps.accounts.models import Role, User
from apps.sales.models import CashierSession, Order, OrderSource, OrderStatus


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def manager(db):
    return User.objects.create_user(username='tax_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Tax Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Tax Counter')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='tax_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )


@pytest.fixture
def product_exempt(db):
    return Product.objects.create(name='Tax Exempt Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def product_taxable(db):
    return Product.objects.create(name='Tax Taxable Meat', uom=UoM.KG, tax_class=TaxClass.TAXABLE)


@pytest.fixture
def price_exempt(db, product_exempt):
    return Price.objects.create(
        product=product_exempt, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )


@pytest.fixture
def price_taxable(db, product_taxable):
    return Price.objects.create(
        product=product_taxable, tier=PriceTier.RETAIL,
        price_paisa=100000, valid_from='2024-01-01',
    )


def make_order(outlet, session):
    return Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=0,
    )


def make_invoice(order, number):
    return Invoice.objects.create(
        order=order, invoice_number=number, issued_at=timezone.now(),
    )


def add_line(invoice, product, price, line_total_paisa, tax_class):
    vat = compute_line_vat(line_total_paisa, tax_class)
    return InvoiceLine.objects.create(
        invoice=invoice, product=product, price=price,
        tax_class=tax_class, qty_kg=Decimal('1.000'), qty_pieces=0,
        unit_paisa=line_total_paisa, line_total_paisa=line_total_paisa, vat_paisa=vat,
    )


# ── All-exempt invoice ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_all_exempt_invoice_zero_vat(outlet, session, product_exempt, price_exempt):
    order = make_order(outlet, session)
    inv = make_invoice(order, 'TAX-EXEMPT-001')
    add_line(inv, product_exempt, price_exempt, 75000, TaxClass.EXEMPT)
    inv.recompute_totals()
    inv.refresh_from_db()

    assert inv.vat_paisa == 0
    assert inv.taxable_paisa == 0
    assert inv.exempt_paisa == 75000
    assert inv.total_paisa == inv.exempt_paisa


# ── All-taxable invoice ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_all_taxable_invoice_vat_is_13_percent(outlet, session, product_taxable, price_taxable):
    order = make_order(outlet, session)
    inv = make_invoice(order, 'TAX-TAXABLE-001')
    line_total = 100000
    add_line(inv, product_taxable, price_taxable, line_total, TaxClass.TAXABLE)
    inv.recompute_totals()
    inv.refresh_from_db()

    expected_vat = int(Decimal(line_total) * Decimal('13') / Decimal('100'))
    assert inv.vat_paisa == expected_vat
    assert inv.taxable_paisa == line_total
    assert inv.exempt_paisa == 0
    assert inv.total_paisa == line_total + expected_vat


# ── Mixed invoice ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mixed_invoice_totals_are_correct(
    outlet, session, product_exempt, price_exempt, product_taxable, price_taxable
):
    order = make_order(outlet, session)
    inv = make_invoice(order, 'TAX-MIXED-001')
    add_line(inv, product_exempt,  price_exempt,  75000,  TaxClass.EXEMPT)
    add_line(inv, product_taxable, price_taxable, 100000, TaxClass.TAXABLE)
    inv.recompute_totals()
    inv.refresh_from_db()

    assert inv.exempt_paisa == 75000
    assert inv.taxable_paisa == 100000
    assert inv.vat_paisa == int(Decimal('100000') * Decimal('13') / Decimal('100'))
    assert inv.total_paisa == inv.exempt_paisa + inv.taxable_paisa + inv.vat_paisa


# ── Integer truncation — no rounding leaks ───────────────────────────────────

@pytest.mark.django_db
def test_vat_truncates_fractional_paisa(outlet, session, product_taxable, price_taxable):
    """
    100001 paisa × 13% = 13000.13 → truncate to 13000 (not round to 13001).
    """
    order = make_order(outlet, session)
    inv = make_invoice(order, 'TAX-TRUNC-001')
    line_total = 100001
    add_line(inv, product_taxable, price_taxable, line_total, TaxClass.TAXABLE)
    inv.recompute_totals()
    inv.refresh_from_db()

    exact_vat = int(Decimal(line_total) * Decimal('13') / Decimal('100'))
    assert inv.vat_paisa == exact_vat
    assert inv.vat_paisa == 13000  # truncates, not rounds


@pytest.mark.django_db
def test_compute_line_vat_exempt_always_zero():
    assert compute_line_vat(999999, TaxClass.EXEMPT) == 0


@pytest.mark.django_db
def test_compute_line_vat_taxable_uses_integer_math():
    # 77777 × 0.13 = 10111.01 → truncates to 10111
    result = compute_line_vat(77777, TaxClass.TAXABLE)
    assert result == int(Decimal('77777') * Decimal('13') / Decimal('100'))
    assert isinstance(result, int)


# ── Invariant: exempt + taxable + vat == total ────────────────────────────────

@pytest.mark.django_db
def test_total_paisa_invariant_multi_line(
    outlet, session, product_exempt, price_exempt, product_taxable, price_taxable
):
    order = make_order(outlet, session)
    inv = make_invoice(order, 'TAX-INVARIANT-001')
    # Three lines of mixed types
    for total, tax in [(50000, TaxClass.EXEMPT), (80000, TaxClass.TAXABLE), (30000, TaxClass.TAXABLE)]:
        add_line(inv, product_taxable if tax == TaxClass.TAXABLE else product_exempt,
                 price_taxable if tax == TaxClass.TAXABLE else price_exempt,
                 total, tax)
    inv.recompute_totals()
    inv.refresh_from_db()

    assert inv.total_paisa == inv.exempt_paisa + inv.taxable_paisa + inv.vat_paisa
