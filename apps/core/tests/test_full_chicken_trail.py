"""
QA scenario: the full data trail of one lot of birds, end to end — the exact
walk described in the onboarding flow doc:

    Lot arrives -> processed -> warehouse stock -> transferred to an outlet
    -> sold by a cashier -> invoiced -> partially returned -> spoilage written off.

Each stage is exercised through the real API (not model shortcuts, except where
noted) so this doubles as a role/permission smoke test. The two invariants
proven throughout:
    1. current_stock(product, location) == SUM(movements) at every stage.
    2. StockMovement.lot lets you answer "where did lot X go?" — but only as
       far as Phase 1 actually tracks it (production -> transfer). Sale/return/
       wastage movements are NOT lot-tagged; FIFO lot allocation is Phase 2.
       That boundary is asserted explicitly so nobody "fixes" it by accident.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.billing.models import CreditNote, Invoice
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.lots.models import Lot, LotStatus
from apps.partners.models import Supplier, SupplierType
from apps.processing.models import ProcessingRun
from apps.sales.models import CashierSession, Order, OrderLine, OrderSource


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='Trail WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Trail Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Trail Counter')


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(name='Trail Poultry Farm', type=SupplierType.FARM)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='trail_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def worker(db):
    return User.objects.create_user(username='trail_worker', password='x', role=Role.WAREHOUSE)


@pytest.fixture
def cashier(db, outlet):
    u = User.objects.create_user(username='trail_cashier', password='x', role=Role.CASHIER)
    u.assigned_locations.add(outlet)
    return u


@pytest.fixture
def product(db):
    return Product.objects.create(name='Trail Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL, price_paisa=75000, valid_from='2024-01-01',
    )


@pytest.mark.django_db
def test_one_lot_end_to_end_arrival_to_wastage(
    warehouse, outlet, counter, supplier, manager, worker, cashier, product, price,
):
    # ── 1. Lot arrives (worker) ────────────────────────────────────────────
    lot_resp = api(worker).post('/api/lots/', {
        'code': 'LOT-TRAIL-001', 'source_type': 'external', 'supplier': supplier.pk,
        'arrival_location': warehouse.pk, 'live_weight_kg': '100.000', 'bird_count': 80,
    }, format='json')
    assert lot_resp.status_code == 201, lot_resp.data
    lot = Lot.objects.get(pk=lot_resp.data['id'])
    assert lot.status == LotStatus.ARRIVAL

    for step in [LotStatus.GRADING, LotStatus.SLAUGHTER, LotStatus.PACKAGING]:
        t = api(worker).post(f'/api/lots/{lot.pk}/transition/', {'status': step}, format='json')
        assert t.status_code == 200, t.data

    # ── 2. Processing run (audit record of the yield) ──────────────────────
    # ProcessingRun has no per-output-product breakdown (it only records
    # input/output weight), so it does NOT itself write stock. The output
    # SKUs are posted separately as production movements, lot-tagged. This
    # is a real architectural decoupling, not an omission — proven below.
    run_resp = api(worker).post('/api/processing-runs/', {
        'lot': lot.pk, 'input_weight_kg': '100.000', 'output_weight_kg': '80.000',
    }, format='json')
    assert run_resp.status_code == 201, run_resp.data
    assert ProcessingRun.objects.filter(lot=lot).count() == 1
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('0'), (
        'creating a ProcessingRun must not, by itself, move any stock'
    )

    prod_resp = api(worker).post('/api/movements/', {
        'product': product.pk, 'location': warehouse.pk, 'lot': lot.pk,
        'type': 'production', 'qty_kg': '80.000', 'qty_pieces': 0,
    }, format='json')
    assert prod_resp.status_code == 201, prod_resp.data
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('80.000')

    # ── 3. Transfer to outlet (manager dispatches, worker receives) ───────
    transfer_resp = api(manager).post('/api/transfers/', {
        'from_location': warehouse.pk, 'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
        'lines': [{'product': product.pk, 'lot': lot.pk, 'qty_kg': '50.000'}],
    }, format='json')
    assert transfer_resp.status_code == 201, transfer_resp.data
    transfer_id = transfer_resp.data['id']

    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('30.000')
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('0'), 'still on the truck'

    recv_resp = api(worker).post(f'/api/transfers/{transfer_id}/confirm-receipt/')
    assert recv_resp.status_code == 200, recv_resp.data
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('50.000')

    # Lot traceability holds through production and transfer...
    lot_movements = StockMovement.objects.filter(lot=lot).order_by('created_at')
    assert list(lot_movements.values_list('type', 'location_id', 'qty_kg')) == [
        (MovementType.PRODUCTION, warehouse.pk, Decimal('80.000')),
        (MovementType.TRANSFER, warehouse.pk, Decimal('-50.000')),
        (MovementType.TRANSFER, outlet.pk, Decimal('50.000')),
    ]

    # ── 4. Cashier sells 2.5kg ──────────────────────────────────────────────
    session = CashierSession.objects.create(
        counter=counter, cashier=cashier, opening_float_paisa=500000, opened_at=timezone.now(),
    )
    order = Order.objects.create(
        fulfilled_location=outlet, session=session, source=OrderSource.COUNTER,
        total_paisa=187500,
    )
    OrderLine.objects.create(
        order=order, product=product, price=price,
        qty_kg=Decimal('2.500'), qty_pieces=0, line_total_paisa=187500,
    )
    order.fulfill(user=cashier)
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('47.500')

    sale_movement = StockMovement.objects.get(ref_id=order.pk, type=MovementType.SALE)
    assert sale_movement.lot is None, (
        'Phase 1 does not allocate a lot to a sale line (no FIFO yet) — '
        'the trail stops at the outlet shelf, by design'
    )

    # ── 5. Invoice + partial return (1kg) ──────────────────────────────────
    inv = Invoice.objects.create(
        order=order, invoice_number='INV-TRAIL-001', issued_at=timezone.now(), total_paisa=187500,
    )
    StockMovement.objects.create(
        product=product, location=outlet, type=MovementType.RETURN,
        qty_kg=Decimal('1.000'), ref_id=order.pk, user=manager,
    )
    cn_resp = api(manager).post('/api/credit-notes/', {
        'invoice': inv.pk, 'reason': 'Customer returned 1kg', 'amount_paisa': 75000,
        'issued_at': timezone.now().isoformat(), 'issued_by': manager.pk,
    }, format='json')
    assert cn_resp.status_code == 201, cn_resp.data
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('48.500')

    # ── 6. Spoilage: 0.5kg wastage ──────────────────────────────────────────
    waste_resp = api(manager).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk,
        'type': 'wastage', 'qty_kg': '-0.500', 'qty_pieces': 0,
    }, format='json')
    assert waste_resp.status_code == 201, waste_resp.data

    # ── Final reconciliation: current_stock == SUM(all movements) ──────────
    final_stock = current_stock(product.pk, outlet.pk)['qty_kg']
    assert final_stock == Decimal('48.000')

    ledger_sum = StockMovement.objects.filter(
        product=product, location=outlet,
    ).aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('qty_kg'))['total']
    assert ledger_sum == final_stock

    # And the warehouse side of the ledger independently reconciles too.
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('30.000')

    # Every movement this lot ever touched is still queryable by lot_id —
    # "where did lot X go?" — even though the trail necessarily stops at the
    # point of sale.
    assert StockMovement.objects.filter(lot=lot).count() == 3
    assert CreditNote.objects.filter(invoice=inv).count() == 1


@pytest.mark.django_db
def test_processing_run_alone_does_not_change_stock_and_is_warehouse_only(
    warehouse, worker, manager,
):
    """
    Guards against a future change silently making ProcessingRun creation
    write stock on its own (it structurally can't right now — no per-output
    breakdown on the model — but this pins the behavior so a refactor that
    adds one doesn't skip the movement-writing step).
    """
    lot = Lot.objects.create(
        code='LOT-TRAIL-002', source_type='own',
        arrival_location=warehouse, live_weight_kg='40.000', bird_count=30,
    )
    resp = api(worker).post('/api/processing-runs/', {
        'lot': lot.pk, 'input_weight_kg': '40.000', 'output_weight_kg': '32.000',
    }, format='json')
    assert resp.status_code == 201
    assert StockMovement.objects.filter(lot=lot).count() == 0

    cashier = User.objects.create_user(username='trail_cashier2', password='x', role=Role.CASHIER)
    denied = api(cashier).post('/api/processing-runs/', {
        'lot': lot.pk, 'input_weight_kg': '1.000', 'output_weight_kg': '1.000',
    }, format='json')
    assert denied.status_code == 403
