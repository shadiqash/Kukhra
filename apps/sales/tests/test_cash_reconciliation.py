"""
Cash reconciliation: expected cash vs counted cash per shift.

This is the shrinkage number, so the arithmetic has to be exactly right —
a fabricated variance is worse than none, because it accuses someone.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import (
    CashierSession, Order, OrderSource, OrderStatus, Payment, PaymentMethod,
)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Recon Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Till 1')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='recon_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='recon_manager', password='x', role=Role.MANAGER)


@pytest.fixture
def client(manager):
    c = APIClient()
    c.force_authenticate(user=manager)
    return c


@pytest.fixture
def session(db, counter, cashier):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=100_000,       # Rs 1,000 float
        opened_at=timezone.now(),
    )


def sale(session, outlet, total_paisa, method=PaymentMethod.CASH, status=OrderStatus.FULFILLED):
    order = Order.objects.create(
        fulfilled_location=outlet, session=session, source=OrderSource.COUNTER,
        status=status, total_paisa=total_paisa,
    )
    Payment.objects.create(order=order, method=method, amount_paisa=total_paisa)
    return order


def row_for(client, session):
    res = client.get('/api/sessions/reconciliation/')
    assert res.status_code == 200
    return next(r for r in res.data['results'] if r['id'] == session.pk)


# ── The variance arithmetic ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_balanced_drawer_has_zero_variance(client, session, outlet):
    sale(session, outlet, 50_000)
    sale(session, outlet, 30_000)
    session.close(closing_counted_paisa=180_000)   # 100,000 float + 80,000 cash

    row = row_for(client, session)
    assert row['expected_cash_paisa'] == 180_000
    assert row['closing_counted_paisa'] == 180_000
    assert row['variance_paisa'] == 0


@pytest.mark.django_db
def test_short_drawer_reports_negative_variance(client, session, outlet):
    sale(session, outlet, 50_000)
    session.close(closing_counted_paisa=145_000)   # expected 150,000 — Rs 50 missing

    row = row_for(client, session)
    assert row['variance_paisa'] == -5_000


@pytest.mark.django_db
def test_over_drawer_reports_positive_variance(client, session, outlet):
    sale(session, outlet, 50_000)
    session.close(closing_counted_paisa=155_000)

    row = row_for(client, session)
    assert row['variance_paisa'] == 5_000


@pytest.mark.django_db
def test_non_cash_payments_are_not_expected_in_the_drawer(client, session, outlet):
    """A card sale must not make the drawer look short."""
    sale(session, outlet, 50_000, method=PaymentMethod.CASH)
    sale(session, outlet, 90_000, method=PaymentMethod.CARD)
    session.close(closing_counted_paisa=150_000)   # float + cash only

    row = row_for(client, session)
    assert row['cash_sales_paisa'] == 50_000
    assert row['expected_cash_paisa'] == 150_000
    assert row['variance_paisa'] == 0
    # …but the shift's takings still include the card sale.
    assert row['sales_total_paisa'] == 140_000


@pytest.mark.django_db
def test_cancelled_orders_do_not_fabricate_a_variance(client, session, outlet):
    """
    A cancelled order never put money in the till. Counting it as expected cash
    would accuse the cashier of being short by its value.
    """
    sale(session, outlet, 50_000)
    sale(session, outlet, 70_000, status=OrderStatus.CANCELLED)
    session.close(closing_counted_paisa=150_000)

    row = row_for(client, session)
    assert row['cash_sales_paisa'] == 50_000
    assert row['variance_paisa'] == 0
    assert row['sales_count'] == 1


@pytest.mark.django_db
def test_open_shift_has_no_variance_yet(client, session, outlet):
    """An open drawer has not been counted — variance must be null, not zero."""
    sale(session, outlet, 50_000)

    row = row_for(client, session)
    assert row['is_open'] is True
    assert row['closing_counted_paisa'] is None
    assert row['variance_paisa'] is None
    assert row['expected_cash_paisa'] == 150_000


@pytest.mark.django_db
def test_totals_are_not_inflated_by_multiple_payments(client, session, outlet):
    """
    Guard against join multiplication: an order with a split payment must not
    have its total counted twice.
    """
    order = Order.objects.create(
        fulfilled_location=outlet, session=session, source=OrderSource.COUNTER,
        status=OrderStatus.FULFILLED, total_paisa=100_000,
    )
    Payment.objects.create(order=order, method=PaymentMethod.CASH, amount_paisa=60_000)
    Payment.objects.create(order=order, method=PaymentMethod.CARD, amount_paisa=40_000)

    row = row_for(client, session)
    assert row['sales_count'] == 1
    assert row['sales_total_paisa'] == 100_000     # not 200,000
    assert row['cash_sales_paisa'] == 60_000


# ── Rule 7: who may see the till ──────────────────────────────────────────────

@pytest.mark.django_db
def test_cashier_cannot_read_the_reconciliation_report(session, cashier):
    """A cashier must not audit their own drawer."""
    c = APIClient()
    c.force_authenticate(user=cashier)
    assert c.get('/api/sessions/reconciliation/').status_code == 403


@pytest.mark.django_db
def test_cashier_z_report_is_a_blind_count(session, outlet, cashier):
    """
    The cashier still gets their Z-report — what they sold, and how it was paid —
    but never the drawer audit. Showing a cashier their own variance tells them
    exactly how much they could take without it showing up.
    """
    sale(session, outlet, 50_000)
    session.close(closing_counted_paisa=145_000)   # Rs 50 short

    c = APIClient()
    c.force_authenticate(user=cashier)
    res = c.get(f'/api/sessions/{session.pk}/summary/')

    assert res.status_code == 200
    assert res.data['sales_total_paisa'] == 50_000     # they can still close their till
    assert 'payment_breakdown' in res.data
    for audit_field in ('variance_paisa', 'expected_cash_paisa',
                        'cash_sales_paisa', 'closing_counted_paisa'):
        assert audit_field not in res.data, f'cashier can see {audit_field}'


@pytest.mark.django_db
def test_manager_z_report_shows_the_variance(client, session, outlet):
    sale(session, outlet, 50_000)
    session.close(closing_counted_paisa=145_000)

    res = client.get(f'/api/sessions/{session.pk}/summary/')
    assert res.data['variance_paisa'] == -5_000
    assert res.data['expected_cash_paisa'] == 150_000


@pytest.mark.django_db
def test_outlet_manager_sees_only_their_own_outlet(session, outlet, cashier):
    other = Location.objects.create(name='Other Outlet', type=LocationType.OUTLET)
    other_counter = Counter.objects.create(location=other, name='Other Till')
    CashierSession.objects.create(
        counter=other_counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )

    om = User.objects.create_user(username='recon_om', password='x', role=Role.OUTLET_MANAGER)
    om.assigned_locations.add(outlet)
    c = APIClient()
    c.force_authenticate(user=om)

    res = c.get('/api/sessions/reconciliation/')
    assert res.status_code == 200
    assert {r['location'] for r in res.data['results']} == {outlet.pk}
