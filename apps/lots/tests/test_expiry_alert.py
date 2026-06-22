"""
Proves: expiry_alert() flags lots in pre-settlement statuses that are older
than LOT_EXPIRY_ALERT_DAYS, and ignores settled lots and fresh lots.
"""
import datetime

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.locations.models import Location, LocationType
from apps.lots.models import Lot, LotStatus
from apps.lots.tasks import expiry_alert


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def location(db):
    return Location.objects.create(name='Farm', type=LocationType.WAREHOUSE)


def make_lot(location, status, days_old, code_suffix=''):
    lot = Lot.objects.create(
        code=f'LOT-{status}-{days_old}d{code_suffix}',
        source_type='own',
        arrival_location=location,
        live_weight_kg='100.000',
        bird_count=100,
        status=status,
    )
    # backdate created_at
    Lot.objects.filter(pk=lot.pk).update(
        created_at=timezone.now() - datetime.timedelta(days=days_old)
    )
    return lot


# ── Core behaviour ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=3)
def test_stale_arrival_lot_is_flagged(location):
    make_lot(location, LotStatus.ARRIVAL, days_old=5)
    result = expiry_alert()
    assert len(result['alerts']) == 1


@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=3)
def test_fresh_lot_is_not_flagged(location):
    make_lot(location, LotStatus.ARRIVAL, days_old=1)
    result = expiry_alert()
    assert result['alerts'] == []


@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=3)
def test_settlement_lot_is_not_flagged(location):
    make_lot(location, LotStatus.SETTLEMENT, days_old=10)
    result = expiry_alert()
    assert result['alerts'] == []


@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=3)
def test_sale_status_not_flagged(location):
    make_lot(location, LotStatus.SALE, days_old=10)
    result = expiry_alert()
    assert result['alerts'] == []


@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=3)
def test_all_stale_pre_settlement_statuses_flagged(location):
    stale_statuses = [
        LotStatus.ARRIVAL, LotStatus.GRADING, LotStatus.STORAGE,
        LotStatus.SLAUGHTER, LotStatus.PACKAGING,
    ]
    for i, status in enumerate(stale_statuses):
        make_lot(location, status, days_old=5, code_suffix=str(i))

    result = expiry_alert()
    assert len(result['alerts']) == len(stale_statuses)


@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=3)
def test_alert_contains_lot_code_and_status(location):
    make_lot(location, LotStatus.GRADING, days_old=4)
    result = expiry_alert()
    alert = result['alerts'][0]
    assert 'lot_code' in alert
    assert alert['status'] == LotStatus.GRADING
    assert alert['age_days'] >= 4


@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=7)
def test_custom_threshold_respected(location):
    make_lot(location, LotStatus.ARRIVAL, days_old=5)  # within 7-day window — no alert
    result = expiry_alert()
    assert result['alerts'] == []
    assert result['alert_days'] == 7


@pytest.mark.django_db
@override_settings(LOT_EXPIRY_ALERT_DAYS=3)
def test_returns_alert_days_in_result(location):
    result = expiry_alert()
    assert result['alert_days'] == 3
