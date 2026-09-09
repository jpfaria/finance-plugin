from datetime import date

import pytest

from finance.model.dates import add_months, clamp_day, parse_month
from finance.model.errors import FinanceError


def test_add_months_clamps_to_month_end() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 1, 31), 2) == date(2026, 3, 31)
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)


def test_add_months_negative() -> None:
    assert add_months(date(2026, 3, 31), -1) == date(2026, 2, 28)


def test_clamp_day() -> None:
    assert clamp_day(2026, 2, 31) == date(2026, 2, 28)
    assert clamp_day(2026, 4, 10) == date(2026, 4, 10)


def test_parse_month() -> None:
    assert parse_month("2026-09") == (2026, 9)


@pytest.mark.parametrize("bad", ["2026", "09/2026", "2026-13"])
def test_parse_month_rejects(bad: str) -> None:
    with pytest.raises(FinanceError, match="mês inválido"):
        parse_month(bad)
