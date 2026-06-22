from django.db import models

from apps.core.models import BaseModel


class SupplierType(models.TextChoices):
    FARM     = 'farm',     'Farm'
    FEED     = 'feed',     'Feed Supplier'
    MEDICINE = 'medicine', 'Medicine Supplier'


class CustomerType(models.TextChoices):
    RETAIL    = 'retail',    'Retail'
    WHOLESALE = 'wholesale', 'Wholesale'


class Supplier(BaseModel):
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=SupplierType.choices)
    pan  = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f'{self.name} ({self.get_type_display()})'


class Customer(BaseModel):
    name               = models.CharField(max_length=200)
    type               = models.CharField(max_length=20, choices=CustomerType.choices)
    pan                = models.CharField(max_length=20, null=True, blank=True)
    credit_limit_paisa = models.PositiveBigIntegerField(default=0)
    lat                = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng                = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f'{self.name} ({self.get_type_display()})'
