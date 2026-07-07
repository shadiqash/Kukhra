"""
Tests for unique_open_session_per_counter constraint:
only one CashierSession with closed_at=None is allowed per counter.
"""
import pytest
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import CashierSession


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Baneshwor', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Counter A')


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='cashier_sc', password='x', role=Role.CASHIER)


@pytest.fixture
def cashier2(db):
    return User.objects.create_user(username='cashier_sc2', password='x', role=Role.CASHIER)


@pytest.mark.django_db
def test_two_open_sessions_same_counter_raises(counter, cashier, cashier2):
    CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )
    with pytest.raises(IntegrityError):
        CashierSession.objects.create(
            counter=counter, cashier=cashier2,
            opening_float_paisa=500000, opened_at=timezone.now(),
        )


@pytest.mark.django_db
def test_close_session_then_open_new_allowed(counter, cashier, cashier2):
    s1 = CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )
    s1.close(closing_counted_paisa=510000)

    s2 = CashierSession.objects.create(
        counter=counter, cashier=cashier2,
        opening_float_paisa=510000, opened_at=timezone.now(),
    )
    assert s2.pk is not None
    assert CashierSession.objects.filter(counter=counter, closed_at__isnull=True).count() == 1


@pytest.mark.django_db
def test_open_sessions_different_counters_allowed(outlet, cashier, cashier2):
    counter_a = Counter.objects.create(location=outlet, name='Counter A')
    counter_b = Counter.objects.create(location=outlet, name='Counter B')

    s1 = CashierSession.objects.create(
        counter=counter_a, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )
    s2 = CashierSession.objects.create(
        counter=counter_b, cashier=cashier2,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )
    assert s1.pk is not None
    assert s2.pk is not None


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_api_open_session_rejects_duplicate_counter_with_400(counter, cashier, cashier2):
    """
    POST /api/sessions/ against a counter with an existing open session must
    return a clean 400 (via CashierSessionSerializer.validate_counter), not a
    raw 500 IntegrityError from the DB constraint.
    """
    CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )

    resp = api(cashier2).post('/api/sessions/', {
        'counter': counter.id,
        'opening_float_paisa': 300000,
    })

    assert resp.status_code == 400
    assert 'counter' in resp.data
    assert CashierSession.objects.filter(counter=counter, closed_at__isnull=True).count() == 1


@pytest.mark.django_db
def test_api_open_session_succeeds_when_none_open(counter, cashier):
    resp = api(cashier).post('/api/sessions/', {
        'counter': counter.id,
        'opening_float_paisa': 500000,
    })

    assert resp.status_code == 201
    assert CashierSession.objects.filter(counter=counter, closed_at__isnull=True).count() == 1


@pytest.mark.django_db
def test_api_open_session_allowed_after_close(counter, cashier, cashier2):
    s1 = CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )

    close_resp = api(cashier).post(f'/api/sessions/{s1.id}/close/', {
        'closing_counted_paisa': 510000,
    })
    assert close_resp.status_code == 200

    open_resp = api(cashier2).post('/api/sessions/', {
        'counter': counter.id,
        'opening_float_paisa': 510000,
    })
    assert open_resp.status_code == 201


@pytest.mark.django_db
def test_api_close_already_closed_session_returns_400(counter, cashier):
    session = CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )
    session.close(closing_counted_paisa=510000)

    resp = api(cashier).post(f'/api/sessions/{session.id}/close/', {
        'closing_counted_paisa': 510000,
    })
    assert resp.status_code == 400


@pytest.mark.django_db
def test_api_cashier_cannot_see_other_cashiers_sessions(counter, cashier, cashier2):
    CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=500000, opened_at=timezone.now(),
    )

    resp = api(cashier2).get('/api/sessions/')
    assert resp.status_code == 200
    ids = [row['id'] for row in resp.data.get('results', resp.data)]
    assert not ids
