"""
Tests for the atomic one-shot checkout: POST /orders/ with a nested
`lines`/`payments` payload creates the Order, its OrderLines, its Payments,
and fulfills it in a single DB transaction.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import CashierSession, Order, OrderLine, OrderSource, OrderStatus, Payment


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Checkout Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Checkout Counter')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='checkout_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )


@pytest.fixture
def product(db):
    return Product.objects.create(name='Checkout Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def stock_in(product, location, qty_kg, user):
    StockMovement.objects.create(
        product=product, location=location,
        type=MovementType.PRODUCTION, qty_kg=Decimal(qty_kg), user=user,
    )


@pytest.mark.django_db
def test_checkout_creates_order_lines_payment_and_fulfills(outlet, session, cashier, product, price):
    stock_in(product, outlet, '10.000', cashier)

    resp = api(cashier).post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': '2.000', 'qty_pieces': 0, 'line_total_paisa': 150000,
        }],
        'payments': [{'method': 'cash', 'amount_paisa': 150000, 'ref': None}],
    }, format='json')

    assert resp.status_code == 201, resp.data
    assert resp.data['status'] == OrderStatus.FULFILLED
    order_id = resp.data['id']

    assert OrderLine.objects.filter(order_id=order_id).count() == 1
    assert Payment.objects.filter(order_id=order_id).count() == 1
    assert StockMovement.objects.filter(
        ref_id=order_id, type=MovementType.SALE, location=outlet,
    ).count() == 1


@pytest.mark.django_db
def test_checkout_supports_split_payment(outlet, session, cashier, product, price):
    stock_in(product, outlet, '10.000', cashier)

    resp = api(cashier).post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': '2.000', 'qty_pieces': 0, 'line_total_paisa': 150000,
        }],
        'payments': [
            {'method': 'cash', 'amount_paisa': 100000, 'ref': None},
            {'method': 'card', 'amount_paisa': 50000, 'ref': 'slip-1'},
        ],
    }, format='json')

    assert resp.status_code == 201, resp.data
    assert Payment.objects.filter(order_id=resp.data['id']).count() == 2


@pytest.mark.django_db
def test_checkout_insufficient_stock_rolls_back_everything(outlet, session, cashier, product, price):
    # No stock seeded — the sale must be rejected and nothing left behind.
    resp = api(cashier).post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': '2.000', 'qty_pieces': 0, 'line_total_paisa': 150000,
        }],
        'payments': [{'method': 'cash', 'amount_paisa': 150000, 'ref': None}],
    }, format='json')

    assert resp.status_code == 400
    assert 'Insufficient stock' in resp.data['detail']

    # Nothing was persisted — order, lines, and payment all rolled back.
    assert Order.objects.count() == 0
    assert OrderLine.objects.count() == 0
    assert Payment.objects.count() == 0
    assert StockMovement.objects.filter(type=MovementType.SALE).count() == 0


@pytest.mark.django_db
def test_checkout_missing_lines_returns_400(outlet, session, cashier):
    resp = api(cashier).post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
        'lines': [],
        'payments': [{'method': 'cash', 'amount_paisa': 150000, 'ref': None}],
    }, format='json')

    assert resp.status_code == 400
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_checkout_missing_payments_returns_400(outlet, session, cashier, product, price):
    resp = api(cashier).post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': '2.000', 'qty_pieces': 0, 'line_total_paisa': 150000,
        }],
        'payments': [],
    }, format='json')

    assert resp.status_code == 400
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_legacy_bare_order_create_still_works(outlet, session, cashier):
    """Existing step-by-step flow (no `lines` key) must be unaffected."""
    resp = api(cashier).post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
    }, format='json')

    assert resp.status_code == 201, resp.data
    assert resp.data['status'] == OrderStatus.PENDING
    assert OrderLine.objects.filter(order_id=resp.data['id']).count() == 0


@pytest.mark.django_db
def test_worker_cannot_use_checkout_endpoint(outlet, session, product, price):
    worker = User.objects.create_user(username='checkout_worker', password='x', role=Role.WAREHOUSE)
    resp = api(worker).post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': '2.000', 'qty_pieces': 0, 'line_total_paisa': 150000,
        }],
        'payments': [{'method': 'cash', 'amount_paisa': 150000, 'ref': None}],
    }, format='json')

    assert resp.status_code == 403
