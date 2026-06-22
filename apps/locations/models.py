from django.db import models

from apps.core.models import BaseModel


class LocationType(models.TextChoices):
    FARM       = 'farm',       'Farm'
    PRODUCTION = 'production', 'Production'
    WAREHOUSE  = 'warehouse',  'Warehouse'
    OUTLET     = 'outlet',     'Outlet'


class Location(BaseModel):
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=LocationType.choices)
    lat  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f'{self.name} ({self.get_type_display()})'


class Counter(BaseModel):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='counters')
    name     = models.CharField(max_length=200)

    def __str__(self):
        return f'{self.name} @ {self.location}'
