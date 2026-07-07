"""
Tests for unique_active_price_per_product_tier constraint:
only one Price with valid_to=None is allowed per (product, tier).
"""
import pytest
from django.db import IntegrityError

from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM


@pytest.fixture
def product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.mark.django_db
def test_two_active_prices_same_product_tier_raises(product):
    Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )
    with pytest.raises(IntegrityError):
        Price.objects.create(
            product=product, tier=PriceTier.RETAIL,
            price_paisa=80000, valid_from='2024-06-01',
        )


@pytest.mark.django_db
def test_active_prices_different_tiers_allowed(product):
    Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )
    p2 = Price.objects.create(
        product=product, tier=PriceTier.WHOLESALE,
        price_paisa=65000, valid_from='2024-01-01',
    )
    assert p2.pk is not None


@pytest.mark.django_db
def test_historical_prices_same_product_tier_allowed(product):
    # Both rows have valid_to set — neither is "active" — constraint does not apply.
    Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=70000, valid_from='2023-01-01', valid_to='2023-12-31',
    )
    p2 = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01', valid_to='2024-12-31',
    )
    assert p2.pk is not None


@pytest.mark.django_db
def test_close_old_price_then_create_new_active_allowed(product):
    # Create the initial active price.
    p1 = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )
    # Close it via queryset update (bypasses the immutable-row guard, which only
    # blocks .save() on an existing instance — a price-change workflow does this).
    Price.objects.filter(pk=p1.pk).update(valid_to='2024-05-31')

    # Now a new active price for the same product+tier is allowed.
    p2 = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=80000, valid_from='2024-06-01',
    )
    assert p2.pk is not None
    assert Price.objects.filter(product=product, tier=PriceTier.RETAIL, valid_to__isnull=True).count() == 1
