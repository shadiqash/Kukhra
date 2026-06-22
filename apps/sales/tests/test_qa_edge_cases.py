"""
QA — Angle 2: Business logic edge cases.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement, StockTransfer
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.lots.models import Lot, LotStatus
from apps.sales.models import (
    CashierSession, Order, OrderLine, OrderSource, OrderStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def manager(db):
    return User.objects.create_user(username='edge_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='edge_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Edge Outlet', type=LocationType.OUTLET)


@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='Edge WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Edge Counter')


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )


@pytest.fixture
def product(db):
    return Product.objects.create(name='Edge Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )


@pytest.fixture
def location(db):
    return Location.objects.create(name='Farm', type=LocationType.WAREHOUSE)


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── Edge case 1: Oversell (negative stock allowed in Phase 1) ──────────────────

@pytest.mark.django_db
def test_oversell_results_in_negative_stock(outlet, session, manager, product, price):
    """
    Phase 1 has no stock floor. Selling beyond available stock drives qty negative.
    This documents current behaviour — Phase 2 should add a floor check.
    """
    # Zero initial stock
    order = Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, total_paisa=75000,
    )
    OrderLine.objects.create(
        order=order, product=product, price=price,
        qty_kg=Decimal('5.000'), qty_pieces=0, line_total_paisa=375000,
    )
    order.fulfill(user=manager)  # no stock guard — succeeds

    stock = current_stock(product.pk, outlet.pk)['qty_kg']
    assert stock == Decimal('-5.000'), (
        f'Expected -5.000 (Phase 1 allows negative), got {stock}. '
        'If this fails, a stock floor was added — remove this test and add a 400 test instead.'
    )


# ── Edge case 2: Double-close cashier session ─────────────────────────────────

@pytest.mark.django_db
def test_double_close_session_raises(session):
    session.close(closing_counted_paisa=100000)
    with pytest.raises(RuntimeError, match='already closed'):
        session.close(closing_counted_paisa=200000)


@pytest.mark.django_db
def test_double_close_session_via_api_returns_400(session, cashier):
    c = api(cashier)
    c.post(f'/api/sessions/{session.pk}/close/', {'closing_counted_paisa': 100000}, format='json')
    resp = c.post(f'/api/sessions/{session.pk}/close/', {'closing_counted_paisa': 200000}, format='json')
    assert resp.status_code == 400


# ── Edge case 3: Double-receive a transfer ────────────────────────────────────

@pytest.mark.django_db
def test_double_receive_transfer_raises(warehouse, outlet, manager, product):
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    StockMovement.objects.create(
        product=product, location=warehouse,
        type=MovementType.TRANSFER, qty_kg=Decimal('-5.000'),
        ref_id=transfer.pk, user=manager,
    )
    transfer.confirm_receipt(user=manager)
    with pytest.raises(RuntimeError, match='already been received'):
        transfer.confirm_receipt(user=manager)


@pytest.mark.django_db
def test_double_receive_transfer_via_api_returns_400(warehouse, outlet, manager, product):
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    StockMovement.objects.create(
        product=product, location=warehouse,
        type=MovementType.TRANSFER, qty_kg=Decimal('-5.000'),
        ref_id=transfer.pk, user=manager,
    )
    c = api(manager)
    c.post(f'/api/transfers/{transfer.pk}/confirm-receipt/')
    resp = c.post(f'/api/transfers/{transfer.pk}/confirm-receipt/')
    assert resp.status_code == 400


# ── Edge case 4: Fulfill order with zero lines ────────────────────────────────

@pytest.mark.django_db
def test_fulfill_order_with_zero_lines_succeeds_but_creates_no_movements(
    outlet, session, manager
):
    """
    Phase 1: no guard on zero-line orders. Fulfill succeeds and creates 0 movements.
    Documents current behaviour.
    """
    order = Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, total_paisa=0,
    )
    order.fulfill(user=manager)
    order.refresh_from_db()
    assert order.status == OrderStatus.FULFILLED
    from apps.inventory.models import StockMovement
    assert StockMovement.objects.filter(ref_id=order.pk, type=MovementType.SALE).count() == 0


# ── Edge case 5: Lot FSM — SETTLEMENT is a dead end ──────────────────────────

@pytest.mark.django_db
def test_settled_lot_cannot_transition(location):
    lot = Lot.objects.create(
        code='SETTLED-001', source_type='own',
        arrival_location=location, live_weight_kg='100.000', bird_count=100,
        status=LotStatus.SETTLEMENT,
    )
    with pytest.raises(ValueError, match='Illegal lot transition'):
        lot.transition(LotStatus.SALE)


# ── Edge case 6: Price overlap — model allows duplicate (valid_from, product, tier) ──

@pytest.mark.django_db
def test_overlapping_price_is_allowed_silently(product):
    """
    Phase 1: Price has no unique_together on (product, tier, valid_from).
    Two prices with the same key can coexist — the API returns whichever the ORM picks.
    Documents current behaviour; Phase 2 should add a unique constraint or overlap guard.
    """
    Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )
    # This should not raise — but documents a known gap
    p2 = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=80000, valid_from='2024-01-01',
    )
    count = Price.objects.filter(
        product=product, tier=PriceTier.RETAIL, valid_from='2024-01-01'
    ).count()
    assert count == 2, (
        'Two prices with same (product, tier, valid_from) were created. '
        'Phase 2 should add a unique constraint to prevent this ambiguity.'
    )
