"""
Proves: Order.fulfill() creates one StockMovement(type=sale, negative qty) per OrderLine,
and that stock at the fulfilled location decreases accordingly.
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import (
    CashierSession, Order, OrderLine, OrderSource, OrderStatus, Payment, PaymentMethod,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Outlet 1', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Counter A')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='cashier1', password='x')


@pytest.fixture
def product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )


@pytest.fixture
def order(db, outlet, session):
    return Order.objects.create(
        fulfilled_location=outlet,
        session=session,
        source=OrderSource.COUNTER,
        total_paisa=0,
    )


def add_line(order, product, price, qty_kg=Decimal('0'), qty_pieces=0):
    return OrderLine.objects.create(
        order=order, product=product, price=price,
        qty_kg=qty_kg, qty_pieces=qty_pieces,
        line_total_paisa=int(qty_kg * price.price_paisa) or (qty_pieces * price.price_paisa),
    )


@pytest.fixture
def seed_stock(db, outlet, product, cashier):
    """Seed a large production movement so fulfill() stock-check passes."""
    StockMovement.objects.create(
        product=product, location=outlet,
        type=MovementType.PRODUCTION, qty_kg=Decimal('1000.000'),
        qty_pieces=1000, user=cashier,
    )


# ── Core invariant: one sale movement per line ────────────────────────────────

@pytest.mark.django_db
def test_fulfill_creates_one_movement_per_line(seed_stock, order, product, price, cashier, outlet):
    add_line(order, product, price, qty_kg=Decimal('2.000'))
    order.fulfill(cashier)
    movements = StockMovement.objects.filter(ref_id=order.pk, type=MovementType.SALE)
    assert movements.count() == 1
    m = movements.first()
    assert m.location == outlet
    assert m.product  == product


@pytest.mark.django_db
def test_sale_movement_qty_is_negative(seed_stock, order, product, price, cashier):
    add_line(order, product, price, qty_kg=Decimal('3.000'))
    order.fulfill(cashier)
    m = StockMovement.objects.get(ref_id=order.pk, type=MovementType.SALE)
    assert m.qty_kg == Decimal('-3.000')


@pytest.mark.django_db
def test_multi_line_order_creates_one_movement_per_line(order, cashier, outlet):
    p2 = Product.objects.create(name='Wings', uom=UoM.KG)
    pr2 = Price.objects.create(product=p2, tier=PriceTier.RETAIL, price_paisa=40000, valid_from='2024-01-01')
    p3 = Product.objects.create(name='Liver', uom=UoM.KG)
    pr3 = Price.objects.create(product=p3, tier=PriceTier.RETAIL, price_paisa=20000, valid_from='2024-01-01')

    # Seed stock for both products before fulfilling
    for p in (p2, p3):
        StockMovement.objects.create(
            product=p, location=outlet,
            type=MovementType.PRODUCTION, qty_kg=Decimal('100.000'), user=cashier,
        )

    for p, pr, qty in [(p2, pr2, Decimal('1.500')), (p3, pr3, Decimal('0.500'))]:
        add_line(order, p, pr, qty_kg=qty)
    order.fulfill(cashier)

    assert StockMovement.objects.filter(ref_id=order.pk, type=MovementType.SALE).count() == 2


@pytest.mark.django_db
def test_sale_movement_reduces_location_stock(order, product, price, cashier, outlet):
    StockMovement.objects.create(
        product=product, location=outlet,
        type=MovementType.PRODUCTION, qty_kg=Decimal('10.000'), user=cashier,
    )
    add_line(order, product, price, qty_kg=Decimal('2.500'))
    order.fulfill(cashier)
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('7.500')


@pytest.mark.django_db
def test_sale_movement_ref_id_points_to_order(seed_stock, order, product, price, cashier):
    add_line(order, product, price, qty_kg=Decimal('1.000'))
    order.fulfill(cashier)
    m = StockMovement.objects.get(type=MovementType.SALE)
    assert m.ref_id == order.pk


# ── Piece products ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_piece_sale_movement_uses_qty_pieces(order, cashier, outlet):
    p = Product.objects.create(name='Sausage Pack', uom=UoM.PIECE)
    pr = Price.objects.create(product=p, tier=PriceTier.RETAIL, price_paisa=25000, valid_from='2024-01-01')
    StockMovement.objects.create(
        product=p, location=outlet,
        type=MovementType.PRODUCTION, qty_pieces=100, user=cashier,
    )
    add_line(order, p, pr, qty_pieces=4)
    order.fulfill(cashier)
    m = StockMovement.objects.get(ref_id=order.pk, type=MovementType.SALE)
    assert m.qty_pieces == -4
    assert m.qty_kg == Decimal('0')


# ── Status transitions ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fulfill_sets_status_to_fulfilled(seed_stock, order, product, price, cashier):
    add_line(order, product, price, qty_kg=Decimal('1.000'))
    order.fulfill(cashier)
    order.refresh_from_db()
    assert order.status == OrderStatus.FULFILLED


@pytest.mark.django_db
def test_fulfilling_fulfilled_order_raises(seed_stock, order, product, price, cashier):
    add_line(order, product, price, qty_kg=Decimal('1.000'))
    order.fulfill(cashier)
    with pytest.raises(RuntimeError, match='only pending orders'):
        order.fulfill(cashier)


@pytest.mark.django_db
def test_fulfilling_cancelled_order_raises(order, product, price, cashier):
    order.status = OrderStatus.CANCELLED
    order.save()
    with pytest.raises(RuntimeError, match='only pending orders'):
        order.fulfill(cashier)


# ── Session and payment ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_order_linked_to_session(order, session):
    assert order.session == session


@pytest.mark.django_db
def test_payment_recorded_against_order(seed_stock, order, product, price, cashier):
    add_line(order, product, price, qty_kg=Decimal('1.000'))
    order.fulfill(cashier)
    Payment.objects.create(
        order=order, method=PaymentMethod.CASH,
        amount_paisa=75000,
    )
    assert order.payments.count() == 1
    assert order.payments.first().method == PaymentMethod.CASH


@pytest.mark.django_db
def test_cashier_session_close(session):
    session.close(closing_counted_paisa=600000)
    session.refresh_from_db()
    assert session.closed_at is not None
    assert session.closing_counted_paisa == 600000


@pytest.mark.django_db
def test_cashier_session_close_twice_raises(session):
    session.close(closing_counted_paisa=600000)
    with pytest.raises(RuntimeError, match='already closed'):
        session.close(closing_counted_paisa=600000)
