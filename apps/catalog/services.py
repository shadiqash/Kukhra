"""
Price rotation — the single sanctioned write path that closes a Price row.

Price.save() blocks all updates so price history stays immutable, which means
setting valid_to on the outgoing row must go through queryset.update(). That
bypass is legal *only here*: rotation closes the old row and inserts the new
one in the same transaction, so the "one active price per (product, tier)"
constraint is never violated and no order can reference a half-rotated state.
"""
from datetime import timedelta

from django.db import transaction

from .models import Price


class PriceRotationError(ValueError):
    """The requested rotation is inconsistent with the existing active price."""


@transaction.atomic
def rotate_price(*, product, tier, price_paisa: int, valid_from):
    """
    Make (product, tier) cost `price_paisa` from `valid_from` onward.

    Closes the currently active price (valid_to = day before `valid_from`, but
    never earlier than its own valid_from for a same-day change) and inserts
    the new active row. Returns the new Price.

    Concurrency: the active row is read under select_for_update, so two
    simultaneous rotations serialize; the loser re-reads after commit and
    either sees no active row (Postgres re-evaluates the predicate after the
    lock wait) or the closed one. A residual race on insert surfaces as the
    unique-constraint IntegrityError, which the caller maps to a 400.
    """
    current = (
        Price.objects.select_for_update()
        .filter(product=product, tier=tier, valid_to__isnull=True)
        .first()
    )
    if current is not None:
        if valid_from < current.valid_from:
            raise PriceRotationError(
                f'valid_from {valid_from} predates the active price '
                f'(effective since {current.valid_from}).'
            )
        closed_to = max(valid_from - timedelta(days=1), current.valid_from)
        Price.objects.filter(pk=current.pk).update(valid_to=closed_to)
    return Price.objects.create(
        product=product, tier=tier, price_paisa=price_paisa, valid_from=valid_from,
    )
