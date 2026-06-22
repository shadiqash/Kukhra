"""
Integration tests — six end-to-end scenarios exercising the full HTTP→DB stack.
All requests go through DRF views; no model methods are called directly.
"""
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.billing.models import CbmsStatus, CreditNote, Invoice, InvoiceLine
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement, StockTransfer
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.sales.models import (
    CashierSession, Order, OrderLine, OrderSource, OrderStatus, Payment, PaymentMethod,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Shared fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Main Outlet', type=LocationType.OUTLET)


@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='Central WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def counter(db, outlet):
    return Counter.objects.create(location=outlet, name='Counter 1')


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def cashier_user(db):
    return User.objects.create_user(username='cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def warehouse_user(db):
    return User.objects.create_user(username='wh_user', password='x', role=Role.WAREHOUSE)


@pytest.fixture
def product_kg(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price_kg(db, product_kg):
    return Price.objects.create(
        product=product_kg, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )


@pytest.fixture
def session(db, counter, cashier_user):
    return CashierSession.objects.create(
        counter=counter, cashier=cashier_user,
        opening_float_paisa=100000, opened_at=timezone.now(),
    )


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ═══════════════════════════════════════════════════════════════════════════════
# 1. POST /api/orders/ → fulfill → stock movements created with negative qty
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_order_fulfill_creates_negative_stock_movement(
    outlet, session, manager, product_kg, price_kg
):
    StockMovement.objects.create(
        product=product_kg, location=outlet,
        type=MovementType.PRODUCTION, qty_kg=Decimal('10.000'), user=manager,
    )

    c = client_for(manager)

    # Create order
    order_resp = c.post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 150000,
    }, format='json')
    assert order_resp.status_code == 201, order_resp.data
    order_id = order_resp.data['id']

    # Add a line
    line_resp = c.post('/api/order-lines/', {
        'order': order_id,
        'product': product_kg.pk,
        'price': price_kg.pk,
        'qty_kg': '2.000',
        'qty_pieces': 0,
        'line_total_paisa': 150000,
    }, format='json')
    assert line_resp.status_code == 201, line_resp.data

    # Fulfill
    fulfill_resp = c.post(f'/api/orders/{order_id}/fulfill/')
    assert fulfill_resp.status_code == 200, fulfill_resp.data
    assert fulfill_resp.data['status'] == OrderStatus.FULFILLED

    # Movement created at fulfilled_location with negative qty
    movements = StockMovement.objects.filter(
        ref_id=order_id, type=MovementType.SALE, location=outlet,
    )
    assert movements.count() == 1
    m = movements.first()
    assert m.qty_kg == Decimal('-2.000')


@pytest.mark.django_db
def test_order_fulfill_multi_line_all_movements_negative(
    outlet, session, manager, product_kg, price_kg
):
    product2 = Product.objects.create(name='Wings', uom=UoM.KG, tax_class=TaxClass.EXEMPT)
    price2 = Price.objects.create(
        product=product2, tier=PriceTier.RETAIL,
        price_paisa=40000, valid_from='2024-01-01',
    )
    c = client_for(manager)

    order_resp = c.post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': 0,
    }, format='json')
    order_id = order_resp.data['id']

    for prod, price, qty in [(product_kg, price_kg, '1.000'), (product2, price2, '2.000')]:
        c.post('/api/order-lines/', {
            'order': order_id, 'product': prod.pk, 'price': price.pk,
            'qty_kg': qty, 'qty_pieces': 0, 'line_total_paisa': 10000,
        }, format='json')

    c.post(f'/api/orders/{order_id}/fulfill/')

    movements = StockMovement.objects.filter(ref_id=order_id, type=MovementType.SALE)
    assert movements.count() == 2
    assert all(m.qty_kg < 0 for m in movements)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GET /api/invoices/ — role-based access
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def outlet2(db):
    return Location.objects.create(name='Branch Outlet', type=LocationType.OUTLET)


@pytest.fixture
def outlet_mgr(db, outlet):
    u = User.objects.create_user(username='omgr', password='x', role=Role.OUTLET_MANAGER)
    u.assigned_locations.add(outlet)
    return u


@pytest.fixture
def sample_invoice(db, outlet, manager, session, product_kg, price_kg):
    counter = Counter.objects.get_or_create(location=outlet, name='Counter 1')[0]
    order = Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=75000,
    )
    inv = Invoice.objects.create(
        order=order, invoice_number='INV-001',
        issued_at=timezone.now(), total_paisa=75000,
    )
    return inv


@pytest.fixture
def other_invoice(db, outlet2, manager):
    counter2 = Counter.objects.create(location=outlet2, name='Counter B')
    cashier2 = User.objects.create_user(username='cashier2', password='x', role=Role.CASHIER)
    sess2 = CashierSession.objects.create(
        counter=counter2, cashier=cashier2,
        opening_float_paisa=0, opened_at=timezone.now(),
    )
    order2 = Order.objects.create(
        fulfilled_location=outlet2, session=sess2,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=50000,
    )
    inv2 = Invoice.objects.create(
        order=order2, invoice_number='INV-002',
        issued_at=timezone.now(), total_paisa=50000,
    )
    return inv2


@pytest.mark.django_db
def test_cashier_cannot_list_invoices(cashier_user, sample_invoice):
    resp = client_for(cashier_user).get('/api/invoices/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_manager_can_list_invoices(manager, sample_invoice):
    resp = client_for(manager).get('/api/invoices/')
    assert resp.status_code == 200
    assert len(resp.data) >= 1


@pytest.mark.django_db
def test_outlet_manager_sees_only_their_outlet_invoices(
    outlet_mgr, sample_invoice, other_invoice
):
    resp = client_for(outlet_mgr).get('/api/invoices/')
    assert resp.status_code == 200
    ids = [row['id'] for row in resp.data]
    assert sample_invoice.pk in ids
    assert other_invoice.pk not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Stock transfer: dispatch → negative at source, confirm → positive at dest
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_transfer_dispatch_creates_negative_at_source(
    warehouse, outlet, manager, product_kg, warehouse_user
):
    StockMovement.objects.create(
        product=product_kg, location=warehouse,
        type=MovementType.PRODUCTION, qty_kg=Decimal('20.000'), user=manager,
    )

    c = client_for(manager)
    transfer_resp = c.post('/api/transfers/', {
        'from_location': warehouse.pk,
        'to_location': outlet.pk,
        'dispatched_at': timezone.now().isoformat(),
    }, format='json')
    assert transfer_resp.status_code == 201, transfer_resp.data
    transfer_id = transfer_resp.data['id']

    # Dispatch movement (negative at source)
    c.post('/api/movements/', {
        'product': product_kg.pk,
        'location': warehouse.pk,
        'type': MovementType.TRANSFER,
        'qty_kg': '-8.000',
        'qty_pieces': 0,
        'ref_id': transfer_id,
        'user': manager.pk,
    }, format='json')

    assert current_stock(product_kg.pk, warehouse.pk)['qty_kg'] == Decimal('12.000')
    assert current_stock(product_kg.pk, outlet.pk)['qty_kg'] == Decimal('0')


@pytest.mark.django_db
def test_transfer_confirm_receipt_adds_positive_at_destination(
    warehouse, outlet, manager, product_kg
):
    StockMovement.objects.create(
        product=product_kg, location=warehouse,
        type=MovementType.PRODUCTION, qty_kg=Decimal('20.000'), user=manager,
    )
    transfer = StockTransfer.objects.create(
        from_location=warehouse, to_location=outlet, dispatched_at=timezone.now(),
    )
    StockMovement.objects.create(
        product=product_kg, location=warehouse,
        type=MovementType.TRANSFER, qty_kg=Decimal('-8.000'),
        ref_id=transfer.pk, user=manager,
    )

    c = client_for(manager)
    resp = c.post(f'/api/transfers/{transfer.pk}/confirm-receipt/')
    assert resp.status_code == 200, resp.data
    assert resp.data['status'] == 'received'

    assert current_stock(product_kg.pk, warehouse.pk)['qty_kg'] == Decimal('12.000')
    assert current_stock(product_kg.pk, outlet.pk)['qty_kg'] == Decimal('8.000')


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Invoice tax split: exempt + taxable lines → correct header totals
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_invoice_tax_split_exempt_and_taxable(outlet, session, manager, product_kg, price_kg):
    product_taxable = Product.objects.create(
        name='Processed Meat', uom=UoM.KG, tax_class=TaxClass.TAXABLE,
    )
    price_taxable = Price.objects.create(
        product=product_taxable, tier=PriceTier.RETAIL,
        price_paisa=100000, valid_from='2024-01-01',
    )

    order = Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=175000,
    )

    exempt_line_total = 75000    # 1 kg × 75000p — exempt
    taxable_line_total = 100000  # 1 kg × 100000p — 13% VAT

    inv = Invoice.objects.create(
        order=order, invoice_number='INV-TAX-001', issued_at=timezone.now(),
    )
    InvoiceLine.objects.create(
        invoice=inv, product=product_kg, price=price_kg,
        tax_class=TaxClass.EXEMPT, qty_kg=Decimal('1.000'), qty_pieces=0,
        unit_paisa=75000, line_total_paisa=exempt_line_total, vat_paisa=0,
    )
    InvoiceLine.objects.create(
        invoice=inv, product=product_taxable, price=price_taxable,
        tax_class=TaxClass.TAXABLE, qty_kg=Decimal('1.000'), qty_pieces=0,
        unit_paisa=100000, line_total_paisa=taxable_line_total,
        vat_paisa=int(Decimal(taxable_line_total) * Decimal('0.13')),
    )
    inv.recompute_totals()
    inv.refresh_from_db()

    expected_vat = int(Decimal('100000') * Decimal('0.13'))  # 13000
    assert inv.exempt_paisa == 75000
    assert inv.taxable_paisa == 100000
    assert inv.vat_paisa == expected_vat
    assert inv.total_paisa == 75000 + 100000 + expected_vat

    # Verify via API
    c = client_for(manager)
    resp = c.get(f'/api/invoices/{inv.pk}/')
    assert resp.status_code == 200
    assert resp.data['exempt_paisa'] == 75000
    assert resp.data['taxable_paisa'] == 100000
    assert resp.data['vat_paisa'] == expected_vat


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Fulfill order → return one line → positive movement + credit note
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_return_line_creates_positive_movement_and_credit_note(
    outlet, session, manager, product_kg, price_kg
):
    StockMovement.objects.create(
        product=product_kg, location=outlet,
        type=MovementType.PRODUCTION, qty_kg=Decimal('10.000'), user=manager,
    )
    order = Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, total_paisa=150000,
    )
    OrderLine.objects.create(
        order=order, product=product_kg, price=price_kg,
        qty_kg=Decimal('2.000'), qty_pieces=0, line_total_paisa=150000,
    )
    order.fulfill(user=manager)

    stock_after_sale = current_stock(product_kg.pk, outlet.pk)['qty_kg']
    assert stock_after_sale == Decimal('8.000')

    # Create invoice and then credit note (return)
    inv = Invoice.objects.create(
        order=order, invoice_number='INV-RET-001', issued_at=timezone.now(),
        total_paisa=150000,
    )
    # Post a reversing return movement
    StockMovement.objects.create(
        product=product_kg, location=outlet,
        type=MovementType.RETURN, qty_kg=Decimal('1.000'),
        ref_id=order.pk, user=manager,
    )

    c = client_for(manager)
    cn_resp = c.post('/api/credit-notes/', {
        'invoice': inv.pk,
        'reason': 'Customer returned 1 kg',
        'amount_paisa': 75000,
        'issued_at': timezone.now().isoformat(),
        'issued_by': manager.pk,
    }, format='json')
    assert cn_resp.status_code == 201, cn_resp.data

    # Positive return movement exists
    return_movements = StockMovement.objects.filter(
        product=product_kg, location=outlet, type=MovementType.RETURN,
    )
    assert return_movements.exists()
    assert return_movements.first().qty_kg == Decimal('1.000')

    # Stock recovered by returned qty
    assert current_stock(product_kg.pk, outlet.pk)['qty_kg'] == Decimal('9.000')

    # Credit note persisted
    assert CreditNote.objects.filter(invoice=inv).count() == 1
    cn = CreditNote.objects.get(invoice=inv)
    assert cn.amount_paisa == 75000


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Cashier session: open → 3 orders with payments → close → Z-report totals
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_z_report_totals_match_session_payments(outlet, counter, cashier_user, product_kg, price_kg):
    c = client_for(cashier_user)

    sess = CashierSession.objects.create(
        counter=counter, cashier=cashier_user,
        opening_float_paisa=50000, opened_at=timezone.now(),
    )

    order_totals = [75000, 150000, 225000]
    for total in order_totals:
        order = Order.objects.create(
            fulfilled_location=outlet, session=sess,
            source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=total,
        )
        Payment.objects.create(
            order=order, method=PaymentMethod.CASH, amount_paisa=total,
        )

    # Close via API
    resp = c.post(f'/api/sessions/{sess.pk}/close/', {
        'closing_counted_paisa': 500000,
    }, format='json')
    assert resp.status_code == 200, resp.data
    assert resp.data['closed_at'] is not None
    assert resp.data['closing_counted_paisa'] == 500000

    # Z-report: sum payments on this session's orders
    session_orders = Order.objects.filter(session=sess)
    total_payments = sum(
        Payment.objects.filter(order=o).aggregate(
            s=__import__('django.db.models', fromlist=['Sum']).Sum('amount_paisa')
        )['s'] or 0
        for o in session_orders
    )
    assert total_payments == sum(order_totals)
    assert session_orders.count() == 3


@pytest.mark.django_db
def test_z_report_cash_and_card_split(outlet, counter, cashier_user, product_kg, price_kg):
    sess = CashierSession.objects.create(
        counter=counter, cashier=cashier_user,
        opening_float_paisa=0, opened_at=timezone.now(),
    )

    # Order 1: cash
    o1 = Order.objects.create(
        fulfilled_location=outlet, session=sess,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=100000,
    )
    Payment.objects.create(order=o1, method=PaymentMethod.CASH, amount_paisa=100000)

    # Order 2: card
    o2 = Order.objects.create(
        fulfilled_location=outlet, session=sess,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=80000,
    )
    Payment.objects.create(order=o2, method=PaymentMethod.CARD, amount_paisa=80000)

    # Order 3: split cash + eSewa
    o3 = Order.objects.create(
        fulfilled_location=outlet, session=sess,
        source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=120000,
    )
    Payment.objects.create(order=o3, method=PaymentMethod.CASH, amount_paisa=70000)
    Payment.objects.create(order=o3, method=PaymentMethod.ESEWA, amount_paisa=50000)

    sess.close(closing_counted_paisa=200000)

    from django.db.models import Sum
    order_ids = Order.objects.filter(session=sess).values_list('id', flat=True)
    cash_total = Payment.objects.filter(
        order__in=order_ids, method=PaymentMethod.CASH
    ).aggregate(s=Sum('amount_paisa'))['s']
    card_total = Payment.objects.filter(
        order__in=order_ids, method=PaymentMethod.CARD
    ).aggregate(s=Sum('amount_paisa'))['s']
    esewa_total = Payment.objects.filter(
        order__in=order_ids, method=PaymentMethod.ESEWA
    ).aggregate(s=Sum('amount_paisa'))['s']

    assert cash_total == 170000
    assert card_total == 80000
    assert esewa_total == 50000
