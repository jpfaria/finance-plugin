"""Previsão por categoria: média dos meses fechados, separando o que repete todo mês."""

import sqlite3
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
from finance.reports.forecast import base_before, forecast, months_between


def _e(id_: str, d: date, amount: str, category: str = "", transfer: str = "") -> Entry:
    return Entry(
        id=id_,
        date=d,
        account="nu",
        amount=Decimal(amount),
        description=id_,
        category=category,
        transfer_group=transfer,
    )


def _conn(data_root: Path, cache_root: Path, entries: list[Entry]) -> sqlite3.Connection:
    LedgerStore(data_root).append(entries)
    accounts = load_accounts(data_root / "accounts.yaml")
    return open_db(data_root, cache_root, accounts, Budget(general={}))


def test_average_divides_by_every_month_of_the_base(data_root: Path, cache_root: Path) -> None:
    """Gasto de um mês só entra como fração: é o que se espera dele num mês qualquer."""
    conn = _conn(
        data_root,
        cache_root,
        [
            _e("m1", date(2026, 9, 10), "-300.00", "casa/mercado"),
            _e("m2", date(2026, 10, 10), "-330.00", "casa/mercado"),
            _e("m3", date(2026, 11, 10), "-270.00", "casa/mercado"),
            _e("tv", date(2026, 10, 5), "-90.00", "lazer/streaming"),
        ],
    )
    result = forecast(conn, (2026, 12), ["2026-09", "2026-10", "2026-11"])
    lines = {line.category: line for line in result.lines}
    assert lines["casa/mercado"].average == Decimal("300.00")
    assert lines["casa/mercado"].months_present == 3
    assert lines["casa/mercado"].every_month is True
    assert lines["lazer/streaming"].average == Decimal("30.00")
    assert lines["lazer/streaming"].months_present == 1
    assert lines["lazer/streaming"].every_month is False
    assert result.expenses == Decimal("330.00")
    assert result.target == "2026-12"


def test_income_is_averaged_and_transfers_are_out(data_root: Path, cache_root: Path) -> None:
    conn = _conn(
        data_root,
        cache_root,
        [
            _e("s1", date(2026, 10, 5), "2000.00", "renda/salario"),
            _e("s2", date(2026, 11, 5), "3000.00", "renda/salario"),
            _e("fat", date(2026, 11, 9), "-800.00", transfer="T1"),
            _e("rec", date(2026, 11, 7), "800.00", transfer="T1"),
        ],
    )
    result = forecast(conn, (2026, 12), ["2026-10", "2026-11"])
    assert result.income == Decimal("2500.00")
    assert result.expenses == Decimal("0.00")
    assert result.net == Decimal("2500.00")


def test_per_month_keeps_the_base_order(data_root: Path, cache_root: Path) -> None:
    conn = _conn(
        data_root,
        cache_root,
        [
            _e("a", date(2026, 10, 1), "-10.00", "casa/luz"),
            _e("b", date(2026, 11, 1), "-30.00", "casa/luz"),
        ],
    )
    [line] = forecast(conn, (2026, 12), ["2026-10", "2026-11"]).lines
    assert line.per_month == [Decimal("10.00"), Decimal("30.00")]
    assert line.average == Decimal("20.00")


def test_uncategorized_is_a_line_of_its_own(data_root: Path, cache_root: Path) -> None:
    conn = _conn(data_root, cache_root, [_e("x", date(2026, 11, 2), "-50.00")])
    [line] = forecast(conn, (2026, 12), ["2026-11"]).lines
    assert line.category == "(sem categoria)"
    assert line.average == Decimal("50.00")


def test_only_the_accounts_of_the_group_count(data_root: Path, cache_root: Path) -> None:
    conn = _conn(
        data_root,
        cache_root,
        [
            _e("nu", date(2026, 11, 2), "-50.00", "casa/luz"),
            Entry(
                id="bra",
                date=date(2026, 11, 3),
                account="bra",
                amount=Decimal("-70.00"),
                description="bra",
                category="casa/luz",
            ),
        ],
    )
    result = forecast(conn, (2026, 12), ["2026-11"], accounts={"nu"}, group="pessoal")
    assert [line.average for line in result.lines] == [Decimal("50.00")]
    assert result.group == "pessoal"


def test_base_before_is_the_months_right_before_the_target() -> None:
    assert base_before(2026, 12, 3) == ["2026-09", "2026-10", "2026-11"]
    assert base_before(2027, 1, 2) == ["2026-11", "2026-12"]
    assert base_before(2027, 2, 1) == ["2027-01"]


def test_an_inverted_range_is_an_error() -> None:
    with pytest.raises(FinanceError, match="intervalo invertido"):
        months_between((2026, 11), (2026, 9))


def test_a_base_without_months_is_an_error(data_root: Path, cache_root: Path) -> None:
    conn = _conn(data_root, cache_root, [])
    with pytest.raises(FinanceError, match="pelo menos um mês"):
        forecast(conn, (2026, 12), [])
