from decimal import Decimal

import pytest

from finance.model.errors import FinanceError
from finance.model.money import format_amount, parse_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("50", Decimal("50.00")),
        ("-12.5", Decimal("-12.50")),
        ("1.234,56", Decimal("1234.56")),
        ("R$ 99,90", Decimal("99.90")),
        ("0.005", Decimal("0.01")),
    ],
)
def test_parse_amount(text: str, expected: Decimal) -> None:
    assert parse_amount(text) == expected


def test_parse_amount_rejects_garbage() -> None:
    with pytest.raises(FinanceError, match="valor inválido"):
        parse_amount("abc")


def test_format_amount_two_places() -> None:
    assert format_amount(Decimal("-7")) == "-7.00"
    assert format_amount(Decimal("1234.5")) == "1234.50"
