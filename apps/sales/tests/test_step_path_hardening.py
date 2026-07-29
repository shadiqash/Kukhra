"""
The step-by-step order flow (bare POST /orders/ → /order-lines/ → /payments/ →
/orders/{id}/fulfill/) must satisfy the same invariants as one-shot checkout
(review findings H1/H2): honest line totals, header total = Σ lines, payments
cover the total, and nothing attaches to a non-pending order.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import CashierSession, Order, OrderLine, OrderSource, OrderStatus


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Baneshwor Outlet', type=LocationType.OUTLET)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='mgr-step', password='x', role=Role.MANAGER)


@pytest.fixture
def session(db, outlet, manager):
    counter = Counter.objects.create(location=outlet, name='C1')
    cashier = User.objects.create_user(username='till-step', password='x', role=Role.CASHIER)
    cashier.assigned_locations.add(outlet)
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=100000, opened_at=timezone.now(),
    )


@pytest.fixture
def product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2026-01-01',
    )


@pytest.fixture
def stocked(db, outlet, product, manager):
    StockMovement.objects.create(
        product=product, location=outlet,
        type=MovementType.PRODUCTION, qty_kg=Decimal('100.000'), user=manager,
    )


def api(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def make_order(outlet, session, total=150000, status=OrderStatus.PENDING):
    return Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, total_paisa=total, status=status,
    )


@pytest.mark.django_db
def test_dishonest_line_total_rejected(outlet, session, manager, product, price):
    order = make_order(outlet, session)
    res = api(manager).post('/api/order-lines/', {
        'order': order.pk, 'product': product.pk, 'price': price.pk,
        'qty_kg': '5.000', 'qty_pieces': 0, 'line_total_paisa': 100,   # 5 kg rung as Rs 1
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_piece_line_total_must_be_exact(outlet, session, manager, price, product):
    piece_product = Product.objects.create(name='Egg Tray', uom=UoM.PIECE)
    piece_price = Price.objects.create(
        product=piece_product, tier=PriceTier.RETAIL,
        price_paisa=1500, valid_from='2026-01-01',
    )
    order = make_order(outlet, session)
    res = api(manager).post('/api/order-lines/', {
        'order': order.pk, 'product': piece_product.pk, 'price': piece_price.pk,
        'qty_kg': '0', 'qty_pieces': 10, 'line_total_paisa': 14999,
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_line_on_fulfilled_order_rejected(outlet, session, manager, product, price):
    order = make_order(outlet, session, status=OrderStatus.FULFILLED)
    res = api(manager).post('/api/order-lines/', {
        'order': order.pk, 'product': product.pk, 'price': price.pk,
        'qty_kg': '1.000', 'qty_pieces': 0, 'line_total_paisa': 75000,
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_payment_on_cancelled_order_rejected(outlet, session, manager):
    order = make_order(outlet, session, status=OrderStatus.CANCELLED)
    res = api(manager).post('/api/payments/', {
        'order': order.pk, 'method': 'cash', 'amount_paisa': 150000,
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_fulfill_rejects_header_total_mismatch(outlet, session, manager, product, price, stocked):
    order = make_order(outlet, session, total=1)   # header claims Rs 0.01
    OrderLine.objects.create(
        order=order, product=product, price=price,
        qty_kg=Decimal('2.000'), qty_pieces=0, line_total_paisa=150000,
    )
    res = api(manager).post(f'/api/orders/{order.pk}/fulfill/')
    assert res.status_code == 400
    assert 'sum of line totals' in res.data['detail']
    order.refresh_from_db()
    assert order.status == OrderStatus.PENDING


@pytest.mark.django_db
def test_fulfill_rejects_uncovered_total(outlet, session, manager, product, price, stocked):
    order = make_order(outlet, session, total=150000)
    OrderLine.objects.create(
        order=order, product=product, price=price,
        qty_kg=Decimal('2.000'), qty_pieces=0, line_total_paisa=150000,
    )
    res = api(manager).post(f'/api/orders/{order.pk}/fulfill/')   # no payment taken
    assert res.status_code == 400
    assert 'do not cover' in res.data['detail']


@pytest.mark.django_db
def test_honest_step_path_still_works(outlet, session, manager, product, price, stocked):
    """The POS offline-replay flow with truthful figures must keep working."""
    c = api(manager)
    order_id = c.post('/api/orders/', {
        'fulfilled_location': outlet.pk, 'session': session.pk,
        'source': OrderSource.COUNTER, 'total_paisa': 150000,
    }, format='json').data['id']
    assert c.post('/api/order-lines/', {
        'order': order_id, 'product': product.pk, 'price': price.pk,
        'qty_kg': '2.000', 'qty_pieces': 0, 'line_total_paisa': 150000,
    }, format='json').status_code == 201
    assert c.post('/api/payments/', {
        'order': order_id, 'method': 'cash', 'amount_paisa': 150000,
    }, format='json').status_code == 201
    res = c.post(f'/api/orders/{order_id}/fulfill/')
    assert res.status_code == 200, res.data
    assert res.data['status'] == OrderStatus.FULFILLED
