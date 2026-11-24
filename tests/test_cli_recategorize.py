"""`finance recategorize`: reapply rules.yaml over what is already in data/ledger/."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app
from finance.ledger.store import LedgerStore
from finance.model.entry import CategorySource

RULES_YAML = """
rules:
  - {pattern: uber, category: transporte/uber}
  - {pattern: enel, category: casa/luz}
"""

GROUPED_ACCOUNTS_YAML = """
accounts:
  - {id: pf, name: Conta pessoal, bank: nubank, type: checking, group: pessoal}
  - {id: pj, name: Conta PJ, bank: bradesco, type: checking, group: pj}
"""


def _run(*args: str, code: int = 0) -> str:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == code, result.output
    return result.output


def _add(account: str, amount: str, desc: str, when: str, category: str = "") -> None:
    args = ["add", "--account", account, "--amount", amount, "--desc", desc, "--date", when]
    if category:
        args += ["--category", category]
    _run(*args)


def _by_description(data_root: Path) -> dict[str, tuple[str, CategorySource]]:
    return {
        e.description: (e.category, e.category_source) for e in LedgerStore(data_root).load_all()
    }


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    _add("nu", "-40", "UBER TRIP 123", "2026-09-02")
    _add("nu", "-9", "PADARIA SAO JOSE", "2026-09-03")
    _add("nu", "-250", "ENEL SP", "2026-09-04")
    _add("nu", "-900", "CONDOMINIO", "2026-09-05", category="casa/condominio")
    (data_root / "rules.yaml").write_text(RULES_YAML, encoding="utf-8")
    return data_root


def test_dry_run_reports_without_writing(env: Path) -> None:
    out = _run("recategorize", "--dry-run")
    assert "UBER TRIP 123" in out
    assert "transporte/uber" in out
    assert "dry-run: 2 recategorizado(s), 1 sem categoria" in out
    assert _by_description(env)["UBER TRIP 123"] == ("", CategorySource.NONE)


def test_recategorize_applies_rules_to_entries_already_stored(env: Path) -> None:
    out = _run("recategorize")
    assert "2 recategorizado(s), 1 sem categoria" in out
    stored = _by_description(env)
    assert stored["UBER TRIP 123"] == ("transporte/uber", CategorySource.RULE)
    assert stored["ENEL SP"] == ("casa/luz", CategorySource.RULE)
    assert stored["PADARIA SAO JOSE"] == ("", CategorySource.NONE)
    assert stored["CONDOMINIO"] == ("casa/condominio", CategorySource.MANUAL)
    assert "0 recategorizado(s), 1 sem categoria" in _run("recategorize")


def test_force_never_overwrites_a_manual_category(env: Path) -> None:
    rows = json.loads(_run("categorize", "--json"))
    enel = next(row for row in rows if row["description"] == "ENEL SP")
    _run("categorize", "set", enel["id"], "casa/aluguel")
    _run("recategorize", "--force")
    stored = _by_description(env)
    assert stored["ENEL SP"] == ("casa/aluguel", CategorySource.MANUAL)
    assert stored["CONDOMINIO"] == ("casa/condominio", CategorySource.MANUAL)


def test_force_reevaluates_a_rule_category(env: Path) -> None:
    _run("recategorize")
    (env / "rules.yaml").write_text(
        "rules:\n  - {pattern: uber, category: transporte/combustivel}\n", encoding="utf-8"
    )
    out = _run("recategorize", "--force")
    assert "1 recategorizado(s)" in out
    assert _by_description(env)["UBER TRIP 123"] == (
        "transporte/combustivel",
        CategorySource.RULE,
    )


def test_force_keeps_a_category_whose_rule_is_gone(env: Path) -> None:
    _run("recategorize")
    (env / "rules.yaml").write_text("rules: []\n", encoding="utf-8")
    assert "0 recategorizado(s)" in _run("recategorize", "--force")
    assert _by_description(env)["UBER TRIP 123"] == ("transporte/uber", CategorySource.RULE)


def test_month_filter(env: Path) -> None:
    _add("nu", "-55", "UBER TRIP 999", "2026-10-02")
    out = _run("recategorize", "--month", "2026-10")
    assert "1 recategorizado(s), 0 sem categoria" in out
    stored = _by_description(env)
    assert stored["UBER TRIP 999"] == ("transporte/uber", CategorySource.RULE)
    assert stored["UBER TRIP 123"] == ("", CategorySource.NONE)


def test_group_filter_and_unknown_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cache_root: Path
) -> None:
    root = tmp_path / "grouped"
    (root / "ledger").mkdir(parents=True)
    (root / "accounts.yaml").write_text(GROUPED_ACCOUNTS_YAML, encoding="utf-8")
    (root / "categories.yaml").write_text("transporte: [uber]\n", encoding="utf-8")
    (root / "budget.yaml").write_text("geral: {}\n", encoding="utf-8")
    (root / "rules.yaml").write_text(
        "rules:\n  - {pattern: uber, category: transporte/uber}\n", encoding="utf-8"
    )
    monkeypatch.setenv("FINANCE_DATA_DIR", str(root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    _add("pf", "-40", "UBER pessoal", "2026-09-02")
    _add("pj", "-80", "UBER cliente", "2026-09-03")

    assert "1 recategorizado(s), 0 sem categoria" in _run("recategorize", "--group", "pj")
    stored = _by_description(root)
    assert stored["UBER cliente"] == ("transporte/uber", CategorySource.RULE)
    assert stored["UBER pessoal"] == ("", CategorySource.NONE)

    out = _run("recategorize", "--group", "inexistente", code=1)
    assert "grupo desconhecido" in out


def test_invalid_month_is_an_error(env: Path) -> None:
    assert "mês inválido" in _run("recategorize", "--month", "2026-13", code=1)
