import logging

from celery import shared_task
from django.conf import settings
from django.db.models import Sum

logger = logging.getLogger(__name__)


@shared_task(name='inventory.low_stock_alert')
def low_stock_alert():
    """
    Scan all (product, location) pairs and log those whose current stock falls
    below LOW_STOCK_THRESHOLD_KG.
    """
    from apps.inventory.models import StockMovement

    threshold = getattr(settings, 'LOW_STOCK_THRESHOLD_KG', 10)

    pairs = list(
        StockMovement.objects
        .values('product_id', 'location_id')
        .annotate(total_kg=Sum('qty_kg'))
        .filter(total_kg__lt=threshold)
    )

    alerts = []
    for row in pairs:
        logger.warning(
            'LOW STOCK: product_id=%s location_id=%s stock=%s kg (threshold=%s kg)',
            row['product_id'], row['location_id'], row['total_kg'], threshold,
        )
        alerts.append({
            'product_id': row['product_id'],
            'location_id': row['location_id'],
            'total_kg': float(row['total_kg']),
        })

    logger.info('low_stock_alert: checked %d pair(s), %d alert(s)', len(pairs), len(alerts))
    return {'alerts': alerts, 'threshold_kg': threshold}
