"""
Full role × endpoint access matrix, exercised for every user type in parallel.

One test per endpoint asserts the complete role vector (all 7 roles), so a
permission regression on any endpoint fails with a diff showing exactly which
role diverged. Run with `pytest -n auto` for parallel execution across workers.

Expected codes come from the role matrix documented in
apps/accounts/permissions.py — that comment block is the source of truth.
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.locations.models import Location, LocationType
from apps.partners.models import Customer, CustomerType

ALL_ROLES = (
    Role.SUPERUSER, Role.MANAGER, Role.OUTLET_MANAGER,
    Role.CASHIER, Role.WAREHOUSE, Role.PROCUREMENT, Role.CUSTOMER,
)


@pytest.fixture
def role_users(db):
    """One user per role. The customer-role user gets a linked Customer record;
    unlinked-customer behaviour is covered separately below."""
    outlet = Location.objects.create(name='Matrix Outlet', type=LocationType.OUTLET)
    customer = Customer.objects.create(name='Matrix Cust', type=CustomerType.RETAIL)
    users = {}
    for role in ALL_ROLES:
        u = User.objects.create_user(username=f'mx_{role}', password='x', role=role)
        if role == Role.OUTLET_MANAGER:
            u.assigned_locations.add(outlet)
        if role == Role.CUSTOMER:
            u.customer = customer
            u.save(update_fields=['customer'])
        users[role] = u
    return users


def status_for(user, url, method='get', data=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user=user)
    resp = getattr(c, method)(url, data or {}, format='json')
    return resp.status_code


# (url, {role: expected_status_for_GET_list})
# 200 = allowed; 403 = role blocked; 400 = allowed but endpoint demands params.
LIST_MATRIX = [
    ('/api/users/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 403,
        Role.CASHIER: 403, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/audit-logs/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 403,
        Role.CASHIER: 403, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/locations/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 200, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/counters/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 200, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/suppliers/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 200, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/customers/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 200, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/products/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 200, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/prices/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/lots/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 403,
        Role.CASHIER: 403, Role.WAREHOUSE: 200, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/processing-runs/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 403,
        Role.CASHIER: 403, Role.WAREHOUSE: 200, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/movements/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 403, Role.WAREHOUSE: 200, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/transfers/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 403, Role.WAREHOUSE: 200, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    # /api/stock/ demands product+location params, so allowed roles see 400.
    ('/api/stock/', {
        Role.SUPERUSER: 400, Role.MANAGER: 400, Role.OUTLET_MANAGER: 400,
        Role.CASHIER: 403, Role.WAREHOUSE: 400, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/purchase-orders/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 403,
        Role.CASHIER: 403, Role.WAREHOUSE: 403, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/goods-received/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 403,
        Role.CASHIER: 403, Role.WAREHOUSE: 403, Role.PROCUREMENT: 200, Role.CUSTOMER: 403,
    }),
    ('/api/payment-intents/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/sessions/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/orders/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 200,
    }),
    ('/api/order-lines/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/payments/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 200, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
    ('/api/invoices/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 403, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 200,
    }),
    ('/api/invoice-lines/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 403, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 200,
    }),
    ('/api/credit-notes/', {
        Role.SUPERUSER: 200, Role.MANAGER: 200, Role.OUTLET_MANAGER: 200,
        Role.CASHIER: 403, Role.WAREHOUSE: 403, Role.PROCUREMENT: 403, Role.CUSTOMER: 403,
    }),
]

LIST_URLS = [url for url, _ in LIST_MATRIX]


@pytest.mark.django_db
@pytest.mark.parametrize('url,expected', LIST_MATRIX, ids=LIST_URLS)
def test_list_access_all_roles(role_users, url, expected):
    actual = {role: status_for(role_users[role], url) for role in ALL_ROLES}
    assert actual == expected, f'{url}: role access diverged from matrix'


@pytest.mark.django_db
@pytest.mark.parametrize('url', LIST_URLS)
def test_anonymous_gets_401(url):
    assert status_for(None, url) == 401, f'{url}: anonymous must get 401'


# Critical write denials. POST with empty body: a blocked role must get 403
# (permission layer), never 400 (which would mean the serializer ran).
WRITE_DENIALS = [
    (Role.CASHIER, '/api/prices/'),          # setting prices is a manager decision
    (Role.CASHIER, '/api/invoices/'),
    (Role.CASHIER, '/api/credit-notes/'),
    (Role.CASHIER, '/api/movements/'),
    (Role.CASHIER, '/api/users/'),
    (Role.WAREHOUSE, '/api/orders/'),
    (Role.WAREHOUSE, '/api/payments/'),
    (Role.WAREHOUSE, '/api/prices/'),
    (Role.PROCUREMENT, '/api/orders/'),
    (Role.OUTLET_MANAGER, '/api/orders/'),
    (Role.OUTLET_MANAGER, '/api/movements/'),
    (Role.OUTLET_MANAGER, '/api/payment-intents/'),
    (Role.OUTLET_MANAGER, '/api/products/'),
    (Role.OUTLET_MANAGER, '/api/prices/'),
    (Role.OUTLET_MANAGER, '/api/users/'),
    (Role.CUSTOMER, '/api/orders/'),         # app ordering is Phase 2
    (Role.CUSTOMER, '/api/invoices/'),
    (Role.CUSTOMER, '/api/products/'),
]


@pytest.mark.django_db
@pytest.mark.parametrize(
    'role,url', WRITE_DENIALS,
    ids=[f'{role}-POST-{url}' for role, url in WRITE_DENIALS],
)
def test_write_denied(role_users, role, url):
    code = status_for(role_users[role], url, method='post')
    assert code == 403, f'BUG: {role} POST {url} returned {code}, expected 403'


# ── Customer data scoping — a customer must only ever see their own documents ──

@pytest.fixture
def two_customer_invoices(db, role_users):
    """Two invoices: one for the linked customer-role user, one walk-in (customer NULL)."""
    from django.utils import timezone

    from apps.billing.models import Invoice, InvoiceLine
    from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
    from apps.locations.models import Counter
    from apps.sales.models import CashierSession, Order, OrderSource, OrderStatus

    outlet = Location.objects.get(name='Matrix Outlet')
    counter = Counter.objects.create(location=outlet, name='MX-C1')
    sess = CashierSession.objects.create(
        counter=counter, cashier=role_users[Role.CASHIER],
        opening_float_paisa=0, opened_at=timezone.now(),
    )
    product = Product.objects.create(name='MX Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)
    price = Price.objects.create(
        product=product, tier=PriceTier.RETAIL, price_paisa=50000, valid_from='2024-01-01',
    )
    own_customer = role_users[Role.CUSTOMER].customer

    def make_invoice(number, customer):
        order = Order.objects.create(
            customer=customer, fulfilled_location=outlet, session=sess,
            source=OrderSource.COUNTER, status=OrderStatus.FULFILLED, total_paisa=50000,
        )
        inv = Invoice.objects.create(
            order=order, customer=customer, invoice_number=number,
            issued_at=timezone.now(), total_paisa=50000,
        )
        InvoiceLine.objects.create(
            invoice=inv, product=product, price=price, tax_class=TaxClass.EXEMPT,
            qty_kg=1, unit_paisa=50000, line_total_paisa=50000,
        )
        return inv

    return {
        'own': make_invoice('MX-OWN-1', own_customer),
        'walkin': make_invoice('MX-WALKIN-1', None),
    }


@pytest.mark.django_db
def test_customer_sees_only_own_invoices(role_users, two_customer_invoices):
    c = APIClient()
    c.force_authenticate(user=role_users[Role.CUSTOMER])
    ids = [row['id'] for row in c.get('/api/invoices/').data['results']]
    assert two_customer_invoices['own'].pk in ids
    assert two_customer_invoices['walkin'].pk not in ids, \
        'LEAK: customer can see walk-in invoices'


@pytest.mark.django_db
def test_customer_sees_only_own_invoice_lines(role_users, two_customer_invoices):
    c = APIClient()
    c.force_authenticate(user=role_users[Role.CUSTOMER])
    invoice_ids = {row['invoice'] for row in c.get('/api/invoice-lines/').data['results']}
    assert invoice_ids <= {two_customer_invoices['own'].pk}, \
        'LEAK: customer can see other customers\' invoice lines'


@pytest.mark.django_db
def test_unlinked_customer_sees_nothing(db, two_customer_invoices):
    """A customer-role user with no linked Customer record must fall closed."""
    orphan = User.objects.create_user(username='mx_orphan', password='x', role=Role.CUSTOMER)
    c = APIClient()
    c.force_authenticate(user=orphan)
    for url in ('/api/invoices/', '/api/invoice-lines/', '/api/orders/'):
        results = c.get(url).data['results']
        assert results == [], f'LEAK: unlinked customer sees rows at {url}'


# ── Immutability over HTTP — money-bearing records reject PATCH/DELETE ────────

@pytest.mark.django_db
def test_sessions_and_invoices_are_immutable_over_http(role_users, two_customer_invoices):
    """PATCH/DELETE must be structurally absent (405) even for managers: a
    drawer count or an issued invoice is corrected by reversing rows, not edits."""
    from apps.sales.models import CashierSession

    inv = two_customer_invoices['own']
    sess = CashierSession.objects.get()
    for role, url in [
        (Role.MANAGER, f'/api/invoices/{inv.pk}/'),
        (Role.MANAGER, f'/api/sessions/{sess.pk}/'),
        (Role.CASHIER, f'/api/sessions/{sess.pk}/'),  # not even their own
    ]:
        for method in ('patch', 'delete'):
            code = status_for(role_users[role], url, method=method)
            assert code == 405, f'BUG: {role} {method.upper()} {url} returned {code}'


@pytest.mark.django_db
def test_cashier_session_delete_blocked_at_model_level(role_users, two_customer_invoices):
    from apps.sales.models import CashierSession

    with pytest.raises(RuntimeError):
        CashierSession.objects.get().delete()
