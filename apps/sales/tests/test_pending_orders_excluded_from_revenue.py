"""
Revenue reports must count FULFILLED orders only. Found live: a pending
(never-fulfilled) order inflated /orders/summary/ while the nightly rollup —
which counts fulfilled only — disagreed with the dashboard.
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import CashierSession, Order, OrderSource, OrderStatus, Payment


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='rev_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Revenue Outlet', type=LocationType.OUTLET)


@pytest.fixture
def session(db, outlet, manager):
    counter = Counter.objects.create(location=outlet, name='R1')
    return CashierSession.objects.create(
        counter=counter, cashier=manager,
        opening_float_paisa=100000, opened_at=timezone.now(),
    )


def api(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def orders(outlet, session):
    Order.objects.create(fulfilled_location=outlet, session=session,
                         source=OrderSource.COUNTER, total_paisa=50000,
                         status=OrderStatus.FULFILLED)
    Order.objects.create(fulfilled_location=outlet, session=session,
                         source=OrderSource.COUNTER, total_paisa=30000,
                         status=OrderStatus.PENDING)
    Order.objects.create(fulfilled_location=outlet, session=session,
                         source=OrderSource.COUNTER, total_paisa=20000,
                         status=OrderStatus.CANCELLED)


@pytest.mark.django_db
def test_orders_summary_counts_fulfilled_only(manager, outlet, session):
    orders(outlet, session)
    res = api(manager).get('/api/orders/summary/')
    assert res.data == {'order_count': 1, 'gross_paisa': 50000}


@pytest.mark.django_db
def test_orders_summary_explicit_status_filter_wins(manager, outlet, session):
    orders(outlet, session)
    res = api(manager).get('/api/orders/summary/?status=pending')
    assert res.data == {'order_count': 1, 'gross_paisa': 30000}


@pytest.mark.django_db
def test_session_summary_sales_are_fulfilled_only(manager, outlet, session):
    orders(outlet, session)
    res = api(manager).get(f'/api/sessions/{session.pk}/summary/')
    assert res.data['sales_count'] == 1
    assert res.data['sales_total_paisa'] == 50000


@pytest.mark.django_db
def test_drawer_cash_still_counts_paid_pending_orders(manager, outlet, session):
    """Cash physically handed over stays in expected cash even if fulfilment failed."""
    orders(outlet, session)
    pending = Order.objects.get(status=OrderStatus.PENDING)
    Payment.objects.create(order=pending, method='cash', amount_paisa=30000)
    res = api(manager).get(f'/api/sessions/{session.pk}/summary/')
    assert res.data['cash_sales_paisa'] == 30000
    assert res.data['expected_cash_paisa'] == 100000 + 30000
