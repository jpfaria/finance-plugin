import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app
from finance.config.rules import load_rules
from finance.ledger.store import LedgerStore
from finance.model.entry import Status

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    return data_root


def _run(*args: str) -> str:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def test_import_reconcile_categorize_flow(env: Path) -> None:
    _run(
        "add",
        "--account",
        "nu",
        "--amount",
        "-35.90",
        "--desc",
        "uber",
        "--date",
        "2026-09-01",
        "--category",
        "transporte/uber",
    )
    out = _run("import", str(FIXTURES / "sample.ofx"), "--account", "nu")
    assert "importados: 2, duplicados: 0, sem categoria: 2" in out
    out = _run("import", str(FIXTURES / "sample.ofx"), "--account", "nu")
    assert "importados: 0, duplicados: 2" in out

    out = _run("reconcile", "--json")
    data = json.loads(out)
    assert data["matched"] == 1
    assert [e["description"] for e in data["unmatched_imported"]] == ["PIX RECEBIDO"]
    entries = LedgerStore(env).load_month(2026, 9)
    assert len(entries) == 2
    uber = next(e for e in entries if e.description == "uber")
    assert uber.status is Status.CONFIRMED
    assert uber.import_hash != ""
    assert uber.category == "transporte/uber"

    out = _run("categorize", "--json")
    [pending] = json.loads(out)
    assert pending["description"] == "PIX RECEBIDO"

    _run("categorize", "set", pending["id"], "renda/salario", "--rule", "PIX RECEBIDO")
    rules = load_rules(env / "rules.yaml", frozenset({"renda/salario"}))
    assert [(r.pattern, r.category) for r in rules] == [("PIX RECEBIDO", "renda/salario")]
    assert json.loads(_run("categorize", "--json")) == []

    month = json.loads(_run("report", "month", "--month", "2026-09", "--json"))
    assert month["uncategorized"] == 0
    assert month["pending_manual"] == 0
    assert month["income"] == "1200.00"


def test_import_unknown_format_fails_cleanly(env: Path, tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.write_text("nada\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["import", str(bad), "--account", "nu"])
    assert result.exit_code == 1
    assert "formato não reconhecido" in result.output


def test_reconcile_reports_stale_manual(env: Path) -> None:
    _run("add", "--account", "nu", "--amount", "-1", "--desc", "velho", "--date", "2020-01-01")
    data = json.loads(_run("reconcile", "--json"))
    assert [e["description"] for e in data["stale_manual"]] == ["velho"]
