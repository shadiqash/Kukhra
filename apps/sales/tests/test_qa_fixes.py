"""
Regression tests for the QA/security fixes:
  EF-01  idempotent checkout (a replayed sale returns the original order)
  EF-04  a cashier without a session is scoped to their assigned outlet
"""
import uuid
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import CashierSession, Order, OrderSource, OrderStatus


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='QA Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='QA Counter')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='qa_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier, opening_float_paisa=0, opened_at=timezone.now(),
    )


@pytest.fixture
def product(db):
    return Product.objects.create(name='QA Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL, price_paisa=75000, valid_from='2024-01-01',
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


def checkout_payload(outlet, product, price, session=None, txn_id=None):
    payload = {
        'fulfilled_location': outlet.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': '2.000', 'qty_pieces': 0, 'line_total_paisa': 150000,
        }],
        'payments': [{'method': 'cash', 'amount_paisa': 150000, 'ref': None}],
    }
    if session is not None:
        payload['session'] = session.pk
    if txn_id is not None:
        payload['client_txn_id'] = txn_id
    return payload


# ── EF-01: idempotency ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_replayed_checkout_returns_original_order_and_charges_once(outlet, session, cashier, product, price):
    """A lost-response retry carrying the same client_txn_id must not ring a second sale."""
    stock_in(product, outlet, '10.000', cashier)
    txn_id = str(uuid.uuid4())
    payload = checkout_payload(outlet, product, price, session=session, txn_id=txn_id)

    r1 = api(cashier).post('/api/orders/', payload, format='json')
    assert r1.status_code == 201, r1.data

    r2 = api(cashier).post('/api/orders/', payload, format='json')
    assert r2.status_code == 200, r2.data          # replay → original, not a new 201
    assert r2.data['id'] == r1.data['id']

    assert Order.objects.count() == 1
    # Stock left the shelf exactly once, not twice.
    assert StockMovement.objects.filter(type=MovementType.SALE, ref_id=r1.data['id']).count() == 1
    assert StockMovement.objects.filter(type=MovementType.SALE).count() == 1


@pytest.mark.django_db
def test_checkout_without_txn_id_is_unaffected(outlet, session, cashier, product, price):
    stock_in(product, outlet, '10.000', cashier)
    payload = checkout_payload(outlet, product, price, session=session)  # no key
    r = api(cashier).post('/api/orders/', payload, format='json')
    assert r.status_code == 201, r.data
    assert Order.objects.get(pk=r.data['id']).client_txn_id is None


# ── EF-04: cashier location scoping when no session is supplied ────────────────

@pytest.mark.django_db
def test_cashier_cannot_sell_without_session_at_unassigned_outlet(outlet, cashier, product, price):
    stock_in(product, outlet, '10.000', cashier)
    # No session, and the cashier is not assigned to this outlet → rejected.
    r = api(cashier).post('/api/orders/', checkout_payload(outlet, product, price), format='json')
    assert r.status_code == 400, r.data
    assert Order.objects.count() == 0
    assert StockMovement.objects.filter(type=MovementType.SALE).count() == 0


@pytest.mark.django_db
def test_cashier_can_sell_without_session_at_assigned_outlet(outlet, cashier, product, price):
    cashier.assigned_locations.add(outlet)
    stock_in(product, outlet, '10.000', cashier)
    r = api(cashier).post('/api/orders/', checkout_payload(outlet, product, price), format='json')
    assert r.status_code == 201, r.data


@pytest.mark.django_db
def test_cashier_session_sale_still_works_without_assignment(outlet, session, cashier, product, price):
    """The normal session path is unchanged: a session ties the cashier to the outlet."""
    stock_in(product, outlet, '10.000', cashier)
    r = api(cashier).post('/api/orders/', checkout_payload(outlet, product, price, session=session), format='json')
    assert r.status_code == 201, r.data
