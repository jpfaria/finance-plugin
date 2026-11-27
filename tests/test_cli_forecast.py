"""`finance report forecast`: quanto cada categoria deve custar no mês que vem."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app


def _run(*args: str, code: int = 0) -> str:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == code, result.output
    return result.output


def _add(amount: str, desc: str, when: str, category: str = "") -> None:
    args = ["add", "--account", "nu", "--amount", amount, "--desc", desc, "--date", when]
    if category:
        args += ["--category", category]
    _run(*args)


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    _add("3000", "salario", "2026-10-05", "renda/salario")
    _add("3000", "salario", "2026-11-05", "renda/salario")
    _add("-400", "luz", "2026-10-10", "casa/luz")
    _add("-600", "luz", "2026-11-10", "casa/luz")
    _add("-900", "uber", "2026-11-12", "transporte/uber")
    return data_root


def test_forecast_over_a_range_of_months(env: Path) -> None:
    out = _run("report", "forecast", "--month", "2026-12", "--from", "2026-10", "--to", "2026-11")
    data = json.loads(
        _run(
            "report",
            "forecast",
            "--month",
            "2026-12",
            "--from",
            "2026-10",
            "--to",
            "2026-11",
            "--json",
        )
    )
    assert "Previsão 2026-12" in out
    assert data["base"] == ["2026-10", "2026-11"]
    assert data["income"] == "3000.00"
    lines = {line["category"]: line for line in data["lines"]}
    assert lines["casa/luz"]["average"] == "500.00"
    assert lines["casa/luz"]["every_month"] is True
    assert lines["transporte/uber"]["average"] == "450.00"
    assert lines["transporte/uber"]["every_month"] is False
    assert data["expenses"] == "950.00"
    assert data["net"] == "2050.00"


def test_the_base_defaults_to_the_months_before_the_target(env: Path) -> None:
    data = json.loads(_run("report", "forecast", "--month", "2026-12", "--base", "2", "--json"))
    assert data["base"] == ["2026-10", "2026-11"]


def test_from_without_to_is_an_error(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "forecast", "--from", "2026-10"])
    assert result.exit_code == 1
    assert "use --from e --to juntos" in result.output


def test_pdf_writes_html_and_asks_the_browser_to_print(
    env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "previsao.pdf"
    script = tmp_path / "browser.sh"
    script.write_text(f'#!/bin/sh\necho pdf > "{out}"\n', encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("FINANCE_BROWSER", str(script))
    output = _run(
        "report",
        "pdf",
        "--month",
        "2026-12",
        "--from",
        "2026-10",
        "--to",
        "2026-11",
        "--out",
        str(out),
    )
    assert str(out) in output
    assert out.exists()
    html = (tmp_path / "previsao.html").read_text(encoding="utf-8")
    assert "Previsão de dezembro de 2026" in html
    assert "casa/luz" in html
