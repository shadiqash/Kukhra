import pytest

from apps.lots.models import Lot, LotStatus, VALID_TRANSITIONS
from apps.locations.models import Location, LocationType


@pytest.fixture
def farm(db):
    return Location.objects.create(name='Test Farm', type=LocationType.FARM)


@pytest.fixture
def lot(db, farm):
    return Lot.objects.create(
        code='LOT-001', source_type='external',
        arrival_location=farm, live_weight_kg='50.000', bird_count=10,
    )


@pytest.mark.django_db
def test_initial_status_is_arrival(lot):
    assert lot.status == LotStatus.ARRIVAL


@pytest.mark.django_db
def test_valid_transition_arrival_to_grading(lot):
    lot.transition(LotStatus.GRADING)
    lot.refresh_from_db()
    assert lot.status == LotStatus.GRADING


@pytest.mark.django_db
def test_invalid_transition_raises(lot):
    with pytest.raises(ValueError, match='Illegal lot transition'):
        lot.transition(LotStatus.SETTLEMENT)


@pytest.mark.django_db
def test_transition_to_self_raises(lot):
    with pytest.raises(ValueError):
        lot.transition(LotStatus.ARRIVAL)


@pytest.mark.django_db
def test_settlement_is_terminal(lot):
    for step in [LotStatus.GRADING, LotStatus.SLAUGHTER, LotStatus.PACKAGING,
                 LotStatus.SALE, LotStatus.SETTLEMENT]:
        lot.transition(step)
    assert VALID_TRANSITIONS[LotStatus.SETTLEMENT] == set()
    with pytest.raises(ValueError):
        lot.transition(LotStatus.ARRIVAL)
