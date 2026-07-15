"""
Regression tests for the audit-hardening pass:

  * checkout rejects negative / zero / mismatched-price / mismatched-total lines
  * a closed or foreign session cannot be sold against
  * Order / OrderLine / Payment are immutable over the API (no PATCH/DELETE)
  * cancel is the only void path, is manager-gated, and reverses the ledger
  * the step-by-step Payment path consumes its intent

Each test asserts the *defended* behaviour — a failure here is a real regression.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.payments.models import Gateway, IntentStatus, PaymentIntent
from apps.sales.models import CashierSession, Order, OrderStatus, Payment


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Hard Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Hard Counter')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='hard_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def other_cashier(db):
    return User.objects.create_user(username='hard_cashier2', password='x', role=Role.CASHIER)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='hard_manager', password='x', role=Role.MANAGER)


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=100000, opened_at=timezone.now(),
    )


@pytest.fixture
def product(db):
    return Product.objects.create(name='Hard Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL, price_paisa=50000, valid_from='2024-01-01',
    )


@pytest.fixture
def other_product(db):
    return Product.objects.create(name='Hard Other', uom=UoM.KG)


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def seed(product, outlet, user, kg='10'):
    StockMovement.objects.create(
        product=product, location=outlet, type=MovementType.PRODUCTION,
        qty_kg=Decimal(kg), user=user,
    )


def payload(outlet, session, price, product, qty_kg, line_total, total=None, pay=None):
    total = line_total if total is None else total
    return {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': 'counter',
        'total_paisa': total,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': str(qty_kg), 'line_total_paisa': line_total,
        }],
        'payments': pay or [{'method': 'cash', 'amount_paisa': total}],
    }


# ── input validation ─────────────────────────────────────────────────────────

def test_negative_qty_rejected(outlet, session, price, product, cashier, manager):
    seed(product, outlet, manager)
    r = api(cashier).post('/api/orders/', payload(outlet, session, price, product, '-5.000', 0), format='json')
    assert r.status_code == 400
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('10')


def test_zero_qty_rejected(outlet, session, price, product, cashier, manager):
    seed(product, outlet, manager)
    r = api(cashier).post('/api/orders/', payload(outlet, session, price, product, '0', 0), format='json')
    assert r.status_code == 400


def test_line_total_must_match_price(outlet, session, price, product, cashier, manager):
    seed(product, outlet, manager)
    # 2 kg × 50000 = 100000, but claim 1 paisa
    r = api(cashier).post('/api/orders/', payload(outlet, session, price, product, '2.000', 1), format='json')
    assert r.status_code == 400


def test_header_total_must_match_lines(outlet, session, price, product, cashier, manager):
    seed(product, outlet, manager)
    body = payload(outlet, session, price, product, '2.000', 100000, total=1)
    body['payments'] = [{'method': 'cash', 'amount_paisa': 1}]
    r = api(cashier).post('/api/orders/', body, format='json')
    assert r.status_code == 400


def test_underpayment_rejected(outlet, session, price, product, cashier, manager):
    seed(product, outlet, manager)
    body = payload(outlet, session, price, product, '1.000', 50000)
    body['payments'] = [{'method': 'cash', 'amount_paisa': 5}]
    r = api(cashier).post('/api/orders/', body, format='json')
    assert r.status_code == 400


def test_price_of_other_product_rejected(outlet, session, price, product, other_product, cashier, manager):
    seed(other_product, outlet, manager)
    r = api(cashier).post(
        '/api/orders/', payload(outlet, session, price, other_product, '1.000', 50000), format='json',
    )
    assert r.status_code == 400


def test_inactive_price_rejected(outlet, session, product, cashier, manager):
    seed(product, outlet, manager)
    closed = Price.objects.create(
        product=product, tier=PriceTier.WHOLESALE, price_paisa=40000,
        valid_from='2024-01-01', valid_to='2024-06-01',
    )
    r = api(cashier).post(
        '/api/orders/', payload(outlet, session, closed, product, '1.000', 40000), format='json',
    )
    assert r.status_code == 400


# ── session integrity ────────────────────────────────────────────────────────

def test_closed_session_rejected(outlet, session, price, product, cashier, manager):
    seed(product, outlet, manager)
    session.close(100000)
    r = api(cashier).post(
        '/api/orders/', payload(outlet, session, price, product, '1.000', 50000), format='json',
    )
    assert r.status_code == 400


def test_foreign_cashier_session_rejected(outlet, session, price, product, other_cashier, manager):
    seed(product, outlet, manager)
    r = api(other_cashier).post(
        '/api/orders/', payload(outlet, session, price, product, '1.000', 50000), format='json',
    )
    assert r.status_code == 400


# ── immutability of the money trail ──────────────────────────────────────────

def _make_order(outlet, session, price, product, cashier, manager):
    seed(product, outlet, manager)
    r = api(cashier).post(
        '/api/orders/', payload(outlet, session, price, product, '1.000', 50000), format='json',
    )
    assert r.status_code == 201, r.data
    return r.data


def test_order_patch_blocked(outlet, session, price, product, cashier, manager):
    o = _make_order(outlet, session, price, product, cashier, manager)
    r = api(cashier).patch(f"/api/orders/{o['id']}/", {'total_paisa': 0}, format='json')
    assert r.status_code == 405
    assert Order.objects.get(pk=o['id']).total_paisa == 50000


def test_order_delete_blocked(outlet, session, price, product, cashier, manager):
    o = _make_order(outlet, session, price, product, cashier, manager)
    r = api(cashier).delete(f"/api/orders/{o['id']}/")
    assert r.status_code == 405
    assert Order.objects.filter(pk=o['id']).exists()


def test_payment_delete_blocked(outlet, session, price, product, cashier, manager):
    o = _make_order(outlet, session, price, product, cashier, manager)
    pay_id = o['payments'][0]['id']
    r = api(cashier).delete(f'/api/payments/{pay_id}/')
    assert r.status_code == 405
    assert Payment.objects.filter(pk=pay_id).exists()


# ── cancel is the sanctioned void ────────────────────────────────────────────

def test_cashier_cannot_cancel(outlet, session, price, product, cashier, manager):
    o = _make_order(outlet, session, price, product, cashier, manager)
    r = api(cashier).post(f"/api/orders/{o['id']}/cancel/")
    assert r.status_code == 403
    assert Order.objects.get(pk=o['id']).status == OrderStatus.FULFILLED


def test_manager_cancel_reverses_stock(outlet, session, price, product, cashier, manager):
    o = _make_order(outlet, session, price, product, cashier, manager)
    # sold 1 kg out of 10 → 9 on hand
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('9')
    r = api(manager).post(f"/api/orders/{o['id']}/cancel/")
    assert r.status_code == 200
    assert Order.objects.get(pk=o['id']).status == OrderStatus.CANCELLED
    # reversing return row restores stock, original sale row untouched
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('10')
    assert StockMovement.objects.filter(ref_id=o['id'], type=MovementType.SALE).exists()
    assert StockMovement.objects.filter(ref_id=o['id'], type=MovementType.RETURN).exists()


def test_double_cancel_rejected(outlet, session, price, product, cashier, manager):
    o = _make_order(outlet, session, price, product, cashier, manager)
    assert api(manager).post(f"/api/orders/{o['id']}/cancel/").status_code == 200
    assert api(manager).post(f"/api/orders/{o['id']}/cancel/").status_code == 400


# ── step-by-step payment consumes its intent ─────────────────────────────────

def test_step_payment_consumes_intent(outlet, session, price, product, cashier, manager):
    o = _make_order(outlet, session, price, product, cashier, manager)
    intent = PaymentIntent.objects.create(
        gateway=Gateway.MOCK, amount_paisa=50000, location=outlet,
        status=IntentStatus.VERIFIED, created_by=cashier,
    )
    r = api(cashier).post('/api/payments/', {
        'order': o['id'], 'method': 'fonepay', 'amount_paisa': 50000, 'intent': intent.pk,
    }, format='json')
    assert r.status_code == 201, r.data
    intent.refresh_from_db()
    assert intent.status == IntentStatus.CONSUMED
