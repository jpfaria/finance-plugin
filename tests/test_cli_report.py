import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    runner = CliRunner()
    seeds = [
        ["nu", "3000", "salario", "2026-09-01", "renda/salario", "1"],
        ["nu", "-40", "uber", "2026-09-02", "transporte/uber", "1"],
        ["nu-card", "-300", "tv", "2026-08-20", "casa/luz", "3"],
    ]
    for account, amount, desc, when, category, installments in seeds:
        args = ["add", "--account", account, "--amount", amount, "--desc", desc, "--date", when]
        args += ["--category", category, "--installments", installments]
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
    return data_root


def test_report_month_json(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "month", "--month", "2026-09", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["income"] == "3000.00"
    assert data["expenses"] == "140.00"
    cats = {line["category"]: line for line in data["lines"]}
    assert cats["transporte/uber"]["pct"] == "13.3"


def test_report_budget_table(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "budget", "--month", "2026-09"])
    assert result.exit_code == 0, result.output
    assert "transporte/uber" in result.output
    assert "300.00" in result.output


def test_report_balance_json(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "balance", "--json"])
    assert result.exit_code == 0, result.output
    data = {row["account_id"]: row for row in json.loads(result.output)}
    assert data["nu"]["balance"] == "2960.00"
    assert data["nu-card"]["balance"] == "-300.00"


def test_report_invoice_json(env: Path) -> None:
    result = CliRunner().invoke(
        app, ["report", "invoice", "--account", "nu-card", "--month", "2026-09", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["total_due"] == "100.00"
    assert data["lines"][0]["installment"] == "1/3"


def test_report_invoice_on_checking_fails(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "invoice", "--account", "nu"])
    assert result.exit_code == 1
    assert "não é cartão" in result.output
