"""
Paisa helpers.

All monetary values in the system are stored and computed as integer paisa.
Never pass floats through these helpers — pass integers only.
"""


def paisa_to_display(paisa: int) -> str:
    """'Rs 1,234.56' string for display only — never for arithmetic."""
    if not isinstance(paisa, int):
        raise TypeError(f'Expected int paisa, got {type(paisa).__name__}: {paisa!r}')
    sign = '-' if paisa < 0 else ''
    rupees, paise = divmod(abs(paisa), 100)
    return f'{sign}Rs {rupees:,}.{paise:02d}'


def assert_paisa(value: object, field: str = 'value') -> int:
    """Raise TypeError if value is not an integer paisa amount."""
    if not isinstance(value, int):
        raise TypeError(
            f'{field} must be integer paisa, got {type(value).__name__}: {value!r}'
        )
    return value
