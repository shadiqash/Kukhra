import pytest
from apps.core.utils.money import assert_paisa, paisa_to_display


def test_paisa_to_display_positive():
    assert paisa_to_display(123456) == 'Rs 1,234.56'


def test_paisa_to_display_zero():
    assert paisa_to_display(0) == 'Rs 0.00'


def test_paisa_to_display_negative():
    assert paisa_to_display(-5050) == '-Rs 50.50'


def test_assert_paisa_accepts_int():
    assert assert_paisa(500) == 500


def test_assert_paisa_rejects_float():
    with pytest.raises(TypeError):
        assert_paisa(5.00)


def test_assert_paisa_rejects_string():
    with pytest.raises(TypeError):
        assert_paisa('500')
