from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.lots.models import Lot


class ProcessingRun(BaseModel):
    """
    One slaughter/processing event on a Lot. Creating a ProcessingRun is a side-effectful
    operation: the caller must also create StockMovement(type=production) rows for each
    output product (done in build step 5 / 6).
    """
    lot              = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name='processing_runs')
    run_at           = models.DateTimeField()
    input_weight_kg  = models.DecimalField(max_digits=10, decimal_places=3)
    output_weight_kg = models.DecimalField(max_digits=10, decimal_places=3)
    operator         = models.ForeignKey(
                           settings.AUTH_USER_MODEL,
                           on_delete=models.PROTECT,
                           related_name='processing_runs',
                       )

    def __str__(self):
        return f'ProcessingRun #{self.pk} on {self.lot} at {self.run_at:%Y-%m-%d}'
