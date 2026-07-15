"""
The manual /movements/ endpoint may only post corrections (adjustment/wastage),
wastage is manager-only, and flow-owned types cannot be forged there.
"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Product, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.queries import current_stock
from apps.locations.models import Location, LocationType


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Guard Outlet', type=LocationType.OUTLET)


@pytest.fixture
def product(db):
    return Product.objects.create(name='Guard Chicken', uom=UoM.KG)


@pytest.fixture
def warehouse(db):
    return User.objects.create_user(username='guard_wh', password='x', role=Role.WAREHOUSE)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='guard_mgr', password='x', role=Role.MANAGER)


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def seed(product, outlet, user, kg='10'):
    StockMovement.objects.create(
        product=product, location=outlet, type=MovementType.PRODUCTION,
        qty_kg=Decimal(kg), user=user,
    )


def test_warehouse_can_post_wastage(product, outlet, warehouse, manager):
    # Warehouse is the batch recorder — allowed to write off spoilage.
    seed(product, outlet, manager)
    r = api(warehouse).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk, 'type': 'wastage', 'qty_kg': '-5.000',
    }, format='json')
    assert r.status_code == 201
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('5')


def test_manager_can_post_wastage(product, outlet, manager):
    seed(product, outlet, manager)
    r = api(manager).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk, 'type': 'wastage', 'qty_kg': '-5.000',
    }, format='json')
    assert r.status_code == 201
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('5')


def test_cashier_cannot_post_wastage(product, outlet, manager, db):
    seed(product, outlet, manager)
    cashier = User.objects.create_user(username='guard_cash', password='x', role=Role.CASHIER)
    r = api(cashier).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk, 'type': 'wastage', 'qty_kg': '-5.000',
    }, format='json')
    # cashier has no inventory access at all → 403 (not even reaching the serializer)
    assert r.status_code == 403


def test_warehouse_can_post_adjustment(product, outlet, warehouse, manager):
    seed(product, outlet, manager)
    r = api(warehouse).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk, 'type': 'adjustment', 'qty_kg': '-1.000',
    }, format='json')
    assert r.status_code == 201


@pytest.mark.parametrize('mtype', ['sale', 'transfer', 'return'])
def test_flow_owned_types_rejected(product, outlet, manager, mtype):
    """sale/transfer/return have guarded flows of their own; the manual endpoint
    must refuse them so those guards cannot be bypassed."""
    seed(product, outlet, manager)
    r = api(manager).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk, 'type': mtype, 'qty_kg': '1.000',
    }, format='json')
    assert r.status_code == 400


def test_production_allowed(product, outlet, manager):
    """Own-production output has no dedicated endpoint in Phase 1, so it is
    posted here directly."""
    r = api(manager).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk, 'type': 'production', 'qty_kg': '5.000',
    }, format='json')
    assert r.status_code == 201


def test_empty_movement_rejected(product, outlet, manager):
    r = api(manager).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk, 'type': 'adjustment',
        'qty_kg': '0', 'qty_pieces': 0,
    }, format='json')
    assert r.status_code == 400
