"""
Core invariant: current_stock(product, location) == SUM of all StockMovement.qty_*
for that (product, location) pair. These tests prove it holds across every movement type.
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog.models import Product, UoM
from apps.inventory.models import MovementType, StockMovement, StockTransfer, TransferStatus
from apps.inventory.queries import current_stock
from apps.locations.models import Location, LocationType


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='Central Warehouse', type=LocationType.WAREHOUSE)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Outlet 1', type=LocationType.OUTLET)


@pytest.fixture
def product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG)


@pytest.fixture
def user(db):
    from apps.accounts.models import User
    return User.objects.create_user(username='stock_tester', password='x')


def make_movement(product, location, type_, user, qty_kg=Decimal('0'), qty_pieces=0, ref_id=None, lot=None):
    return StockMovement.objects.create(
        product=product, location=location, lot=lot,
        type=type_, qty_kg=qty_kg, qty_pieces=qty_pieces,
        ref_id=ref_id, user=user,
    )


# ── Zero-movement baseline ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_no_movements_returns_zero(product, warehouse):
    stock = current_stock(product.pk, warehouse.pk)
    assert stock['qty_kg'] == Decimal('0')
    assert stock['qty_pieces'] == 0


# ── Single movement types ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_production_adds_stock(product, warehouse, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('20.000'))
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('20.000')


@pytest.mark.django_db
def test_sale_reduces_stock(product, warehouse, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('10.000'))
    make_movement(product, warehouse, MovementType.SALE,       user, qty_kg=Decimal('-3.500'))
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('6.500')


@pytest.mark.django_db
def test_return_restores_stock(product, warehouse, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('10.000'))
    make_movement(product, warehouse, MovementType.SALE,       user, qty_kg=Decimal('-10.000'))
    make_movement(product, warehouse, MovementType.RETURN,     user, qty_kg=Decimal('2.000'))
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('2.000')


@pytest.mark.django_db
def test_wastage_reduces_stock(product, warehouse, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('10.000'))
    make_movement(product, warehouse, MovementType.WASTAGE,    user, qty_kg=Decimal('-1.250'))
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('8.750')


@pytest.mark.django_db
def test_adjustment_can_go_either_way(product, warehouse, user):
    make_movement(product, warehouse, MovementType.PRODUCTION,  user, qty_kg=Decimal('10.000'))
    make_movement(product, warehouse, MovementType.ADJUSTMENT,  user, qty_kg=Decimal('-0.500'))  # write-down
    make_movement(product, warehouse, MovementType.ADJUSTMENT,  user, qty_kg=Decimal('0.200'))   # write-up
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('9.700')


# ── The core invariant: stock = sum of all movements ─────────────────────────

@pytest.mark.django_db
def test_stock_equals_sum_of_movements(product, warehouse, user):
    """Explicit sum-of-movements proof across all six movement types."""
    entries = [
        (MovementType.PRODUCTION,  Decimal('50.000')),
        (MovementType.TRANSFER,    Decimal('-10.000')),
        (MovementType.SALE,        Decimal('-8.500')),
        (MovementType.RETURN,      Decimal('1.000')),
        (MovementType.WASTAGE,     Decimal('-0.750')),
        (MovementType.ADJUSTMENT,  Decimal('0.250')),
    ]
    for type_, qty in entries:
        make_movement(product, warehouse, type_, user, qty_kg=qty)

    expected = sum(qty for _, qty in entries)
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == expected


@pytest.mark.django_db
def test_piece_stock_is_independent_of_kg(product, warehouse, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('5.000'), qty_pieces=10)
    make_movement(product, warehouse, MovementType.SALE,       user, qty_kg=Decimal('0'),    qty_pieces=-3)
    stock = current_stock(product.pk, warehouse.pk)
    assert stock['qty_kg'] == Decimal('5.000')
    assert stock['qty_pieces'] == 7


@pytest.mark.django_db
def test_both_qty_fields_can_be_nonzero_on_same_movement(product, warehouse, user):
    """Spec allows both qty_kg and qty_pieces on the same row."""
    make_movement(product, warehouse, MovementType.PRODUCTION, user,
                  qty_kg=Decimal('3.500'), qty_pieces=5)
    stock = current_stock(product.pk, warehouse.pk)
    assert stock['qty_kg'] == Decimal('3.500')
    assert stock['qty_pieces'] == 5


# ── Location isolation ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_stock_is_scoped_to_location(product, warehouse, outlet, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('10.000'))
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('0')


@pytest.mark.django_db
def test_different_locations_do_not_bleed(product, warehouse, outlet, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('10.000'))
    make_movement(product, outlet,    MovementType.PRODUCTION, user, qty_kg=Decimal('5.000'))
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('10.000')
    assert current_stock(product.pk, outlet.pk)['qty_kg']    == Decimal('5.000')


# ── Transfer two-phase ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_dispatch_reduces_source_immediately(product, warehouse, outlet, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('10.000'))
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    make_movement(product, warehouse, MovementType.TRANSFER, user,
                  qty_kg=Decimal('-8.000'), ref_id=transfer.pk)

    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('2.000')
    assert current_stock(product.pk, outlet.pk)['qty_kg']    == Decimal('0')


@pytest.mark.django_db
def test_confirm_receipt_adds_stock_at_destination(product, warehouse, outlet, user):
    make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('10.000'))
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    make_movement(product, warehouse, MovementType.TRANSFER, user,
                  qty_kg=Decimal('-8.000'), ref_id=transfer.pk)

    transfer.confirm_receipt(user)

    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('2.000')
    assert current_stock(product.pk, outlet.pk)['qty_kg']    == Decimal('8.000')


@pytest.mark.django_db
def test_confirm_receipt_sets_status_and_received_by(product, warehouse, outlet, user):
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    make_movement(product, warehouse, MovementType.TRANSFER, user,
                  qty_kg=Decimal('-5.000'), ref_id=transfer.pk)
    transfer.confirm_receipt(user)

    transfer.refresh_from_db()
    assert transfer.status      == TransferStatus.RECEIVED
    assert transfer.received_by == user
    assert transfer.received_at is not None


@pytest.mark.django_db
def test_confirm_receipt_twice_raises(product, warehouse, outlet, user):
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    make_movement(product, warehouse, MovementType.TRANSFER, user,
                  qty_kg=Decimal('-5.000'), ref_id=transfer.pk)
    transfer.confirm_receipt(user)
    with pytest.raises(RuntimeError, match='already been received'):
        transfer.confirm_receipt(user)


@pytest.mark.django_db
def test_multi_product_transfer(warehouse, outlet, user):
    """confirm_receipt mirrors all dispatch movements, not just one product."""
    product_a = Product.objects.create(name='Breast', uom=UoM.KG)
    product_b = Product.objects.create(name='Wing',   uom=UoM.KG)

    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    make_movement(product_a, warehouse, MovementType.TRANSFER, user, qty_kg=Decimal('-5.000'), ref_id=transfer.pk)
    make_movement(product_b, warehouse, MovementType.TRANSFER, user, qty_kg=Decimal('-3.000'), ref_id=transfer.pk)

    transfer.confirm_receipt(user)

    assert current_stock(product_a.pk, outlet.pk)['qty_kg'] == Decimal('5.000')
    assert current_stock(product_b.pk, outlet.pk)['qty_kg'] == Decimal('3.000')


# ── Append-only enforcement ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_movement_update_raises(product, warehouse, user):
    m = make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('5.000'))
    m.qty_kg = Decimal('99.000')
    with pytest.raises(RuntimeError, match='append-only'):
        m.save()


@pytest.mark.django_db
def test_movement_delete_raises(product, warehouse, user):
    m = make_movement(product, warehouse, MovementType.PRODUCTION, user, qty_kg=Decimal('5.000'))
    with pytest.raises(RuntimeError, match='never be deleted'):
        m.delete()
