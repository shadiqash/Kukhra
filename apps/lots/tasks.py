import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='lots.expiry_alert')
def expiry_alert():
    """
    Log lots that are still active (not yet at 'settlement') and arrived more
    than LOT_EXPIRY_ALERT_DAYS ago without being fully processed.
    """
    from apps.lots.models import Lot, LotStatus

    alert_days = getattr(settings, 'LOT_EXPIRY_ALERT_DAYS', 3)
    cutoff = timezone.now() - timedelta(days=alert_days)

    stale_statuses = [
        LotStatus.ARRIVAL,
        LotStatus.GRADING,
        LotStatus.STORAGE,
        LotStatus.SLAUGHTER,
        LotStatus.PACKAGING,
    ]

    stale_lots = Lot.objects.filter(
        status__in=stale_statuses,
        created_at__lt=cutoff,
    ).values('id', 'code', 'status', 'created_at')

    alerts = []
    for lot in stale_lots:
        age_days = (timezone.now() - lot['created_at']).days
        msg = (
            f'EXPIRY ALERT: lot={lot["code"]} id={lot["id"]} '
            f'status={lot["status"]} age={age_days}d (threshold={alert_days}d)'
        )
        logger.warning(msg)
        alerts.append({'lot_id': lot['id'], 'lot_code': lot['code'], 'status': lot['status'], 'age_days': age_days})

    logger.info('expiry_alert: %d stale lot(s) found', len(alerts))
    return {'alerts': alerts, 'alert_days': alert_days}
