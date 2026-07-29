"""
Price changes must be possible through the API: POSTing a new active price
closes the outgoing one atomically instead of tripping the partial unique
constraint as a 500 (review finding C1).
"""
from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM
from apps.catalog.services import PriceRotationError, rotate_price


@pytest.fixture
def product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='mgr-price', password='x', role=Role.MANAGER)


@pytest.fixture
def manager_client(manager):
    client = APIClient()
    client.force_authenticate(manager)
    return client


@pytest.mark.django_db
def test_rotate_closes_old_and_creates_new(product):
    old = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from=date(2026, 1, 1),
    )
    new = rotate_price(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=80000, valid_from=date(2026, 6, 1),
    )
    old.refresh_from_db()
    assert old.valid_to == date(2026, 5, 31)
    assert new.valid_to is None
    assert Price.objects.filter(
        product=product, tier=PriceTier.RETAIL, valid_to__isnull=True
    ).count() == 1


@pytest.mark.django_db
def test_same_day_rotation_keeps_valid_range(product):
    old = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from=date(2026, 6, 1),
    )
    rotate_price(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=80000, valid_from=date(2026, 6, 1),
    )
    old.refresh_from_db()
    # Closing to the day before valid_from would invert the range; same-day
    # changes clamp to the old row's own valid_from.
    assert old.valid_to == old.valid_from


@pytest.mark.django_db
def test_rotation_predating_active_price_rejected(product):
    Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from=date(2026, 6, 1),
    )
    with pytest.raises(PriceRotationError):
        rotate_price(
            product=product, tier=PriceTier.RETAIL,
            price_paisa=80000, valid_from=date(2026, 1, 1),
        )


@pytest.mark.django_db
def test_rotation_without_existing_active_price(product):
    new = rotate_price(
        product=product, tier=PriceTier.WHOLESALE,
        price_paisa=65000, valid_from=date(2026, 6, 1),
    )
    assert new.valid_to is None


@pytest.mark.django_db
def test_api_price_change_returns_201_not_500(product, manager_client):
    Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from=date(2026, 1, 1),
    )
    res = manager_client.post('/api/prices/', {
        'product': product.pk, 'tier': 'retail',
        'price_paisa': 82000, 'valid_from': '2026-07-01',
    }, format='json')
    assert res.status_code == 201, res.content
    assert Price.objects.filter(
        product=product, tier=PriceTier.RETAIL, valid_to__isnull=True
    ).get().price_paisa == 82000


@pytest.mark.django_db
def test_api_backdated_price_change_returns_400(product, manager_client):
    Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from=date(2026, 6, 1),
    )
    res = manager_client.post('/api/prices/', {
        'product': product.pk, 'tier': 'retail',
        'price_paisa': 82000, 'valid_from': '2026-01-01',
    }, format='json')
    assert res.status_code == 400


@pytest.mark.django_db
def test_api_historical_row_does_not_rotate(product, manager_client):
    active = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from=date(2026, 1, 1),
    )
    res = manager_client.post('/api/prices/', {
        'product': product.pk, 'tier': 'retail',
        'price_paisa': 70000, 'valid_from': '2025-01-01', 'valid_to': '2025-12-31',
    }, format='json')
    assert res.status_code == 201
    active.refresh_from_db()
    assert active.valid_to is None


@pytest.mark.django_db
def test_api_inverted_date_range_rejected(product, manager_client):
    res = manager_client.post('/api/prices/', {
        'product': product.pk, 'tier': 'retail',
        'price_paisa': 70000, 'valid_from': '2025-12-31', 'valid_to': '2025-01-01',
    }, format='json')
    assert res.status_code == 400
