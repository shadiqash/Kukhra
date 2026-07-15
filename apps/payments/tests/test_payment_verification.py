"""
Digital payments must be unforgeable.

Before this, a cashier could pick "eSewa", type any reference, and the system
recorded the money as received without ever contacting the gateway. These tests
are written as attacks: each one is a way to get goods without paying, and each
one must fail.
"""
from decimal import Decimal

import pytest
from django.db.utils import IntegrityError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.inventory.models import MovementType, StockMovement
from apps.inventory.queries import current_stock
from apps.locations.models import Counter, Location, LocationType
from apps.payments.gateways import mock as mock_gateway
from apps.payments.models import Gateway, IntentStatus, PaymentIntent
from apps.sales.models import CashierSession, Order, OrderSource, Payment, PaymentMethod


@pytest.fixture(autouse=True)
def clean_gateway():
    mock_gateway.reset()
    yield
    mock_gateway.reset()


@pytest.fixture
def outlet(db):
    return Location.objects.create(name='Pay Outlet', type=LocationType.OUTLET)


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='pay_cashier', password='x', role=Role.CASHIER)


@pytest.fixture
def session(db, outlet, cashier):
    counter = Counter.objects.create(location=outlet, name='Pay Till')
    return CashierSession.objects.create(
        counter=counter, cashier=cashier, opening_float_paisa=0, opened_at=timezone.now(),
    )


@pytest.fixture
def product(db):
    return Product.objects.create(name='Pay Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def price(db, product):
    return Price.objects.create(
        product=product, tier=PriceTier.RETAIL, price_paisa=50_000, valid_from='2024-01-01',
    )


@pytest.fixture
def client(cashier):
    c = APIClient()
    c.force_authenticate(user=cashier)
    return c


@pytest.fixture
def stocked(db, product, outlet, cashier):
    StockMovement.objects.create(
        product=product, location=outlet, type=MovementType.PRODUCTION,
        qty_kg=Decimal('100.000'), user=cashier,
    )


def make_intent(client, outlet, session, amount_paisa):
    res = client.post('/api/payment-intents/', {
        'gateway': Gateway.MOCK,
        'amount_paisa': amount_paisa,
        'fulfilled_location': outlet.pk,
        'session': session.pk,
    }, format='json')
    assert res.status_code == 201, res.data
    return res.data


def checkout(client, outlet, session, product, price, *, amount_paisa, payment):
    return client.post('/api/orders/', {
        'fulfilled_location': outlet.pk,
        'session': session.pk,
        'source': OrderSource.COUNTER,
        'total_paisa': amount_paisa,
        'lines': [{
            'product': product.pk, 'price': price.pk,
            'qty_kg': '1.000', 'qty_pieces': 0, 'line_total_paisa': amount_paisa,
        }],
        'payments': [payment],
    }, format='json')


# ── The happy path ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_verified_qr_payment_completes_the_sale(client, outlet, session, product, price, stocked):
    intent = make_intent(client, outlet, session, 50_000)
    assert intent['status'] == IntentStatus.INITIATED
    assert intent['qr_payload']                     # something to show the customer

    mock_gateway.settle(intent['prn'], 50_000)     # the customer scans and pays

    res = client.post(f'/api/payment-intents/{intent["id"]}/verify/')
    assert res.data['status'] == IntentStatus.VERIFIED

    res = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment={
        'method': PaymentMethod.FONEPAY, 'amount_paisa': 50_000, 'intent': intent['id'],
    })
    assert res.status_code == 201, res.data

    # Money proven, stock moved, intent spent.
    payment = Payment.objects.get(order_id=res.data['id'])
    assert payment.intent_id == intent['id']
    assert PaymentIntent.objects.get(pk=intent['id']).status == IntentStatus.CONSUMED
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('99.000')


# ── Attacks ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cannot_claim_a_digital_payment_without_an_intent(client, outlet, session, product, price, stocked):
    """The old behaviour: pick eSewa, type a reference, walk out with the chicken."""
    res = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment={
        'method': PaymentMethod.ESEWA, 'amount_paisa': 50_000, 'ref': 'I promise I paid',
    })

    assert res.status_code == 400
    assert Order.objects.count() == 0
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('100.000')


@pytest.mark.django_db
def test_cannot_spend_an_unverified_intent(client, outlet, session, product, price, stocked):
    """Generating a QR is not paying. Nobody scanned it."""
    intent = make_intent(client, outlet, session, 50_000)

    res = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment={
        'method': PaymentMethod.FONEPAY, 'amount_paisa': 50_000, 'intent': intent['id'],
    })

    assert res.status_code == 400
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_polling_an_unpaid_intent_does_not_verify_it(client, outlet, session):
    """The gateway says pending; hammering verify must not wear it down."""
    intent = make_intent(client, outlet, session, 50_000)

    for _ in range(5):
        res = client.post(f'/api/payment-intents/{intent["id"]}/verify/')
        assert res.data['status'] == IntentStatus.INITIATED


@pytest.mark.django_db
def test_underpayment_is_rejected_not_reconciled(client, outlet, session):
    """
    The customer pays Rs 100 against a Rs 500 basket. Accepting it and 'reconciling'
    would hand over the goods for a fifth of the price.
    """
    intent = make_intent(client, outlet, session, 50_000)
    mock_gateway.settle(intent['prn'], 10_000)          # paid far less

    res = client.post(f'/api/payment-intents/{intent["id"]}/verify/')

    assert res.data['status'] == IntentStatus.FAILED
    assert 'mismatch' in res.data['failure_reason'].lower()


@pytest.mark.django_db
def test_intent_amount_cannot_be_restated_at_checkout(client, outlet, session, product, price, stocked):
    """
    A Rs 100 QR is paid, then the basket claims that payment covers Rs 500.
    The intent's amount is the server's, not the client's.
    """
    intent = make_intent(client, outlet, session, 10_000)
    mock_gateway.settle(intent['prn'], 10_000)
    client.post(f'/api/payment-intents/{intent["id"]}/verify/')

    res = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment={
        'method': PaymentMethod.FONEPAY, 'amount_paisa': 50_000, 'intent': intent['id'],
    })

    assert res.status_code == 400
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_one_paid_qr_cannot_settle_two_baskets(client, outlet, session, product, price, stocked):
    """The replay attack: scan once, keep re-using the same verified payment."""
    intent = make_intent(client, outlet, session, 50_000)
    mock_gateway.settle(intent['prn'], 50_000)
    client.post(f'/api/payment-intents/{intent["id"]}/verify/')

    payment = {'method': PaymentMethod.FONEPAY, 'amount_paisa': 50_000, 'intent': intent['id']}

    first = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment=payment)
    assert first.status_code == 201

    second = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment=payment)
    assert second.status_code == 400

    assert Order.objects.count() == 1
    assert current_stock(product.pk, outlet.pk)['qty_kg'] == Decimal('99.000')   # one bird, not two


@pytest.mark.django_db
def test_a_failed_intent_can_never_be_spent(client, outlet, session, product, price, stocked):
    intent = make_intent(client, outlet, session, 50_000)
    mock_gateway.fail(intent['prn'])
    client.post(f'/api/payment-intents/{intent["id"]}/verify/')

    res = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment={
        'method': PaymentMethod.FONEPAY, 'amount_paisa': 50_000, 'intent': intent['id'],
    })
    assert res.status_code == 400


@pytest.mark.django_db
def test_a_verified_intent_cannot_be_downgraded_by_a_later_gateway_lie(client, outlet, session):
    """
    Once verified, the intent is terminal. A gateway (or a spoofed callback) that
    later claims a different amount cannot rewrite settled money.
    """
    intent = make_intent(client, outlet, session, 50_000)
    mock_gateway.settle(intent['prn'], 50_000)
    client.post(f'/api/payment-intents/{intent["id"]}/verify/')

    mock_gateway.settle(intent['prn'], 999_999)      # the gateway changes its story
    res = client.post(f'/api/payment-intents/{intent["id"]}/verify/')

    assert res.data['status'] == IntentStatus.VERIFIED
    assert res.data['amount_paisa'] == 50_000


@pytest.mark.django_db
def test_database_itself_refuses_a_digital_payment_with_no_intent(outlet, session, cashier, product):
    """
    Defence in depth: not merely the serializer in front of it today. Any future code
    path that tries to write an unproven digital payment must fail at the constraint.
    """
    order = Order.objects.create(
        fulfilled_location=outlet, session=session,
        source=OrderSource.COUNTER, total_paisa=50_000,
    )
    with pytest.raises(IntegrityError):
        Payment.objects.create(
            order=order, method=PaymentMethod.FONEPAY, amount_paisa=50_000, intent=None,
        )


@pytest.mark.django_db
def test_cash_still_works_and_needs_no_intent(client, outlet, session, product, price, stocked):
    """The gateway rules must not get in the way of the cash till."""
    res = checkout(client, outlet, session, product, price, amount_paisa=50_000, payment={
        'method': PaymentMethod.CASH, 'amount_paisa': 50_000, 'ref': None,
    })
    assert res.status_code == 201


@pytest.mark.django_db
def test_a_cashier_cannot_see_another_cashiers_intents(client, outlet, session):
    make_intent(client, outlet, session, 50_000)

    other = User.objects.create_user(username='other_cashier', password='x', role=Role.CASHIER)
    c = APIClient()
    c.force_authenticate(user=other)

    res = c.get('/api/payment-intents/')
    assert res.data['results'] == []


@pytest.mark.django_db
def test_disabled_gateway_is_refused(client, outlet, session, settings):
    """A gateway not enabled for this deployment cannot be invoked by asking nicely."""
    settings.PAYMENT_GATEWAYS = ['fonepay']          # mock switched off, as in production

    res = client.post('/api/payment-intents/', {
        'gateway': Gateway.MOCK,
        'amount_paisa': 50_000,
        'fulfilled_location': outlet.pk,
        'session': session.pk,
    }, format='json')

    assert res.status_code == 502
