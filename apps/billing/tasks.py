import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name='billing.cbms_sync')
def cbms_sync():
    """
    Stub: find pending invoices and credit notes, log them, and mark as synced.
    Real IRD/CBMS API call is Phase 2.
    """
    from apps.billing.models import CbmsStatus, Invoice

    batch_size = getattr(settings, 'CBMS_SYNC_BATCH_SIZE', 50)

    pending_invoices = list(
        Invoice.objects.filter(cbms_status=CbmsStatus.PENDING)[:batch_size]
    )

    synced_invoices = []
    for inv in pending_invoices:
        logger.info(
            'CBMS SYNC (stub): invoice id=%d number=%s total=%d paisa → would POST to IRD',
            inv.pk, inv.invoice_number, inv.total_paisa,
        )
        synced_invoices.append(inv.pk)

    if pending_invoices:
        Invoice.objects.filter(pk__in=synced_invoices).update(cbms_status=CbmsStatus.SYNCED)

    logger.info('cbms_sync: synced %d invoice(s)', len(synced_invoices))
    return {'synced_invoices': synced_invoices}
