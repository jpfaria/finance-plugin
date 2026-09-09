from datetime import date
from decimal import Decimal

import pytest

from finance.actions.categorize import pending, set_category
from finance.model.entry import Entry
from finance.model.errors import FinanceError

CATS = frozenset({"casa/luz"})


def _e(id_: str, d: date, category: str = "", transfer: str = "") -> Entry:
    return Entry(
        id=id_,
        date=d,
        account="nu",
        amount=Decimal("-1.00"),
        description=id_,
        category=category,
        transfer_group=transfer,
    )


def test_pending_filters_month_and_transfers() -> None:
    entries = [
        _e("a", date(2026, 9, 1)),
        _e("b", date(2026, 9, 2), category="casa/luz"),
        _e("c", date(2026, 9, 3), transfer="T"),
        _e("d", date(2026, 10, 1)),
    ]
    assert [e.id for e in pending(entries, 2026, 9)] == ["a"]
    assert [e.id for e in pending(entries, None, None)] == ["a", "d"]


def test_set_category() -> None:
    entries = [_e("a", date(2026, 9, 1))]
    assert set_category(entries, "a", "casa/luz", CATS).category == "casa/luz"
    with pytest.raises(FinanceError, match="não encontrado"):
        set_category(entries, "zz", "casa/luz", CATS)
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        set_category(entries, "a", "lazer/bar", CATS)
