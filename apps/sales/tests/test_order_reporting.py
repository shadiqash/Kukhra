"""
Tests for the order report filters and the /orders/summary/ aggregate.

The summary is what the admin dashboard shows, so two things must hold:
it aggregates the whole filtered set (not one page), and cancelled orders
never count as revenue.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.locations.models import Location, LocationType
from apps.sales.models import Order, OrderSource, OrderStatus


@pytest.fixture
def outlet_a(db):
    return Location.objects.create(name='Outlet A', type=LocationType.OUTLET)


@pytest.fixture
def outlet_b(db):
    return Location.objects.create(name='Outlet B', type=LocationType.OUTLET)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='report_manager', password='x', role=Role.MANAGER)


@pytest.fixture
def client(manager):
    c = APIClient()
    c.force_authenticate(user=manager)
    return c


def make_order(location, total_paisa, status=OrderStatus.FULFILLED, created_at=None):
    order = Order.objects.create(
        fulfilled_location=location,
        source=OrderSource.COUNTER,
        status=status,
        total_paisa=total_paisa,
    )
    if created_at is not None:
        # created_at is auto_now_add — reset it directly for date-range coverage.
        Order.objects.filter(pk=order.pk).update(created_at=created_at)
        order.refresh_from_db()
    return order


# ── Summary aggregate ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_summary_aggregates_all_orders_not_just_a_page(client, outlet_a):
    for _ in range(60):          # more than one page
        make_order(outlet_a, 1000)

    res = client.get('/api/orders/summary/')
    assert res.status_code == 200
    assert res.data['order_count'] == 60
    assert res.data['gross_paisa'] == 60_000


@pytest.mark.django_db
def test_summary_excludes_cancelled_orders(client, outlet_a):
    make_order(outlet_a, 5000, status=OrderStatus.FULFILLED)
    make_order(outlet_a, 9999, status=OrderStatus.CANCELLED)

    res = client.get('/api/orders/summary/')
    assert res.data['order_count'] == 1
    assert res.data['gross_paisa'] == 5000


@pytest.mark.django_db
def test_summary_of_empty_set_is_zero_not_null(client):
    res = client.get('/api/orders/summary/')
    assert res.data == {'order_count': 0, 'gross_paisa': 0}


# ── Filters ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_location_filter(client, outlet_a, outlet_b):
    make_order(outlet_a, 1000)
    make_order(outlet_b, 2000)

    res = client.get('/api/orders/summary/', {'fulfilled_location': outlet_b.pk})
    assert res.data['order_count'] == 1
    assert res.data['gross_paisa'] == 2000


@pytest.mark.django_db
def test_date_range_filter_is_inclusive(client, outlet_a):
    today = timezone.now()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    make_order(outlet_a, 1000, created_at=today)
    make_order(outlet_a, 2000, created_at=yesterday)
    make_order(outlet_a, 4000, created_at=last_week)

    # localdate: created_at__date compares in TIME_ZONE (Asia/Kathmandu), so the
    # UTC .date() would be one day behind between 18:15 and 24:00 UTC.
    res = client.get('/api/orders/summary/', {
        'date_from': timezone.localdate(yesterday).isoformat(),
        'date_to': timezone.localdate(today).isoformat(),
    })
    assert res.data['order_count'] == 2
    assert res.data['gross_paisa'] == 3000


@pytest.mark.django_db
def test_today_only(client, outlet_a):
    today = timezone.now()
    make_order(outlet_a, 1500, created_at=today)
    make_order(outlet_a, 8000, created_at=today - timedelta(days=3))

    res = client.get('/api/orders/summary/', {
        'date_from': timezone.localdate(today).isoformat(),
        'date_to': timezone.localdate(today).isoformat(),
    })
    assert res.data['order_count'] == 1
    assert res.data['gross_paisa'] == 1500


@pytest.mark.django_db
def test_list_endpoint_honours_the_same_filters(client, outlet_a, outlet_b):
    make_order(outlet_a, 1000)
    make_order(outlet_b, 2000)

    res = client.get('/api/orders/', {'fulfilled_location': outlet_a.pk})
    results = res.data['results'] if 'results' in res.data else res.data
    assert len(results) == 1
    assert results[0]['fulfilled_location'] == outlet_a.pk


@pytest.mark.django_db
def test_outlet_manager_scoping_wins_over_location_param(outlet_a, outlet_b):
    """An outlet manager must not be able to read another outlet by passing its id."""
    make_order(outlet_a, 1000)
    make_order(outlet_b, 2000)

    om = User.objects.create_user(username='om_report', password='x', role=Role.OUTLET_MANAGER)
    om.assigned_locations.add(outlet_a)
    c = APIClient()
    c.force_authenticate(user=om)

    res = c.get('/api/orders/summary/', {'fulfilled_location': outlet_b.pk})
    assert res.data['order_count'] == 0
    assert res.data['gross_paisa'] == 0


# ── Rule 7: who may read the revenue aggregate ────────────────────────────────

@pytest.mark.django_db
def test_cashier_is_denied_the_revenue_summary(outlet_a):
    """
    A cashier rings up sales but must never read org-wide takings.
    The action must not inherit the viewset's sales-write permissions.
    """
    make_order(outlet_a, 5000)

    cashier = User.objects.create_user(username='till_cashier', password='x', role=Role.CASHIER)
    c = APIClient()
    c.force_authenticate(user=cashier)

    assert c.get('/api/orders/summary/').status_code == 403
    # …while still being able to do their actual job.
    assert c.get('/api/orders/').status_code == 200


@pytest.mark.django_db
def test_customer_is_denied_the_revenue_summary(outlet_a):
    make_order(outlet_a, 5000)

    customer = User.objects.create_user(username='shopper', password='x', role=Role.CUSTOMER)
    c = APIClient()
    c.force_authenticate(user=customer)

    assert c.get('/api/orders/summary/').status_code == 403


@pytest.mark.django_db
def test_customer_without_linked_customer_record_sees_no_walk_in_orders(outlet_a):
    """
    Walk-in orders have customer=NULL. A customer-role user with no linked customer
    must match none of them, not all of them.
    """
    make_order(outlet_a, 5000)   # walk-in: customer is NULL

    orphan = User.objects.create_user(username='orphan', password='x', role=Role.CUSTOMER)
    c = APIClient()
    c.force_authenticate(user=orphan)

    res = c.get('/api/orders/')
    results = res.data['results'] if 'results' in res.data else res.data
    assert results == []


# ── Malformed filters are rejected, not 500s ──────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize('params', [
    {'date_from': 'banana'},
    {'date_to': '2026-13-45'},
    {'fulfilled_location': 'abc'},
    {'status': 'not_a_status'},
])
def test_malformed_filters_return_400(client, params):
    assert client.get('/api/orders/summary/', params).status_code == 400
