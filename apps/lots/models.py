from django.db import models

from apps.core.models import BaseModel
from apps.locations.models import Location
from apps.partners.models import Supplier


class LotStatus(models.TextChoices):
    ARRIVAL    = 'arrival',    'Arrival'
    GRADING    = 'grading',    'Grading'
    STORAGE    = 'storage',    'Storage'
    SLAUGHTER  = 'slaughter',  'Slaughter'
    PACKAGING  = 'packaging',  'Packaging'
    SALE       = 'sale',       'Sale'
    SETTLEMENT = 'settlement', 'Settlement'


# Explicit whitelist — only these moves are legal.
VALID_TRANSITIONS: dict[str, set[str]] = {
    LotStatus.ARRIVAL:    {LotStatus.GRADING},
    LotStatus.GRADING:    {LotStatus.STORAGE, LotStatus.SLAUGHTER},
    LotStatus.STORAGE:    {LotStatus.SLAUGHTER},
    LotStatus.SLAUGHTER:  {LotStatus.PACKAGING},
    LotStatus.PACKAGING:  {LotStatus.SALE},
    LotStatus.SALE:       {LotStatus.SETTLEMENT},
    LotStatus.SETTLEMENT: set(),
}


class Lot(BaseModel):
    code                 = models.CharField(max_length=50, unique=True)
    source_type          = models.CharField(max_length=10, choices=[('own', 'Own'), ('external', 'External')])
    supplier             = models.ForeignKey(
                               Supplier, null=True, blank=True,
                               on_delete=models.PROTECT, related_name='lots',
                           )
    arrival_location     = models.ForeignKey(
                               Location, on_delete=models.PROTECT, related_name='arrived_lots',
                           )
    live_weight_kg       = models.DecimalField(max_digits=10, decimal_places=3)
    bird_count           = models.PositiveIntegerField()
    # Cost allocation method TBD (by weight vs sales value). Stub for now.
    accumulated_cost_paisa = models.PositiveBigIntegerField(default=0)
    status               = models.CharField(
                               max_length=20, choices=LotStatus.choices, default=LotStatus.ARRIVAL,
                           )

    def transition(self, new_status: str) -> None:
        """Advance the lot status. Raises ValueError on an illegal move."""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f'Illegal lot transition: {self.status!r} → {new_status!r}. '
                f'Allowed from {self.status!r}: {sorted(allowed) or "none"}'
            )
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])

    def __str__(self):
        return f'Lot {self.code} [{self.status}]'
