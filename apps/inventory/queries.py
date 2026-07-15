"""
Read-side helpers for the inventory ledger.
All stock computations derive from StockMovement aggregates — never from stored columns.
"""
from decimal import Decimal

from django.db.models import Sum

from .models import StockMovement


def stock_matrix(location_ids=None, product_ids=None) -> list[dict]:
    """
    Return current stock for every (product, location) pair that has movements,
    as a single aggregate query — the bulk counterpart to current_stock().

    Same derivation rule: stock is SUM(qty) over the ledger, never a stored column.
    Pairs whose movements net to zero are still returned, so a product that sold
    out reads as 0 rather than silently vanishing from the grid.

    Returns a list of {'product', 'location', 'qty_kg', 'qty_pieces'} dicts.
    """
    qs = StockMovement.objects.all()
    if location_ids is not None:
        qs = qs.filter(location_id__in=location_ids)
    if product_ids is not None:
        qs = qs.filter(product_id__in=product_ids)

    rows = (
        qs.values('product_id', 'location_id')
        .annotate(qty_kg=Sum('qty_kg'), qty_pieces=Sum('qty_pieces'))
        .order_by('location_id', 'product_id')
    )
    return [
        {
            'product':    r['product_id'],
            'location':   r['location_id'],
            'qty_kg':     r['qty_kg']     if r['qty_kg']     is not None else Decimal('0'),
            'qty_pieces': r['qty_pieces'] if r['qty_pieces'] is not None else 0,
        }
        for r in rows
    ]


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
