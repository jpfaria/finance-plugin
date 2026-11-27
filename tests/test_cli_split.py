"""`finance split`: a cobrança única aparece nas duas categorias e não duplica na reimportação."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    return data_root


def _run(*args: str, code: int = 0) -> str:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == code, result.output
    return result.output


def _add(amount: str, desc: str) -> str:
    out = _run(
        "add", "--account", "bra", "--amount", amount, "--desc", desc, "--date", "2026-11-24"
    )
    return out.split(":")[1].strip()


def test_the_two_parts_show_up_in_their_own_categories(env: Path) -> None:
    entry_id = _add("-868.00", "STARLINK")
    _run("split", entry_id, "--part", "576:casa/luz", "--part", "292:casa/aluguel")
    report = json.loads(_run("report", "month", "--month", "2026-11", "--json"))
    spent = {row["category"]: row["spent"] for row in report["lines"]}
    assert spent["casa/luz"] == "576.00"
    assert spent["casa/aluguel"] == "292.00"
    assert report["expenses"] == "868.00"


def test_the_split_entry_is_not_imported_again(env: Path) -> None:
    out = _run("import", str(FIXTURES / "sample.ofx"), "--account", "nu")
    assert "importados: 2" in out
    pending = json.loads(_run("categorize", "--json"))
    entry = pending[0]
    half = abs(Decimal(str(entry["amount"]))) / 2
    _run("split", entry["id"], "--part", f"{half}:casa/luz", "--part", f"{half}:casa/aluguel")
    out = _run("import", str(FIXTURES / "sample.ofx"), "--account", "nu")
    assert "importados: 0, duplicados: 2" in out


def test_a_part_without_a_category_is_a_clear_error(env: Path) -> None:
    entry_id = _add("-868.00", "STARLINK")
    out = _run("split", entry_id, "--part", "576", "--part", "292:casa/aluguel", code=1)
    assert "parte sem categoria" in out
