import logging
from datetime import date, timedelta

from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='sales.nightly_rollup')
def nightly_rollup(target_date: str | None = None):
    """
    Aggregate completed orders for target_date (default: yesterday) into a
    DailySalesRollup row.  Idempotent: if a row already exists for that date,
    it is overwritten.
    """
    from apps.sales.models import DailySalesRollup, Order, OrderStatus

    if target_date:
        rollup_date = date.fromisoformat(target_date)
    else:
        rollup_date = (timezone.now() - timedelta(days=1)).date()

    day_orders = Order.objects.filter(
        status=OrderStatus.FULFILLED,
        created_at__date=rollup_date,
    )
    order_count = day_orders.count()
    total_revenue = day_orders.aggregate(total_revenue=Sum('total_paisa'))['total_revenue'] or 0

    rollup, created = DailySalesRollup.objects.update_or_create(
        date=rollup_date,
        defaults={
            'order_count': order_count,
            'total_revenue_paisa': total_revenue,
        },
    )

    action = 'created' if created else 'updated'
    logger.info(
        'nightly_rollup: %s rollup for %s — %d orders, %d paisa',
        action, rollup_date, order_count, total_revenue,
    )
    return {
        'date': str(rollup_date),
        'order_count': order_count,
        'total_revenue_paisa': total_revenue,
        'action': action,
    }
