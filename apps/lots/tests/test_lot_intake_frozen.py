"""EF-10: a lot's intake figures are locked once it leaves 'arrival'."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.lots.models import Lot, LotStatus
from apps.locations.models import Location, LocationType


@pytest.fixture
def farm(db):
    return Location.objects.create(name='Frozen Farm', type=LocationType.FARM)


@pytest.fixture
def lot(db, farm):
    return Lot.objects.create(
        code='LOT-FROZEN', source_type='external',
        arrival_location=farm, live_weight_kg='50.000', bird_count=10,
    )


@pytest.fixture
def warehouse(db):
    return User.objects.create_user(username='wh_frozen', password='x', role=Role.WAREHOUSE)


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_intake_editable_while_in_arrival(lot, warehouse):
    r = api(warehouse).patch(f'/api/lots/{lot.pk}/', {'live_weight_kg': '51.000'}, format='json')
    assert r.status_code == 200, r.data
    lot.refresh_from_db()
    assert str(lot.live_weight_kg) == '51.000'


@pytest.mark.django_db
def test_intake_frozen_after_leaving_arrival(lot, warehouse):
    lot.transition(LotStatus.GRADING)
    for field, value in [('live_weight_kg', '99.000'), ('bird_count', 999),
                         ('accumulated_cost_paisa', 12345)]:
        r = api(warehouse).patch(f'/api/lots/{lot.pk}/', {field: value}, format='json')
        assert r.status_code == 400, f'{field} should be locked: {r.data}'
    lot.refresh_from_db()
    assert str(lot.live_weight_kg) == '50.000'
    assert lot.bird_count == 10


@pytest.mark.django_db
def test_non_frozen_field_still_editable_after_arrival(lot, warehouse):
    """Freezing the intake figures must not lock everything — e.g. supplier stays editable."""
    lot.transition(LotStatus.GRADING)
    r = api(warehouse).patch(f'/api/lots/{lot.pk}/', {'code': 'LOT-FROZEN-2'}, format='json')
    assert r.status_code == 200, r.data
