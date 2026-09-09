from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app
from finance.ledger.store import LedgerStore


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    return data_root


def test_add_single(env: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "add",
            "--account",
            "nu",
            "--amount",
            "-50",
            "--desc",
            "uber",
            "--date",
            "2026-09-05",
            "--category",
            "transporte/uber",
            "--tags",
            "viagem,trabalho",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1 lançamento(s) gravado(s)" in result.output
    [e] = LedgerStore(env).load_month(2026, 9)
    assert e.description == "uber"
    assert e.tags == ("viagem", "trabalho")


def test_add_installments_by_account_name(env: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "add",
            "--account",
            "nubank cart",
            "--amount",
            "-1000",
            "--desc",
            "celular",
            "--date",
            "2026-09-05",
            "--installments",
            "10",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "10 lançamento(s) gravado(s)" in result.output
    assert len(LedgerStore(env).load_all()) == 10
    assert LedgerStore(env).load_month(2027, 6)[0].installment == "10/10"


def test_add_unknown_account_fails_cleanly(env: Path) -> None:
    result = CliRunner().invoke(app, ["add", "--account", "zzz", "--amount", "-1", "--desc", "x"])
    assert result.exit_code == 1
    assert "conta desconhecida" in result.output


def test_add_ambiguous_account_fails(env: Path) -> None:
    result = CliRunner().invoke(
        app, ["add", "--account", "nubank", "--amount", "-1", "--desc", "x"]
    )
    assert result.exit_code == 1
    assert "ambígua" in result.output


def test_default_dirs_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from finance.cli.context import resolve_dirs

    monkeypatch.delenv("FINANCE_DATA_DIR", raising=False)
    monkeypatch.delenv("FINANCE_CACHE_DIR", raising=False)
    assert resolve_dirs() == (Path("data"), Path(".cache"))
