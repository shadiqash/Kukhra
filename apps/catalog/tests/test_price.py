import pytest
from django.utils import timezone

from apps.catalog.models import Price, PriceTier, Product, TaxClass, UoM


@pytest.fixture
def product(db):
    return Product.objects.create(name='Whole Chicken', uom=UoM.KG, tax_class=TaxClass.EXEMPT)


@pytest.mark.django_db
def test_price_insert_succeeds(product):
    p = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )
    assert p.pk is not None


@pytest.mark.django_db
def test_price_update_raises(product):
    p = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )
    p.price_paisa = 80000
    with pytest.raises(RuntimeError):
        p.save()


@pytest.mark.django_db
def test_price_delete_raises(product):
    p = Price.objects.create(
        product=product, tier=PriceTier.RETAIL,
        price_paisa=75000, valid_from='2024-01-01',
    )
    with pytest.raises(RuntimeError):
        p.delete()


@pytest.mark.django_db
def test_price_paisa_is_integer(product):
    p = Price.objects.create(
        product=product, tier=PriceTier.WHOLESALE,
        price_paisa=60000, valid_from='2024-01-01',
    )
    assert isinstance(p.price_paisa, int)
