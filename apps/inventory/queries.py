"""
Read-side helpers for the inventory ledger.
All stock computations derive from StockMovement aggregates — never from stored columns.
"""
from decimal import Decimal

from django.db.models import Sum

from .models import StockMovement


def current_stock(product_id: int, location_id: int) -> dict:
    """
    Return current stock for a single (product, location) pair.

    current_stock = SUM(qty_kg), SUM(qty_pieces) over all StockMovement rows
    for the given product and location. Signed values cancel correctly:
    a sale row of -3 kg plus a production row of +10 kg yields 7 kg.

    Returns {'qty_kg': Decimal, 'qty_pieces': int}.
    Never returns None; no-movement case returns zeros.
    """
    agg = (
        StockMovement.objects
        .filter(product_id=product_id, location_id=location_id)
        .aggregate(qty_kg=Sum('qty_kg'), qty_pieces=Sum('qty_pieces'))
    )
    return {
        'qty_kg':     agg['qty_kg']     if agg['qty_kg']     is not None else Decimal('0'),
        'qty_pieces': agg['qty_pieces'] if agg['qty_pieces'] is not None else 0,
    }
