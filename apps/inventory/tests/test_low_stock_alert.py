"""
Proves: low_stock_alert() returns only (product, location) pairs whose net
stock falls below LOW_STOCK_THRESHOLD_KG, and respects the threshold setting.
"""
from decimal import Decimal

import pytest
from django.test import override_settings

from apps.accounts.models import User
from apps.catalog.models import Product, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.tasks import low_stock_alert
from apps.locations.models import Location, LocationType


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='OL', type=LocationType.OUTLET)


@pytest.fixture
def user(db):
    return User.objects.create_user(username='alert_user', password='x')


@pytest.fixture
def chicken(db):
    return Product.objects.create(name='Chicken', uom=UoM.KG)


@pytest.fixture
def wings(db):
    return Product.objects.create(name='Wings', uom=UoM.KG)


def add_stock(product, location, user, qty_kg):
    StockMovement.objects.create(
        product=product, location=location,
        type=MovementType.PRODUCTION if qty_kg > 0 else MovementType.SALE,
        qty_kg=Decimal(str(qty_kg)), user=user,
    )


# ── Core behaviour ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=10)
def test_no_alerts_when_stock_above_threshold(chicken, warehouse, user):
    add_stock(chicken, warehouse, user, 20)
    result = low_stock_alert()
    assert result['alerts'] == []


@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=10)
def test_alert_when_stock_below_threshold(chicken, warehouse, user):
    add_stock(chicken, warehouse, user, 5)
    result = low_stock_alert()
    assert len(result['alerts']) == 1
    assert result['alerts'][0]['product_id'] == chicken.pk
    assert result['alerts'][0]['location_id'] == warehouse.pk
    assert result['alerts'][0]['total_kg'] == pytest.approx(5.0)


@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=10)
def test_threshold_is_exclusive(chicken, warehouse, user):
    # stock exactly at threshold is NOT below it
    add_stock(chicken, warehouse, user, 10)
    result = low_stock_alert()
    assert result['alerts'] == []


@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=10)
def test_multiple_pairs_reported_independently(chicken, wings, warehouse, outlet, user):
    add_stock(chicken, warehouse, user, 3)   # below — alert
    add_stock(wings,   outlet,   user, 50)  # above — no alert
    add_stock(wings,   warehouse, user, 2)  # below — alert

    result = low_stock_alert()
    assert len(result['alerts']) == 2


@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=10)
def test_net_stock_used_not_gross(chicken, warehouse, user):
    add_stock(chicken, warehouse, user, 15)
    add_stock(chicken, warehouse, user, -9)   # net = 6, below threshold
    result = low_stock_alert()
    assert len(result['alerts']) == 1
    assert result['alerts'][0]['total_kg'] == pytest.approx(6.0)


@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=25)
def test_custom_threshold_respected(chicken, warehouse, user):
    add_stock(chicken, warehouse, user, 20)   # below 25 — should alert
    result = low_stock_alert()
    assert len(result['alerts']) == 1
    assert result['threshold_kg'] == 25


@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=10)
def test_returns_threshold_in_result(chicken, warehouse, user):
    result = low_stock_alert()
    assert result['threshold_kg'] == 10
