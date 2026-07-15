"""
Proves a transfer actually moves goods.

Dispatch writes negative transfer movements at from_location; confirm_receipt
mirrors them positive at to_location. Between the two, the stock is in transit:
gone from the origin, not yet at the destination. Total stock across both
locations must never be created or destroyed by a transfer.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Product, UoM
from apps.inventory.models import MovementType, StockMovement, StockTransfer, TransferStatus
from apps.inventory.queries import current_stock
from apps.locations.models import Location, LocationType


@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='OL', type=LocationType.OUTLET)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='xfer_manager', password='x', role=Role.MANAGER)


@pytest.fixture
def client(manager):
    c = APIClient()
    c.force_authenticate(user=manager)
    return c


@pytest.fixture
def chicken(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG)


def stock_in(product, location, user, qty_kg, qty_pieces=0):
    StockMovement.objects.create(
        product=product, location=location, type=MovementType.PRODUCTION,
        qty_kg=Decimal(str(qty_kg)), qty_pieces=qty_pieces, user=user,
    )


def dispatch_payload(warehouse, outlet, product, qty_kg):
    return {
        'from_location': warehouse.pk,
        'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
        'lines': [{'product': product.pk, 'qty_kg': str(qty_kg)}],
    }


# ── Stock actually moves ──────────────────────────────────────────────────────

@pytest.mark.django_db
def test_dispatch_removes_stock_from_origin(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 100)

    res = client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 30), format='json')
    assert res.status_code == 201

    assert current_stock(chicken.pk, warehouse.pk)['qty_kg'] == Decimal('70.000')
    # Not yet arrived — it is on the van.
    assert current_stock(chicken.pk, outlet.pk)['qty_kg'] == Decimal('0')


@pytest.mark.django_db
def test_confirm_receipt_lands_stock_at_destination(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 100)
    res = client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 30), format='json')
    transfer_id = res.data['id']

    res = client.post(f'/api/transfers/{transfer_id}/confirm-receipt/')
    assert res.status_code == 200

    assert current_stock(chicken.pk, warehouse.pk)['qty_kg'] == Decimal('70.000')
    assert current_stock(chicken.pk, outlet.pk)['qty_kg'] == Decimal('30.000')


@pytest.mark.django_db
def test_transfer_conserves_total_stock(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 100)
    res = client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 40), format='json')
    client.post(f'/api/transfers/{res.data["id"]}/confirm-receipt/')

    total = (current_stock(chicken.pk, warehouse.pk)['qty_kg']
             + current_stock(chicken.pk, outlet.pk)['qty_kg'])
    assert total == Decimal('100.000')


@pytest.mark.django_db
def test_pieces_move_too(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 0, qty_pieces=50)

    res = client.post('/api/transfers/', {
        'from_location': warehouse.pk,
        'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
        'lines': [{'product': chicken.pk, 'qty_pieces': 20}],
    }, format='json')
    assert res.status_code == 201
    client.post(f'/api/transfers/{res.data["id"]}/confirm-receipt/')

    assert current_stock(chicken.pk, warehouse.pk)['qty_pieces'] == 30
    assert current_stock(chicken.pk, outlet.pk)['qty_pieces'] == 20


# ── You cannot ship what you do not have ──────────────────────────────────────

@pytest.mark.django_db
def test_cannot_dispatch_more_than_on_hand(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 10)

    res = client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 25), format='json')
    assert res.status_code == 400
    assert 'Insufficient stock' in str(res.data)


@pytest.mark.django_db
def test_two_lines_of_the_same_product_are_summed_against_stock(client, warehouse, outlet, chicken, manager):
    """
    60 + 60 against 100 on hand must be rejected. Checking each line separately
    against the same snapshot would pass both and drive the ledger to -20 kg.
    """
    stock_in(chicken, warehouse, manager, 100)

    res = client.post('/api/transfers/', {
        'from_location': warehouse.pk,
        'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
        'lines': [
            {'product': chicken.pk, 'qty_kg': '60'},
            {'product': chicken.pk, 'qty_kg': '60'},
        ],
    }, format='json')

    assert res.status_code == 400
    assert 'Insufficient stock' in str(res.data)
    assert current_stock(chicken.pk, warehouse.pk)['qty_kg'] == Decimal('100.000')


@pytest.mark.django_db
def test_two_lines_of_the_same_product_within_stock_are_allowed(client, warehouse, outlet, chicken, manager):
    """The fold must not over-reject: 30 + 30 against 100 is fine, and both ship."""
    stock_in(chicken, warehouse, manager, 100)

    res = client.post('/api/transfers/', {
        'from_location': warehouse.pk,
        'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
        'lines': [
            {'product': chicken.pk, 'qty_kg': '30'},
            {'product': chicken.pk, 'qty_kg': '30'},
        ],
    }, format='json')

    assert res.status_code == 201
    assert current_stock(chicken.pk, warehouse.pk)['qty_kg'] == Decimal('40.000')


@pytest.mark.django_db
def test_failed_dispatch_leaves_no_transfer_and_no_movements(client, warehouse, outlet, chicken, manager):
    """The header must roll back with the movements — no phantom empty transfers."""
    stock_in(chicken, warehouse, manager, 10)
    before = StockMovement.objects.count()

    client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 25), format='json')

    assert StockTransfer.objects.count() == 0
    assert StockMovement.objects.count() == before
    assert current_stock(chicken.pk, warehouse.pk)['qty_kg'] == Decimal('10.000')


# ── Shape guards ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_transfer_without_lines_is_rejected(client, warehouse, outlet):
    res = client.post('/api/transfers/', {
        'from_location': warehouse.pk,
        'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
        'lines': [],
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_cannot_transfer_to_the_same_location(client, warehouse, chicken, manager):
    stock_in(chicken, warehouse, manager, 100)
    res = client.post('/api/transfers/', dispatch_payload(warehouse, warehouse, chicken, 10), format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_zero_quantity_line_is_rejected(client, warehouse, outlet, chicken):
    res = client.post('/api/transfers/', {
        'from_location': warehouse.pk,
        'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
        'lines': [{'product': chicken.pk, 'qty_kg': '0'}],
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_receipt_cannot_be_confirmed_twice(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 100)
    res = client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 30), format='json')
    tid = res.data['id']

    assert client.post(f'/api/transfers/{tid}/confirm-receipt/').status_code == 200
    assert client.post(f'/api/transfers/{tid}/confirm-receipt/').status_code == 400

    # Stock must not double-land.
    assert current_stock(chicken.pk, outlet.pk)['qty_kg'] == Decimal('30.000')


@pytest.mark.django_db
def test_stale_instance_cannot_double_land_the_stock(client, warehouse, outlet, chicken, manager):
    """
    Two concurrent confirmations each hold their own instance, both reading
    status='dispatched'. If the guard trusts that in-memory value instead of
    re-reading the row under a lock, the movements are mirrored twice and 30 kg
    becomes 60 kg at the destination — permanently, since the ledger is append-only.
    """
    stock_in(chicken, warehouse, manager, 100)
    res = client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 30), format='json')
    tid = res.data['id']

    first = StockTransfer.objects.get(pk=tid)
    second = StockTransfer.objects.get(pk=tid)   # stale handle, as a racing request would hold

    first.confirm_receipt(user=manager)
    with pytest.raises(RuntimeError, match='already been received'):
        second.confirm_receipt(user=manager)

    assert current_stock(chicken.pk, outlet.pk)['qty_kg'] == Decimal('30.000')
    assert StockTransfer.objects.get(pk=tid).status == TransferStatus.RECEIVED


@pytest.mark.django_db
def test_items_are_readable_on_the_transfer(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 100)
    res = client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 30), format='json')

    res = client.get(f'/api/transfers/{res.data["id"]}/')
    items = res.data['items']
    assert len(items) == 1
    # Displayed positive, stored negative.
    assert items[0]['product_name'] == 'Whole Chicken'
    assert Decimal(items[0]['qty_kg']) == Decimal('30.000')


@pytest.mark.django_db
def test_transfer_out_movement_is_recorded_as_transfer_type(client, warehouse, outlet, chicken, manager):
    stock_in(chicken, warehouse, manager, 100)
    client.post('/api/transfers/', dispatch_payload(warehouse, outlet, chicken, 30), format='json')

    m = StockMovement.objects.filter(type=MovementType.TRANSFER, location=warehouse).get()
    assert m.qty_kg == Decimal('-30.000')
    assert m.user_id == manager.pk
