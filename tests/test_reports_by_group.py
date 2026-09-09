"""Reports scoped to an account group: which accounts count, and which caps apply."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cache.connection import open_db
from finance.cli import app
from finance.config.accounts import load_accounts
from finance.config.budget import load_budget
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.reports.balance import account_balances
from finance.reports.month import month_summary

ACCOUNTS_YAML = """
accounts:
  - {id: pf, name: Conta pessoal, bank: nubank, type: checking, group: pessoal}
  - {id: pj, name: Conta PJ, bank: bradesco, type: checking, group: pj}
"""
CATEGORIES_YAML = "transporte: [uber]\nrenda: [freelance]\n"
CATEGORIES = frozenset({"transporte/uber", "renda/freelance"})
BUDGET_YAML = """
geral:
  transporte/uber: 300
grupos:
  pj:
    transporte/uber: 500
"""


@pytest.fixture
def grouped_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    (root / "ledger").mkdir(parents=True)
    (root / "accounts.yaml").write_text(ACCOUNTS_YAML, encoding="utf-8")
    (root / "categories.yaml").write_text(CATEGORIES_YAML, encoding="utf-8")
    (root / "budget.yaml").write_text(BUDGET_YAML, encoding="utf-8")
    (root / "rules.yaml").write_text("rules: []\n", encoding="utf-8")
    LedgerStore(root).append(
        [
            Entry(
                id="p1",
                date=date(2026, 9, 2),
                account="pf",
                amount=Decimal("-40.00"),
                description="uber pessoal",
                category="transporte/uber",
            ),
            Entry(
                id="j1",
                date=date(2026, 9, 3),
                account="pj",
                amount=Decimal("-100.00"),
                description="uber cliente",
                category="transporte/uber",
            ),
            Entry(
                id="j2",
                date=date(2026, 9, 4),
                account="pj",
                amount=Decimal("2000.00"),
                description="nota fiscal",
                category="renda/freelance",
            ),
        ]
    )
    return root


def test_month_summary_counts_only_the_group_accounts(grouped_root: Path, cache_root: Path) -> None:
    accounts = load_accounts(grouped_root / "accounts.yaml")
    budget = load_budget(
        grouped_root / "budget.yaml", frozenset({"transporte/uber", "renda/freelance"})
    )
    conn = open_db(grouped_root, cache_root, accounts, budget)

    everything = month_summary(conn, 2026, 9, budget.limits(None), accounts=None)
    assert everything.expenses == Decimal("140.00")
    assert everything.income == Decimal("2000.00")

    pj = month_summary(conn, 2026, 9, budget.limits("pj"), accounts={"pj"})
    assert pj.expenses == Decimal("100.00")
    assert pj.income == Decimal("2000.00")
    uber = next(line for line in pj.lines if line.category == "transporte/uber")
    assert uber.budget == Decimal("500.00")
    assert uber.pct == "20.0"

    pessoal = month_summary(conn, 2026, 9, budget.limits("pessoal"), accounts={"pf"})
    assert pessoal.expenses == Decimal("40.00")
    assert pessoal.income == Decimal("0.00")
    uber_pf = next(line for line in pessoal.lines if line.category == "transporte/uber")
    assert uber_pf.budget == Decimal("300.00")


def test_balance_lists_only_the_group_accounts(grouped_root: Path, cache_root: Path) -> None:
    accounts = load_accounts(grouped_root / "accounts.yaml")
    budget = load_budget(
        grouped_root / "budget.yaml", frozenset({"transporte/uber", "renda/freelance"})
    )
    conn = open_db(grouped_root, cache_root, accounts, budget)
    from finance.config.accounts import accounts_in_group

    rows = account_balances(conn, accounts_in_group(accounts, "pj"), today=date(2026, 9, 30))
    assert [(r.account_id, r.balance) for r in rows] == [("pj", Decimal("1900.00"))]


def test_cli_group_flag(
    monkeypatch: pytest.MonkeyPatch, grouped_root: Path, cache_root: Path
) -> None:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(grouped_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    runner = CliRunner()

    result = runner.invoke(
        app, ["report", "month", "--month", "2026-09", "--group", "pj", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["expenses"] == "100.00"
    assert data["group"] == "pj"

    result = runner.invoke(app, ["report", "balance", "--group", "pessoal", "--json"])
    assert result.exit_code == 0, result.output
    assert [r["account_id"] for r in json.loads(result.output)] == ["pf"]

    result = runner.invoke(app, ["report", "month", "--month", "2026-09", "--json"])
    assert json.loads(result.output)["expenses"] == "140.00"

    result = runner.invoke(app, ["report", "balance", "--group", "inexistente"])
    assert result.exit_code == 1
    assert "grupo desconhecido" in result.output
