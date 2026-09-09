from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.cache.connection import open_db
from finance.config.accounts import load_accounts
from finance.config.budget import Budget
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry, Status
from finance.reports.month import month_summary


def _e(
    id_: str,
    d: date,
    amount: str,
    category: str = "",
    transfer: str = "",
    status: Status = Status.CONFIRMED,
) -> Entry:
    return Entry(
        id=id_,
        date=d,
        account="nu",
        amount=Decimal(amount),
        description=id_,
        category=category,
        transfer_group=transfer,
        status=status,
    )


def test_month_summary(data_root: Path, cache_root: Path) -> None:
    LedgerStore(data_root).append(
        [
            _e("sal", date(2026, 9, 1), "3000.00", "renda/salario"),
            _e("u1", date(2026, 9, 2), "-40.00", "transporte/uber"),
            _e("u2", date(2026, 9, 3), "-20.00", "transporte/uber", status=Status.MANUAL),
            _e("luz", date(2026, 9, 4), "-300.00", "casa/luz"),
            _e("??", date(2026, 9, 5), "-15.00"),
            _e("pay", date(2026, 9, 6), "-500.00", transfer="T1"),
            _e("oct", date(2026, 10, 1), "-1.00", "casa/luz"),
        ]
    )
    accounts = load_accounts(data_root / "accounts.yaml")
    budget = {
        "transporte/uber": Decimal("300.00"),
        "casa/luz": Decimal("250.00"),
        "casa/aluguel": Decimal("1500.00"),
    }
    conn = open_db(data_root, cache_root, accounts, Budget(general=budget))
    s = month_summary(conn, 2026, 9, budget)
    assert s.income == Decimal("3000.00")
    assert s.expenses == Decimal("375.00")
    assert s.net == Decimal("2625.00")
    assert s.uncategorized == 1
    assert s.pending_manual == 1
    by_cat = {line.category: line for line in s.lines}
    assert by_cat["casa/luz"].spent == Decimal("300.00")
    assert by_cat["casa/luz"].pct == "120.0"
    assert by_cat["transporte/uber"].spent == Decimal("60.00")
    assert by_cat["transporte/uber"].pct == "20.0"
    assert by_cat["casa/aluguel"].spent == Decimal("0.00")
    assert by_cat["(sem categoria)"].budget is None
    assert by_cat["(sem categoria)"].pct is None
    assert [line.category for line in s.lines][:2] == ["casa/luz", "transporte/uber"]
