"""
The audit trail must actually be written (review finding H5): /api/audit-logs/
existed but nothing ever created a row. Sensitive mutations now log who did
what — and never log secrets.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog, Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import CashierSession, Order, OrderSource, OrderStatus


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='audit_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Audit Outlet', type=LocationType.OUTLET)


def api(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def entries(model_name, action=None):
    qs = AuditLog.objects.filter(model_name=model_name)
    if action:
        qs = qs.filter(action=action)
    return list(qs)


@pytest.mark.django_db
def test_order_cancel_is_audited(manager, outlet):
    order = Order.objects.create(
        fulfilled_location=outlet, source=OrderSource.COUNTER,
        total_paisa=50000, status=OrderStatus.PENDING,
    )
    res = api(manager).post(f'/api/orders/{order.pk}/cancel/')
    assert res.status_code == 200
    (entry,) = entries('Order', 'cancel')
    assert entry.user == manager
    assert entry.object_id == order.pk
    assert entry.diff['status'] == ['pending', 'cancelled']


@pytest.mark.django_db
def test_manual_movement_is_audited(manager, outlet):
    product = Product.objects.create(name='Audit Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)
    res = api(manager).post('/api/movements/', {
        'product': product.pk, 'location': outlet.pk,
        'type': MovementType.WASTAGE, 'qty_kg': '-2.500',
    }, format='json')
    assert res.status_code == 201, res.data
    (entry,) = entries('StockMovement')
    assert entry.diff['type'] == 'wastage'
    assert entry.diff['qty_kg'] == '-2.500'


@pytest.mark.django_db
def test_price_change_is_audited(manager):
    product = Product.objects.create(name='Audit Wings', uom=UoM.KG, tax_class=TaxClass.EXEMPT)
    res = api(manager).post('/api/prices/', {
        'product': product.pk, 'tier': PriceTier.RETAIL,
        'price_paisa': 40000, 'valid_from': '2026-07-01',
    }, format='json')
    assert res.status_code == 201
    (entry,) = entries('Price')
    assert entry.diff['price_paisa'] == 40000


@pytest.mark.django_db
def test_invoice_creation_is_audited(manager):
    res = api(manager).post('/api/invoices/', {}, format='json')
    assert res.status_code == 201
    (entry,) = entries('Invoice')
    assert entry.diff['invoice_number'] == res.data['invoice_number']


@pytest.mark.django_db
def test_session_close_is_audited(manager, outlet):
    counter = Counter.objects.create(location=outlet, name='A1')
    session = CashierSession.objects.create(
        counter=counter, cashier=manager,
        opening_float_paisa=100000, opened_at=timezone.now(),
    )
    res = api(manager).post(f'/api/sessions/{session.pk}/close/',
                            {'closing_counted_paisa': 123400}, format='json')
    assert res.status_code == 200
    (entry,) = entries('CashierSession', 'close')
    assert entry.diff['closing_counted_paisa'] == 123400


@pytest.mark.django_db
def test_password_events_audited_without_secrets(manager):
    cashier = User.objects.create_user(username='audit_till', password='oldpass123', role=Role.CASHIER)
    api(manager).post(f'/api/users/{cashier.pk}/set-password/',
                      {'password': 'brand-new-99'}, format='json')
    (entry,) = entries('User', 'password_reset')
    assert entry.object_id == cashier.pk
    assert 'brand-new-99' not in str(entry.diff)


@pytest.mark.django_db
def test_user_deactivation_is_audited(manager):
    cashier = User.objects.create_user(username='audit_gone', password='x', role=Role.CASHIER)
    api(manager).delete(f'/api/users/{cashier.pk}/')
    (entry,) = entries('User', 'deactivate')
    assert entry.object_id == cashier.pk
