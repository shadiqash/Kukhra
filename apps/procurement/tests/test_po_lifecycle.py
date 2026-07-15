"""
Purchase order lifecycle: draft → sent → received, or cancelled along the way.

Receiving goods writes production movements into an append-only ledger, so the
guards matter: a double receipt would permanently double the stock, and a
cancelled PO has no goods coming.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Product, UoM
from apps.inventory.queries import current_stock
from apps.locations.models import Location, LocationType
from apps.partners.models import Supplier
from apps.procurement.models import GoodsReceived, PurchaseOrder, PurchaseOrderStatus


@pytest.fixture
def warehouse(db):
    return Location.objects.create(name='PO WH', type=LocationType.WAREHOUSE)


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(name='Kathmandu Poultry Farm')


@pytest.fixture
def buyer(db):
    return User.objects.create_user(username='po_buyer', password='x', role=Role.PROCUREMENT)


@pytest.fixture
def client(buyer):
    c = APIClient()
    c.force_authenticate(user=buyer)
    return c


@pytest.fixture
def product(db):
    return Product.objects.create(name='Live Bird', uom=UoM.KG)


@pytest.fixture
def po(db, supplier):
    return PurchaseOrder.objects.create(supplier=supplier, total_paisa=500_000)


def make_gr(po, warehouse):
    """Bypasses the API's send-first validation to test the model guards directly."""
    return GoodsReceived.objects.create(
        purchase_order=po, location=warehouse, received_at=timezone.now(),
    )


def sent(client, po):
    client.post(f'/api/purchase-orders/{po.pk}/send/')
    po.refresh_from_db()
    return po


def receive(client, gr, product, qty_kg):
    return client.post(f'/api/goods-received/{gr.pk}/receive/', {
        'lines': [{'product': product.pk, 'qty_kg': str(qty_kg), 'qty_pieces': 0}],
    }, format='json')


# ── The happy path ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_draft_to_sent_to_received(client, po, warehouse, product, buyer):
    assert po.status == PurchaseOrderStatus.DRAFT

    res = client.post(f'/api/purchase-orders/{po.pk}/send/')
    assert res.status_code == 200
    assert res.data['status'] == PurchaseOrderStatus.SENT

    gr = make_gr(po, warehouse)
    res = receive(client, gr, product, 200)
    assert res.status_code == 200

    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.RECEIVED
    # The goods are now real stock.
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('200.000')


@pytest.mark.django_db
def test_receipt_records_who_received_it(client, po, warehouse, product, buyer):
    gr = make_gr(sent(client, po), warehouse)
    receive(client, gr, product, 50)

    gr.refresh_from_db()
    assert gr.received_by == buyer


# ── Guards ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_draft_po_cannot_write_stock(client, po, warehouse, product):
    """
    Goods only arrive against a PO that went to a supplier. draft → received is not
    a legal edge, and the one path that moves stock must not be allowed to skip it.
    """
    gr = make_gr(po, warehouse)     # PO still draft
    res = receive(client, gr, product, 100)

    assert res.status_code == 400
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('0')
    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.DRAFT


@pytest.mark.django_db
def test_receipt_cannot_even_be_opened_against_a_draft_po(client, po, warehouse):
    """Rejected up front, so no orphan receipt document is left behind."""
    res = client.post('/api/goods-received/', {
        'purchase_order': po.pk, 'location': warehouse.pk,
        'received_at': timezone.now().isoformat(),
    }, format='json')

    assert res.status_code == 400
    assert GoodsReceived.objects.count() == 0


@pytest.mark.django_db
def test_cancelled_po_cannot_be_received(client, po, warehouse, product):
    res = client.post(f'/api/purchase-orders/{po.pk}/cancel/')
    assert res.status_code == 200

    gr = make_gr(po, warehouse)
    res = receive(client, gr, product, 100)

    assert res.status_code == 400
    assert 'cancelled' in str(res.data).lower()
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('0')


@pytest.mark.django_db
def test_po_cannot_be_received_twice(client, po, warehouse, product):
    """A second receipt would double the stock, permanently."""
    po = sent(client, po)
    gr = make_gr(po, warehouse)
    assert receive(client, gr, product, 100).status_code == 200

    second = make_gr(po, warehouse)
    res = receive(client, second, product, 100)

    assert res.status_code == 400
    assert 'already been received' in str(res.data)
    assert current_stock(product.pk, warehouse.pk)['qty_kg'] == Decimal('100.000')


@pytest.mark.django_db
def test_received_po_cannot_be_cancelled(client, po, warehouse, product):
    """The goods are in and the ledger has moved — cancelling would be a lie."""
    gr = make_gr(sent(client, po), warehouse)
    receive(client, gr, product, 100)

    res = client.post(f'/api/purchase-orders/{po.pk}/cancel/')
    assert res.status_code == 400


@pytest.mark.django_db
def test_a_receipt_cannot_be_edited_or_deleted_once_it_has_written_the_ledger(
    client, po, warehouse, product,
):
    """
    The receipt is the source document for append-only production movements.
    Editing its location, or deleting it, would let the document contradict
    the ledger rows it created.
    """
    gr = make_gr(sent(client, po), warehouse)
    receive(client, gr, product, 100)

    other = Location.objects.create(name='Elsewhere', type=LocationType.OUTLET)
    assert client.patch(f'/api/goods-received/{gr.pk}/', {'location': other.pk}, format='json').status_code == 405
    assert client.delete(f'/api/goods-received/{gr.pk}/').status_code == 405

    gr.refresh_from_db()
    assert gr.location == warehouse


@pytest.mark.django_db
def test_cancelled_po_cannot_be_sent(client, po):
    client.post(f'/api/purchase-orders/{po.pk}/cancel/')
    res = client.post(f'/api/purchase-orders/{po.pk}/send/')
    assert res.status_code == 400


@pytest.mark.django_db
def test_empty_receipt_is_rejected(client, po, warehouse):
    po = sent(client, po)
    gr = make_gr(po, warehouse)
    res = client.post(f'/api/goods-received/{gr.pk}/receive/', {'lines': []}, format='json')

    assert res.status_code == 400
    po.refresh_from_db()
    assert po.status == PurchaseOrderStatus.SENT   # not silently marked received


# ── Rule 7 ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cashier_cannot_touch_purchase_orders(po):
    cashier = User.objects.create_user(username='po_cashier', password='x', role=Role.CASHIER)
    c = APIClient()
    c.force_authenticate(user=cashier)

    assert c.get('/api/purchase-orders/').status_code == 403
    assert c.post(f'/api/purchase-orders/{po.pk}/send/').status_code == 403
