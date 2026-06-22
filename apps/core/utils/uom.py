"""Unit-of-measure conversion helpers."""
from decimal import Decimal

KG = 'kg'
PIECE = 'piece'

_THOUSAND = Decimal('1000')
_PRECISION = Decimal('0.001')


def grams_to_kg(grams: Decimal) -> Decimal:
    return (grams / _THOUSAND).quantize(_PRECISION)


def kg_to_grams(kg: Decimal) -> Decimal:
    return (kg * _THOUSAND).quantize(_PRECISION)
