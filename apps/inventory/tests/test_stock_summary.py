"""
Proves: stock_matrix() agrees with current_stock() for every pair it reports
(Rule 1 — stock is always SUM of the ledger, never a stored column), and that
/api/stock/summary/ scopes rows to an outlet manager's assigned locations.
"""
from decimal import Decimal

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Product, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.queries import current_stock, stock_matrix
from apps.locations.models import Location, LocationType


@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='OL', type=LocationType.OUTLET)


@pytest.fixture
def user(db):
    return User.objects.create_user(username='summary_user', password='x')


@pytest.fixture
def chicken(db):
    return Product.objects.create(name='Chicken', uom=UoM.KG)


@pytest.fixture
def wings(db):
    return Product.objects.create(name='Wings', uom=UoM.KG)


def add_stock(product, location, user, qty_kg, qty_pieces=0):
    StockMovement.objects.create(
        product=product, location=location,
        type=MovementType.PRODUCTION if qty_kg > 0 else MovementType.SALE,
        qty_kg=Decimal(str(qty_kg)), qty_pieces=qty_pieces, user=user,
    )


# ── The invariant ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_matrix_agrees_with_current_stock_for_every_pair(chicken, wings, warehouse, outlet, user):
    add_stock(chicken, warehouse, user, 20)
    add_stock(chicken, warehouse, user, -7)
    add_stock(chicken, outlet, user, 4)
    add_stock(wings, warehouse, user, 12, qty_pieces=30)

    rows = stock_matrix()
    assert len(rows) == 3
    for row in rows:
        expected = current_stock(row['product'], row['location'])
        assert row['qty_kg'] == expected['qty_kg']
        assert row['qty_pieces'] == expected['qty_pieces']


@pytest.mark.django_db
def test_net_stock_not_gross(chicken, warehouse, user):
    add_stock(chicken, warehouse, user, 15)
    add_stock(chicken, warehouse, user, -9)

    rows = stock_matrix()
    assert len(rows) == 1
    assert rows[0]['qty_kg'] == Decimal('6.000')


@pytest.mark.django_db
def test_sold_out_pair_still_reported_as_zero(chicken, warehouse, user):
    add_stock(chicken, warehouse, user, 5)
    add_stock(chicken, warehouse, user, -5)

    rows = stock_matrix()
    assert len(rows) == 1
    assert rows[0]['qty_kg'] == Decimal('0.000')


@pytest.mark.django_db
def test_location_filter_narrows_rows(chicken, warehouse, outlet, user):
    add_stock(chicken, warehouse, user, 10)
    add_stock(chicken, outlet, user, 3)

    rows = stock_matrix(location_ids=[outlet.pk])
    assert len(rows) == 1
    assert rows[0]['location'] == outlet.pk
    assert rows[0]['qty_kg'] == Decimal('3.000')


# ── The endpoint ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(LOW_STOCK_THRESHOLD_KG=10)
def test_summary_endpoint_flags_low_stock(chicken, wings, warehouse, user):
    add_stock(chicken, warehouse, user, 50)   # healthy
    add_stock(wings, warehouse, user, 2)      # low

    user.role = Role.MANAGER
    user.save()
    client = APIClient()
    client.force_authenticate(user=user)

    res = client.get('/api/stock/summary/')
    assert res.status_code == 200
    assert res.data['threshold_kg'] == 10

    by_product = {r['product']: r for r in res.data['results']}
    assert by_product[chicken.pk]['low_stock'] is False
    assert by_product[wings.pk]['low_stock'] is True


@pytest.mark.django_db
def test_summary_scopes_outlet_manager_to_assigned_locations(chicken, warehouse, outlet, user):
    add_stock(chicken, warehouse, user, 10)
    add_stock(chicken, outlet, user, 3)

    manager = User.objects.create_user(username='om', password='x', role='outlet_manager')
    manager.assigned_locations.add(outlet)

    client = APIClient()
    client.force_authenticate(user=manager)

    res = client.get('/api/stock/summary/')
    assert res.status_code == 200
    locations = {r['location'] for r in res.data['results']}
    assert locations == {outlet.pk}
