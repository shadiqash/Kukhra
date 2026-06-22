"""
Proves: nightly_rollup() aggregates FULFILLED orders for the target date into
DailySalesRollup, is idempotent, and ignores non-FULFILLED orders.
"""
import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import (
    CashierSession, DailySalesRollup, Order, OrderLine, OrderSource, OrderStatus,
)
from apps.sales.tasks import nightly_rollup


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='C1')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='rollup_cashier', password='x')


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )


@pytest.fixture
def product(db):
    return Product.objects.create(name='Breast', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=50000, valid_from='2024-01-01',
    )


TARGET = '2025-03-01'


def make_order(outlet, session, status=OrderStatus.FULFILLED, total_paisa=0):
    return Order.objects.create(
        fulfilled_location=outlet,
        session=session,
        source=OrderSource.COUNTER,
        status=status,
        total_paisa=total_paisa,
    )


# ── Core behaviour ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_rollup_creates_row_for_target_date(outlet, session):
    o = make_order(outlet, session, total_paisa=100000)
    Order.objects.filter(pk=o.pk).update(created_at=datetime.datetime(2025, 3, 1, tzinfo=datetime.timezone.utc))

    result = nightly_rollup(target_date=TARGET)

    assert result['date'] == TARGET
    assert result['action'] == 'created'
    assert DailySalesRollup.objects.filter(date=datetime.date(2025, 3, 1)).exists()


@pytest.mark.django_db
def test_rollup_counts_only_fulfilled_orders(outlet, session):
    for status in (OrderStatus.FULFILLED, OrderStatus.FULFILLED):
        o = make_order(outlet, session, status=status, total_paisa=50000)
        Order.objects.filter(pk=o.pk).update(created_at=datetime.datetime(2025, 3, 1, tzinfo=datetime.timezone.utc))

    pending = make_order(outlet, session, status=OrderStatus.PENDING, total_paisa=99999)
    Order.objects.filter(pk=pending.pk).update(created_at=datetime.datetime(2025, 3, 1, tzinfo=datetime.timezone.utc))

    result = nightly_rollup(target_date=TARGET)
    assert result['order_count'] == 2


@pytest.mark.django_db
def test_rollup_sums_revenue(outlet, session):
    for total in (30000, 70000):
        o = make_order(outlet, session, status=OrderStatus.FULFILLED, total_paisa=total)
        Order.objects.filter(pk=o.pk).update(created_at=datetime.datetime(2025, 3, 1, tzinfo=datetime.timezone.utc))

    result = nightly_rollup(target_date=TARGET)
    assert result['total_revenue_paisa'] == 100000


@pytest.mark.django_db
def test_rollup_is_idempotent(outlet, session):
    o = make_order(outlet, session, status=OrderStatus.FULFILLED, total_paisa=10000)
    Order.objects.filter(pk=o.pk).update(created_at=datetime.datetime(2025, 3, 1, tzinfo=datetime.timezone.utc))

    nightly_rollup(target_date=TARGET)
    result = nightly_rollup(target_date=TARGET)

    assert result['action'] == 'updated'
    assert DailySalesRollup.objects.filter(date=datetime.date(2025, 3, 1)).count() == 1


@pytest.mark.django_db
def test_rollup_zero_orders_creates_empty_row():
    result = nightly_rollup(target_date=TARGET)
    assert result['order_count'] == 0
    assert result['total_revenue_paisa'] == 0
    assert DailySalesRollup.objects.filter(date=datetime.date(2025, 3, 1)).exists()


@pytest.mark.django_db
def test_rollup_does_not_bleed_across_dates(outlet, session):
    o_march = make_order(outlet, session, status=OrderStatus.FULFILLED, total_paisa=50000)
    Order.objects.filter(pk=o_march.pk).update(created_at=datetime.datetime(2025, 3, 1, tzinfo=datetime.timezone.utc))

    o_april = make_order(outlet, session, status=OrderStatus.FULFILLED, total_paisa=99000)
    Order.objects.filter(pk=o_april.pk).update(created_at=datetime.datetime(2025, 4, 1, tzinfo=datetime.timezone.utc))

    result = nightly_rollup(target_date=TARGET)
    assert result['order_count'] == 1
    assert result['total_revenue_paisa'] == 50000
