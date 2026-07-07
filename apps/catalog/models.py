from django.db import models

from apps.core.models import BaseModel


class UoM(models.TextChoices):
    KG    = 'kg',    'Kilogram'
    PIECE = 'piece', 'Piece'


class TaxClass(models.TextChoices):
    EXEMPT  = 'exempt',  'Exempt'
    TAXABLE = 'taxable', 'Taxable (13% VAT)'


class PriceTier(models.TextChoices):
    RETAIL    = 'retail',    'Retail'
    WHOLESALE = 'wholesale', 'Wholesale'
    MEMBER    = 'member',    'Member'


class Product(BaseModel):
    name      = models.CharField(max_length=200)
    barcode   = models.CharField(max_length=50, null=True, blank=True, unique=True)
    uom       = models.CharField(max_length=10, choices=UoM.choices)
    is_weighed = models.BooleanField(default=False)
    # Default exempt — management to confirm taxable products before enabling VAT.
    tax_class = models.CharField(max_length=10, choices=TaxClass.choices, default=TaxClass.EXEMPT)

    def __str__(self):
        return self.name


class Price(BaseModel):
    """
    Append-only price rows. A price change inserts a new row; existing rows are never
    mutated. Sales keep a FK to the exact price_id used so old orders always reproduce
    their original total.
    """
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    tier       = models.CharField(max_length=20, choices=PriceTier.choices)
    price_paisa = models.PositiveIntegerField()          # integer paisa — never float
    valid_from = models.DateField()
    valid_to   = models.DateField(null=True, blank=True)  # null = currently active

    class Meta:
        ordering = ['-valid_from']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'tier'],
                condition=models.Q(valid_to__isnull=True),
                name='unique_active_price_per_product_tier',
            ),
        ]

    def delete(self, *args, **kwargs):
        raise RuntimeError(
            'Price rows are immutable. Close the current price by setting valid_to, '
            'then insert a new Price row.'
        )

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError(
                'Price rows are immutable. Create a new Price row instead of updating.'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product} / {self.tier} / {self.price_paisa}p from {self.valid_from}'
