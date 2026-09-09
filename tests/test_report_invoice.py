from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.cache.connection import open_db
from finance.config.accounts import load_accounts
from finance.config.budget import Budget
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.model.errors import FinanceError
from finance.reports.invoice import invoice


def _e(id_: str, d: date, amount: str, transfer: str = "") -> Entry:
    return Entry(
        id=id_,
        date=d,
        account="nu-card",
        amount=Decimal(amount),
        description=id_,
        transfer_group=transfer,
    )


def test_invoice_totals_and_window(data_root: Path, cache_root: Path) -> None:
    LedgerStore(data_root).append(
        [
            _e("before", date(2026, 8, 3), "-999.00"),  # fatura 2026-08
            _e("a", date(2026, 8, 4), "-100.00"),
            _e("b", date(2026, 9, 3), "-20.50"),
            _e("pay", date(2026, 8, 15), "60.00", "T1"),
            _e("after", date(2026, 9, 4), "-1.00"),  # fatura 2026-10
        ]
    )
    accounts = load_accounts(data_root / "accounts.yaml")
    conn = open_db(data_root, cache_root, accounts, Budget())
    inv = invoice(conn, accounts["nu-card"], 2026, 9)
    assert (inv.start, inv.end, inv.due) == (date(2026, 8, 4), date(2026, 9, 3), date(2026, 9, 10))
    assert [line.id for line in inv.lines] == ["a", "pay", "b"]
    assert inv.purchases == Decimal("120.50")
    assert inv.payments == Decimal("60.00")
    assert inv.total_due == Decimal("60.50")


def test_invoice_rejects_checking(data_root: Path, cache_root: Path) -> None:
    accounts = load_accounts(data_root / "accounts.yaml")
    conn = open_db(data_root, cache_root, accounts, Budget())
    with pytest.raises(FinanceError, match="não é cartão"):
        invoice(conn, accounts["nu"], 2026, 9)
