"""
Production-readiness simulation: every role working at the same time, on the same stock.

These are the only tests in the suite that run with real threads on real database
connections (django_db(transaction=True)), so they are the only ones that actually
exercise the select_for_update() row locks the ledger's integrity depends on. A
single-threaded test can never prove an oversell guard works.

The invariant under test everywhere below: stock derived from the ledger must never
go negative, and a transfer must never create or destroy stock.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connection, connections
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement, StockTransfer
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import CashierSession, OrderSource, OrderStatus


# ── Scenario setup ────────────────────────────────────────────────────────────

def build_world():
    """A warehouse, an outlet, two tills, and one product priced for sale."""
    warehouse = Location.objects.create(name='Central WH', type=LocationType.WAREHOUSE)
    outlet = Location.objects.create(name='Outlet 1', type=LocationType.OUTLET)

    manager = User.objects.create_user(username='c_manager', password='x', role=Role.MANAGER)
    worker = User.objects.create_user(username='c_worker', password='x', role=Role.WAREHOUSE)
    cashier_a = User.objects.create_user(username='c_cashier_a', password='x', role=Role.CASHIER)
    cashier_b = User.objects.create_user(username='c_cashier_b', password='x', role=Role.CASHIER)

    counter_a = Counter.objects.create(location=outlet, name='Till A')
    counter_b = Counter.objects.create(location=outlet, name='Till B')
    session_a = CashierSession.objects.create(
        counter=counter_a, cashier=cashier_a, opening_float_paisa=0, opened_at=timezone.now(),
    )
    session_b = CashierSession.objects.create(
        counter=counter_b, cashier=cashier_b, opening_float_paisa=0, opened_at=timezone.now(),
    )

    product = Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)
    price = Price.objects.create(
        product=product, tier=PriceTier.RETAIL, price_paisa=50000, valid_from='2024-01-01',
    )
    return locals()


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def stock_in(product, location, user, qty_kg):
    StockMovement.objects.create(
        product=product, location=location, type=MovementType.PRODUCTION,
        qty_kg=Decimal(str(qty_kg)), user=user,
    )


def sell(cashier, session, outlet, product, price, qty_kg):
    """One POS checkout. Closes the thread's DB connection so it isn't leaked."""
    try:
        paisa = int(Decimal(str(qty_kg)) * price.price_paisa)
        return api(cashier).post('/api/orders/', {
            'fulfilled_location': outlet.pk,
            'session': session.pk,
            'source': OrderSource.COUNTER,
            'total_paisa': paisa,
            'lines': [{
                'product': product.pk, 'price': price.pk,
                'qty_kg': str(qty_kg), 'qty_pieces': 0, 'line_total_paisa': paisa,
            }],
            'payments': [{'method': 'cash', 'amount_paisa': paisa, 'ref': None}],
        }, format='json')
    finally:
        connections.close_all()


def dispatch(user, warehouse, outlet, product, qty_kg):
    try:
        return api(user).post('/api/transfers/', {
            'from_location': warehouse.pk,
            'to_location': outlet.pk,
            'dispatched_at': timezone.now().isoformat(),
            'lines': [{'product': product.pk, 'qty_kg': str(qty_kg)}],
        }, format='json')
    finally:
        connections.close_all()


def run_parallel(fns):
    with ThreadPoolExecutor(max_workers=len(fns)) as pool:
        return [f.result() for f in [pool.submit(fn) for fn in fns]]


# ── Two cashiers, one till-load of stock ──────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_two_cashiers_cannot_oversell_the_same_stock():
    """
    10 kg at the outlet. Both tills ring up 6 kg at the same instant.
    Exactly one sale may succeed — the ledger must not go to -2 kg.
    """
    w = build_world()
    stock_in(w['product'], w['outlet'], w['manager'], 10)

    results = run_parallel([
        lambda: sell(w['cashier_a'], w['session_a'], w['outlet'], w['product'], w['price'], 6),
        lambda: sell(w['cashier_b'], w['session_b'], w['outlet'], w['product'], w['price'], 6),
    ])
    codes = sorted(r.status_code for r in results)

    assert codes == [201, 400], f'expected one sale to be rejected, got {codes}'
    assert current_stock(w['product'].pk, w['outlet'].pk)['qty_kg'] == Decimal('4.000')


@pytest.mark.django_db(transaction=True)
def test_parallel_sales_within_stock_all_succeed_and_nothing_is_lost():
    """
    Six concurrent 1 kg sales against 10 kg. All must succeed, and the ledger must
    show exactly 4 kg left — a lost update would leave more.
    """
    w = build_world()
    stock_in(w['product'], w['outlet'], w['manager'], 10)

    cashiers = [(w['cashier_a'], w['session_a']), (w['cashier_b'], w['session_b'])]
    results = run_parallel([
        (lambda i=i: sell(*cashiers[i % 2], w['outlet'], w['product'], w['price'], 1))
        for i in range(6)
    ])

    assert all(r.status_code == 201 for r in results), [r.status_code for r in results]
    assert current_stock(w['product'].pk, w['outlet'].pk)['qty_kg'] == Decimal('4.000')


# ── Manager transferring while a cashier is selling ───────────────────────────

@pytest.mark.django_db(transaction=True)
def test_transfer_out_and_sale_cannot_both_claim_the_same_stock():
    """
    The warehouse has 10 kg. The manager dispatches 8 kg to an outlet while a
    cashier at the warehouse counter sells 8 kg. Only one can win.
    """
    w = build_world()
    stock_in(w['product'], w['warehouse'], w['manager'], 10)

    # A till at the warehouse itself, so both operations contend for the same location.
    wh_counter = Counter.objects.create(location=w['warehouse'], name='WH Till')
    wh_session = CashierSession.objects.create(
        counter=wh_counter, cashier=w['cashier_a'], opening_float_paisa=0, opened_at=timezone.now(),
    )

    results = run_parallel([
        lambda: dispatch(w['manager'], w['warehouse'], w['outlet'], w['product'], 8),
        lambda: sell(w['cashier_a'], wh_session, w['warehouse'], w['product'], w['price'], 8),
    ])
    codes = sorted(r.status_code for r in results)

    assert codes == [201, 400], f'both operations claimed the same stock: {codes}'
    assert current_stock(w['product'].pk, w['warehouse'].pk)['qty_kg'] == Decimal('2.000')


@pytest.mark.django_db(transaction=True)
def test_concurrent_dispatches_cannot_oversell_the_warehouse():
    w = build_world()
    stock_in(w['product'], w['warehouse'], w['manager'], 10)
    outlet2 = Location.objects.create(name='Outlet 2', type=LocationType.OUTLET)

    results = run_parallel([
        lambda: dispatch(w['manager'], w['warehouse'], w['outlet'], w['product'], 7),
        lambda: dispatch(w['worker'], w['warehouse'], outlet2, w['product'], 7),
    ])
    codes = sorted(r.status_code for r in results)

    assert codes == [201, 400], f'warehouse oversold: {codes}'
    assert current_stock(w['product'].pk, w['warehouse'].pk)['qty_kg'] == Decimal('3.000')


# ── Two people confirming the same delivery ───────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_concurrent_receipt_confirmations_land_the_stock_once():
    """
    The manager and the warehouse worker both hit "Mark Received" on the same
    van. The goods must arrive once. Double-landing would be unfixable: the
    ledger is append-only, so the phantom rows could only ever be reversed.
    """
    w = build_world()
    stock_in(w['product'], w['warehouse'], w['manager'], 50)

    res = dispatch(w['manager'], w['warehouse'], w['outlet'], w['product'], 30)
    assert res.status_code == 201
    tid = res.data['id']

    def confirm(user):
        try:
            return api(user).post(f'/api/transfers/{tid}/confirm-receipt/')
        finally:
            connections.close_all()

    results = run_parallel([lambda: confirm(w['manager']), lambda: confirm(w['worker'])])
    codes = sorted(r.status_code for r in results)

    assert codes == [200, 400], f'receipt confirmed twice: {codes}'
    assert current_stock(w['product'].pk, w['outlet'].pk)['qty_kg'] == Decimal('30.000')
    # Conservation: nothing created, nothing destroyed.
    total = (current_stock(w['product'].pk, w['warehouse'].pk)['qty_kg']
             + current_stock(w['product'].pk, w['outlet'].pk)['qty_kg'])
    assert total == Decimal('50.000')


# ── The whole business running at once ────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_full_day_all_roles_working_in_parallel():
    """
    Everyone works at the same time on the same product:
      - two cashiers selling at the outlet
      - the manager dispatching warehouse stock to the outlet
      - the warehouse worker booking in production and recording wastage
      - the outlet manager reading reports throughout

    No operation may drive stock negative, and the reader must never 500.
    """
    w = build_world()
    stock_in(w['product'], w['warehouse'], w['manager'], 100)
    stock_in(w['product'], w['outlet'], w['manager'], 20)

    outlet_mgr = User.objects.create_user(
        username='c_outlet_mgr', password='x', role=Role.OUTLET_MANAGER,
    )
    outlet_mgr.assigned_locations.add(w['outlet'])

    def produce():
        try:
            return api(w['worker']).post('/api/movements/', {
                'product': w['product'].pk, 'location': w['warehouse'].pk,
                'type': MovementType.PRODUCTION, 'qty_kg': '10.000', 'qty_pieces': 0,
            }, format='json')
        finally:
            connections.close_all()

    def waste():
        # Warehouse (the batch recorder) may write off spoilage as wastage.
        try:
            return api(w['worker']).post('/api/movements/', {
                'product': w['product'].pk, 'location': w['warehouse'].pk,
                'type': MovementType.WASTAGE, 'qty_kg': '-2.000', 'qty_pieces': 0,
            }, format='json')
        finally:
            connections.close_all()

    def read_reports():
        try:
            c = api(outlet_mgr)
            return [
                c.get('/api/stock/summary/').status_code,
                c.get('/api/orders/summary/').status_code,
                c.get('/api/movements/').status_code,
            ]
        finally:
            connections.close_all()

    results = run_parallel([
        lambda: sell(w['cashier_a'], w['session_a'], w['outlet'], w['product'], w['price'], 5),
        lambda: sell(w['cashier_b'], w['session_b'], w['outlet'], w['product'], w['price'], 5),
        lambda: sell(w['cashier_a'], w['session_a'], w['outlet'], w['product'], w['price'], 3),
        lambda: dispatch(w['manager'], w['warehouse'], w['outlet'], w['product'], 40),
        produce,
        waste,
        read_reports,
    ])

    sales = results[0:3]
    transfer, production, wastage, reads = results[3], results[4], results[5], results[6]

    assert all(r.status_code == 201 for r in sales), [r.status_code for r in sales]
    assert transfer.status_code == 201
    assert production.status_code == 201
    assert wastage.status_code == 201
    assert reads == [200, 200, 200], f'a reader errored during concurrent writes: {reads}'

    # Outlet: 20 opening − 13 sold = 7 (the transfer has not been received yet).
    assert current_stock(w['product'].pk, w['outlet'].pk)['qty_kg'] == Decimal('7.000')
    # Warehouse: 100 + 10 produced − 2 wasted − 40 dispatched = 68.
    assert current_stock(w['product'].pk, w['warehouse'].pk)['qty_kg'] == Decimal('68.000')

    # Nothing anywhere may be negative.
    for row in StockMovement.objects.values('product_id', 'location_id').distinct():
        stock = current_stock(row['product_id'], row['location_id'])
        assert stock['qty_kg'] >= 0, f'negative stock at {row}'
