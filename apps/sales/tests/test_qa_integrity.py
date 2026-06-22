"""
QA — Angle 1: Data integrity.
Verifies current_stock == sum(movements) after every movement type,
and that StockMovement / Price / Invoice are immutable via the API.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.billing.models import Invoice
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement, StockTransfer
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import (
    CashierSession, Order, OrderLine, OrderSource, OrderStatus, Payment, PaymentMethod,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def manager(db):
    return User.objects.create_user(username='qa_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='QA WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='QA Outlet', type=LocationType.OUTLET)


@pytest.fixture
def product(db):
    return Product.objects.create(name='QA Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='QA Counter')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='qa_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def net_stock(product, location):
    return current_stock(product.pk, location.pk)['qty_kg']


def add_movement(product, location, user, type_, qty_kg, ref_id=None):
    return StockMovement.objects.create(
        product=product, location=location,
        type=type_, qty_kg=Decimal(str(qty_kg)),
        ref_id=ref_id, user=user,
    )


# ── Stock invariant after each movement type ──────────────────────────────────

@pytest.mark.django_db
def test_stock_invariant_after_sale(warehouse, product, manager, session, outlet, price):
    add_movement(product, warehouse, manager, MovementType.PRODUCTION, '20.000')
    order = Order.objects.create(
        fulfilled_location=warehouse, session=session,
        source=OrderSource.COUNTER, total_paisa=0,
    )
    OrderLine.objects.create(
        order=order, product=product, price=price,
        qty_kg=Decimal('5.000'), qty_pieces=0, line_total_paisa=375000,
    )
    order.fulfill(user=manager)

    assert net_stock(product, warehouse) == Decimal('15.000')


@pytest.mark.django_db
def test_stock_invariant_after_return(warehouse, product, manager):
    add_movement(product, warehouse, manager, MovementType.PRODUCTION, '10.000')
    add_movement(product, warehouse, manager, MovementType.SALE, '-8.000')
    add_movement(product, warehouse, manager, MovementType.RETURN, '3.000')

    assert net_stock(product, warehouse) == Decimal('5.000')


@pytest.mark.django_db
def test_stock_invariant_after_wastage(warehouse, product, manager):
    add_movement(product, warehouse, manager, MovementType.PRODUCTION, '10.000')
    add_movement(product, warehouse, manager, MovementType.WASTAGE, '-2.500')

    assert net_stock(product, warehouse) == Decimal('7.500')


@pytest.mark.django_db
def test_stock_invariant_after_transfer(warehouse, outlet, product, manager):
    add_movement(product, warehouse, manager, MovementType.PRODUCTION, '20.000')
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    add_movement(product, warehouse, manager, MovementType.TRANSFER, '-8.000', ref_id=transfer.pk)
    transfer.confirm_receipt(user=manager)

    assert net_stock(product, warehouse) == Decimal('12.000')
    assert net_stock(product, outlet) == Decimal('8.000')


# ── Immutability via API ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_patch_stock_movement_blocked(warehouse, product, manager):
    m = add_movement(product, warehouse, manager, MovementType.PRODUCTION, '10.000')
    resp = api(manager).patch(f'/api/movements/{m.pk}/', {'qty_kg': '99.000'}, format='json')
    assert resp.status_code in (403, 404, 405)


@pytest.mark.django_db
def test_delete_stock_movement_blocked(warehouse, product, manager):
    m = add_movement(product, warehouse, manager, MovementType.PRODUCTION, '10.000')
    resp = api(manager).delete(f'/api/movements/{m.pk}/')
    assert resp.status_code in (403, 404, 405)


@pytest.mark.django_db
def test_patch_price_blocked(price, manager):
    resp = api(manager).patch(f'/api/prices/{price.pk}/', {'price_paisa': 1}, format='json')
    assert resp.status_code in (403, 404, 405)


@pytest.mark.django_db
def test_delete_invoice_returns_405(outlet, session, manager):
    order = Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=0,
    )
    inv = Invoice.objects.create(
        order=order, invoice_number='QA-INV-DEL-001',
        issued_at=timezone.now(), total_paisa=0,
    )
    resp = api(manager).delete(f'/api/invoices/{inv.pk}/')
    assert resp.status_code == 405
