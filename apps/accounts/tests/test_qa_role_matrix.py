"""
QA — Angle 3: Role boundary matrix.
For each role, hit key endpoints and assert expected HTTP status.
Any 200 from cashier or worker on a money/billing endpoint is a bug.
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.billing.models import Invoice
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import (
    CashierSession, Order, OrderLine, OrderSource, OrderStatus, Payment, PaymentMethod,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Matrix Outlet', type=LocationType.OUTLET)


@pytest.fixture
def outlet2(db):
    return Location.objects.create(name='Other Outlet', type=LocationType.OUTLET)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Matrix Counter')


@pytest.fixture
def superuser(db):
    return User.objects.create_user(username='rm_admin', password='x', role=Role.SUPERUSER)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='rm_manager', password='x', role=Role.MANAGER)


@pytest.fixture
def outlet_mgr(db, outlet):
    u = User.objects.create_user(username='rm_omgr', password='x', role=Role.OUTLET_MANAGER)
    u.assigned_locations.add(outlet)
    return u


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='rm_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def worker(db):
    return User.objects.create_user(username='rm_worker', password='x', role=Role.WAREHOUSE)


@pytest.fixture
def product(db):
    return Product.objects.create(name='Matrix Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )


@pytest.fixture
def sample_order(db, outlet, counter, cashier):
    sess = CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )
    return Order.objects.create(
        fulfilled_location=outlet, session=sess,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=75000,
    )


@pytest.fixture
def sample_invoice(db, sample_order, manager):
    return Invoice.objects.create(
        order=sample_order, invoice_number='RM-INV-001',
        issued_at=timezone.now(), total_paisa=75000,
    )


@pytest.fixture
def sample_movement(db, outlet, manager, product):
    return StockMovement.objects.create(
        product=product, location=outlet,
        type=MovementType.PRODUCTION, qty_kg=10, user=manager,
    )


def get(user, url):
    c = APIClient()
    c.force_authenticate(user=user)
    return c.get(url).status_code


def post(user, url, data=None):
    c = APIClient()
    c.force_authenticate(user=user)
    return c.post(url, data or {}, format='json').status_code


# ═══════════════════════════════════════════════════════════════════════════════
# CASHIER — must be BLOCKED from billing (Rule 7: cashier has NO billing access)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_cashier_blocked_from_invoices(cashier, sample_invoice):
    assert get(cashier, '/api/invoices/') == 403, 'BUG: cashier can list invoices'


@pytest.mark.django_db
def test_cashier_blocked_from_credit_notes(cashier, sample_invoice):
    assert get(cashier, '/api/credit-notes/') == 403, 'BUG: cashier can list credit notes'


@pytest.mark.django_db
def test_cashier_blocked_from_movements(cashier, sample_movement):
    assert get(cashier, '/api/movements/') == 403, 'BUG: cashier can list stock movements'


@pytest.mark.django_db
def test_cashier_blocked_from_transfers(cashier):
    assert get(cashier, '/api/transfers/') == 403, 'BUG: cashier can list transfers'


@pytest.mark.django_db
def test_cashier_can_list_orders(cashier, sample_order):
    assert get(cashier, '/api/orders/') == 200


@pytest.mark.django_db
def test_cashier_can_list_sessions(cashier, sample_order):
    assert get(cashier, '/api/sessions/') == 200


# ═══════════════════════════════════════════════════════════════════════════════
# WORKER (warehouse) — must be BLOCKED from all money/sales endpoints (Rule 7)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_worker_blocked_from_orders(worker, sample_order):
    assert get(worker, '/api/orders/') == 403, 'BUG: worker can list orders'


@pytest.mark.django_db
def test_worker_blocked_from_invoices(worker, sample_invoice):
    assert get(worker, '/api/invoices/') == 403, 'BUG: worker can list invoices'


@pytest.mark.django_db
def test_worker_blocked_from_payments(worker, sample_order):
    assert get(worker, '/api/payments/') == 403, 'BUG: worker can list payments'


@pytest.mark.django_db
def test_worker_blocked_from_sessions(worker, sample_order):
    assert get(worker, '/api/sessions/') == 403, 'BUG: worker can list cashier sessions'


@pytest.mark.django_db
def test_worker_can_list_movements(worker, sample_movement):
    assert get(worker, '/api/movements/') == 200


@pytest.mark.django_db
def test_worker_can_list_transfers(worker):
    assert get(worker, '/api/transfers/') == 200


# ═══════════════════════════════════════════════════════════════════════════════
# OUTLET MANAGER — read-only on their outlet, blocked from writes
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_outlet_manager_can_read_invoices(outlet_mgr, sample_invoice):
    assert get(outlet_mgr, '/api/invoices/') == 200


@pytest.mark.django_db
def test_outlet_manager_blocked_from_creating_order(outlet_mgr, outlet, counter, cashier):
    sess = CashierSession.objects.create(
        counter=counter, cashier=cashier,
        opening_float_paisa=0, opened_at=timezone.now(),
    )
    code = post(outlet_mgr, '/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': sess.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 0,
    })
    assert code == 403, 'BUG: outlet_manager should not be able to create orders'


@pytest.mark.django_db
def test_outlet_manager_sees_only_their_outlet_invoices(outlet_mgr, sample_invoice, outlet2, manager):
    # Create invoice for outlet2 (not assigned to outlet_mgr)
    counter2 = Counter.objects.create(location=outlet2, name='C2')
    cashier2 = User.objects.create_user(username='c2', password='x', role=Role.CASHIER)
    sess2 = CashierSession.objects.create(
        counter=counter2, cashier=cashier2,
        opening_float_paisa=0, opened_at=timezone.now(),
    )
    order2 = Order.objects.create(
        fulfilled_location=outlet2, session=sess2,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=0,
    )
    inv2 = Invoice.objects.create(
        order=order2, invoice_number='RM-INV-OTHER',
        issued_at=timezone.now(), total_paisa=0,
    )

    c = APIClient()
    c.force_authenticate(user=outlet_mgr)
    resp = c.get('/api/invoices/')
    ids = [row['id'] for row in resp.data['results']]
    assert sample_invoice.pk in ids
    assert inv2.pk not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# MANAGER — full read/write access to everything
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_manager_can_read_invoices(manager, sample_invoice):
    assert get(manager, '/api/invoices/') == 200


@pytest.mark.django_db
def test_manager_can_read_movements(manager, sample_movement):
    assert get(manager, '/api/movements/') == 200


@pytest.mark.django_db
def test_manager_can_read_orders(manager, sample_order):
    assert get(manager, '/api/orders/') == 200
