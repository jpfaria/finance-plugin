from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.cache.connection import open_db
from finance.config.accounts import load_accounts
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.reports.balance import account_balances


def _e(id_: str, d: date, account: str, amount: str, transfer: str = "") -> Entry:
    return Entry(
        id=id_,
        date=d,
        account=account,
        amount=Decimal(amount),
        description=id_,
        transfer_group=transfer,
    )


def test_balances_and_open_invoice(data_root: Path, cache_root: Path) -> None:
    LedgerStore(data_root).append(
        [
            _e("sal", date(2026, 9, 1), "nu", "3000.00"),
            _e("mkt", date(2026, 9, 2), "nu", "-200.00"),
            _e("c1", date(2026, 8, 20), "nu-card", "-100.00"),  # fatura 2026-09 (04/08..03/09)
            _e("c2", date(2026, 9, 5), "nu-card", "-50.00"),  # fatura 2026-10
            _e("pay-out", date(2026, 9, 10), "nu", "-100.00", "T1"),
            _e("pay-in", date(2026, 9, 10), "nu-card", "100.00", "T1"),
        ]
    )
    accounts = load_accounts(data_root / "accounts.yaml")
    conn = open_db(data_root, cache_root, accounts, {})
    result = {b.account_id: b for b in account_balances(conn, accounts, today=date(2026, 9, 20))}
    assert result["nu"].balance == Decimal("2700.00")
    assert result["nu"].open_invoice is None
    assert result["nu-card"].balance == Decimal("-50.00")
    assert result["nu-card"].open_invoice_month == "2026-10"
    assert result["nu-card"].open_invoice == Decimal("-50.00")
    assert result["bra"].balance == Decimal("0.00")
