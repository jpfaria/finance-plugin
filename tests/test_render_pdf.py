"""A ponte HTML -> PDF: quem imprime é o navegador da máquina, e falha tem que ser clara."""

from pathlib import Path

import pytest

from finance.model.errors import FinanceError
from finance.render.pdf import BROWSER_ENV, find_browser, html_to_pdf


def _stub(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "browser.sh"
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def test_a_browser_pointed_by_the_env_var_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = _stub(tmp_path, "exit 0")
    monkeypatch.setenv(BROWSER_ENV, str(script))
    assert find_browser() == script


def test_a_browser_that_does_not_exist_is_a_clear_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(BROWSER_ENV, str(tmp_path / "nao-existe"))
    with pytest.raises(FinanceError, match="não existe"):
        find_browser()


def test_printing_writes_the_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf = tmp_path / "saida" / "previsao.pdf"
    monkeypatch.setenv(BROWSER_ENV, str(_stub(tmp_path, f'echo pdf > "{pdf}"')))
    html = tmp_path / "previsao.html"
    html.write_text("<p>oi</p>", encoding="utf-8")
    html_to_pdf(html, pdf)
    assert pdf.read_text(encoding="utf-8").strip() == "pdf"


def test_a_browser_that_prints_nothing_is_an_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(BROWSER_ENV, str(_stub(tmp_path, "echo 'deu ruim' >&2; exit 3")))
    html = tmp_path / "previsao.html"
    html.write_text("<p>oi</p>", encoding="utf-8")
    with pytest.raises(FinanceError, match="deu ruim"):
        html_to_pdf(html, tmp_path / "previsao.pdf")
