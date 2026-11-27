"""`finance report cash`: saldo do banco, não só a soma do que foi importado."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app

ACCOUNTS = """
accounts:
  - id: bra
    name: Bradesco conta
    bank: bradesco
    type: checking
    opening_balance: 1000.00
    opening_date: 2026-10-01
  - id: nu
    name: Nubank conta
    bank: nubank
    type: checking
"""


def _run(*args: str, code: int = 0) -> str:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == code, result.output
    return result.output


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    (data_root / "accounts.yaml").write_text(ACCOUNTS, encoding="utf-8")
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    _run("add", "--account", "bra", "--amount", "5000", "--desc", "salario", "--date", "2026-10-05")
    _run("add", "--account", "bra", "--amount", "-800", "--desc", "fatura", "--date", "2026-10-09")
    _run("add", "--account", "bra", "--amount", "-200", "--desc", "luz", "--date", "2026-11-03")
    return data_root


def test_cash_shows_opening_and_closing_balance(env: Path) -> None:
    data = json.loads(_run("report", "cash", "--month", "2026-10", "--json"))
    bra = next(line for line in data["lines"] if line["account_id"] == "bra")
    assert bra["opening"] == "1000.00"
    assert bra["income"] == "5000.00"
    assert bra["outflow"] == "800.00"
    assert bra["closing"] == "5200.00"


def test_the_closing_of_one_month_opens_the_next(env: Path) -> None:
    october = json.loads(_run("report", "cash", "--month", "2026-10", "--json"))
    november = json.loads(_run("report", "cash", "--month", "2026-11", "--json"))
    closed = next(line for line in october["lines"] if line["account_id"] == "bra")["closing"]
    opened = next(line for line in november["lines"] if line["account_id"] == "bra")["opening"]
    assert closed == opened == "5200.00"


def test_an_account_without_opening_balance_is_named_in_the_output(env: Path) -> None:
    out = _run("report", "cash", "--month", "2026-10")
    assert "sem saldo inicial em accounts.yaml: nu" in out


def test_balance_says_whether_the_number_is_the_bank(env: Path) -> None:
    rows = json.loads(_run("report", "balance", "--json"))
    bra = next(row for row in rows if row["account_id"] == "bra")
    nu = next(row for row in rows if row["account_id"] == "nu")
    assert bra["balance"] == "5000.00" and bra["real"] is True
    assert nu["balance"] == "0.00" and nu["real"] is False
