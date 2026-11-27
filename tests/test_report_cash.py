"""Caixa: o dinheiro que entrou e saiu da conta, com saldo de verdade."""

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.cache.connection import open_db
from finance.config.accounts import load_accounts
from finance.config.budget import Budget
from finance.ledger.store import LedgerStore
from finance.model.account import Account
from finance.model.entry import Entry
from finance.reports.cash import balance_now, cash_report

ACCOUNTS = """
accounts:
  - id: bra
    name: Bradesco conta
    bank: bradesco
    type: checking
    opening_balance: -3675.37
    opening_date: 2026-09-28
  - id: nu
    name: Nubank conta
    bank: nubank
    type: checking
  - id: nu-card
    name: Nubank cartão
    bank: nubank
    type: credit
    closing_day: 3
    due_day: 10
"""


def _e(id_: str, account: str, d: date, amount: str, transfer: str = "") -> Entry:
    return Entry(
        id=id_,
        date=d,
        account=account,
        amount=Decimal(amount),
        description=id_,
        transfer_group=transfer,
    )


def _setup(
    data_root: Path, cache_root: Path, entries: list[Entry]
) -> tuple[sqlite3.Connection, dict[str, Account]]:
    (data_root / "accounts.yaml").write_text(ACCOUNTS, encoding="utf-8")
    LedgerStore(data_root).append(entries)
    accounts = load_accounts(data_root / "accounts.yaml")
    return open_db(data_root, cache_root, accounts, Budget(general={})), accounts


def test_the_opening_balance_is_the_statement_before_the_first_entry(
    data_root: Path, cache_root: Path
) -> None:
    conn, accounts = _setup(
        data_root,
        cache_root,
        [
            _e("a", "bra", date(2026, 9, 28), "-187.61"),
            _e("b", "bra", date(2026, 10, 2), "1000.00"),
        ],
    )
    report = cash_report(conn, accounts, 2026, 10, None)
    line = next(ln for ln in report.lines if ln.account_id == "bra")
    assert line.opening == Decimal("-3862.98")  # -3675.37 - 187.61
    assert line.income == Decimal("1000.00")
    assert line.outflow == Decimal("0.00")
    assert line.closing == Decimal("-2862.98")


def test_a_transfer_leg_counts_as_cash_leaving_the_account(
    data_root: Path, cache_root: Path
) -> None:
    """Pagar a fatura não é despesa do mês, mas é dinheiro saindo da conta."""
    conn, accounts = _setup(
        data_root,
        cache_root,
        [
            _e("sal", "bra", date(2026, 10, 5), "5000.00"),
            _e("fat", "bra", date(2026, 10, 9), "-2000.00", transfer="T1"),
            _e("rec", "nu-card", date(2026, 10, 9), "2000.00", transfer="T1"),
        ],
    )
    report = cash_report(conn, accounts, 2026, 10, None)
    line = next(ln for ln in report.lines if ln.account_id == "bra")
    assert line.outflow == Decimal("2000.00")
    assert line.movement == Decimal("3000.00")
    assert line.closing == Decimal("-675.37")


def test_a_card_is_not_a_cash_account(data_root: Path, cache_root: Path) -> None:
    """Cartão não tem caixa: o que sai do bolso é o pagamento da fatura, na conta."""
    conn, accounts = _setup(data_root, cache_root, [])
    report = cash_report(conn, accounts, 2026, 10, None)
    assert [line.account_id for line in report.lines] == ["bra", "nu"]


def test_an_account_without_opening_balance_has_no_balance(
    data_root: Path, cache_root: Path
) -> None:
    conn, accounts = _setup(data_root, cache_root, [_e("x", "nu", date(2026, 10, 3), "-10.00")])
    report = cash_report(conn, accounts, 2026, 10, None)
    nu = next(ln for ln in report.lines if ln.account_id == "nu")
    assert nu.opening is None and nu.closing is None
    assert nu.outflow == Decimal("10.00")
    assert report.accounts_without_opening == ["nu"]
    assert report.opening is None and report.closing is None
    assert report.outflow == Decimal("10.00")


def test_balance_now_adds_every_entry_to_the_opening(data_root: Path, cache_root: Path) -> None:
    conn, accounts = _setup(
        data_root,
        cache_root,
        [
            _e("a", "bra", date(2026, 9, 28), "-187.61"),
            _e("b", "bra", date(2026, 11, 24), "-1671.85"),
        ],
    )
    assert balance_now(conn, accounts["bra"]) == Decimal("-5534.83")
    assert balance_now(conn, accounts["nu"]) is None


def test_only_the_accounts_of_the_group_are_in_the_report(
    data_root: Path, cache_root: Path
) -> None:
    conn, accounts = _setup(data_root, cache_root, [])
    selected = {"bra": accounts["bra"]}
    report = cash_report(conn, selected, 2026, 10, "pessoal")
    assert [line.account_id for line in report.lines] == ["bra"]
    assert report.group == "pessoal"
