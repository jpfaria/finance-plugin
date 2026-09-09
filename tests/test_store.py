from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.model.errors import FinanceError


def _e(id_: str, d: date, amount: str = "-10.00") -> Entry:
    return Entry(id=id_, date=d, account="nu", amount=Decimal(amount), description="x")


def test_append_splits_by_month_and_load_all_is_ordered(data_root: Path) -> None:
    store = LedgerStore(data_root)
    store.append([_e("B", date(2026, 10, 1)), _e("A", date(2026, 9, 15))])
    store.append([_e("C", date(2026, 9, 2))])
    assert (data_root / "ledger" / "2026-09.csv").exists()
    assert (data_root / "ledger" / "2026-10.csv").exists()
    assert [e.id for e in store.load_month(2026, 9)] == ["C", "A"]
    assert [e.id for e in store.load_all()] == ["C", "A", "B"]


def test_append_rejects_duplicate_id(data_root: Path) -> None:
    store = LedgerStore(data_root)
    store.append([_e("A", date(2026, 9, 1))])
    with pytest.raises(FinanceError, match="id duplicado"):
        store.append([_e("A", date(2026, 9, 3))])


def test_replace_updates_and_removes(data_root: Path) -> None:
    store = LedgerStore(data_root)
    store.append([_e("A", date(2026, 9, 1)), _e("B", date(2026, 9, 2)), _e("C", date(2026, 10, 1))])
    updated = Entry(
        id="A",
        date=date(2026, 9, 1),
        account="nu",
        amount=Decimal("-10.00"),
        description="x",
        category="casa/luz",
    )
    store.replace([updated], removed_ids={"B"})
    assert [(e.id, e.category) for e in store.load_month(2026, 9)] == [("A", "casa/luz")]
    assert [e.id for e in store.load_month(2026, 10)] == ["C"]


def test_replace_unknown_id_fails(data_root: Path) -> None:
    store = LedgerStore(data_root)
    with pytest.raises(FinanceError, match="não encontrado"):
        store.replace([_e("Z", date(2026, 9, 1))], removed_ids=set())
