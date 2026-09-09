from pathlib import Path

import pytest

from finance.imports.registry import detect
from finance.model.errors import FinanceError

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("name", "parser"),
    [
        ("sample.ofx", "ofx"),
        ("nubank_checking.csv", "nubank-checking-csv"),
        ("nubank_card.csv", "nubank-card-csv"),
    ],
)
def test_detects_fixture(name: str, parser: str) -> None:
    assert detect(FIXTURES / name).name == parser


def test_unknown_format_is_a_clear_error(tmp_path: Path) -> None:
    p = tmp_path / "extrato.txt"
    p.write_text("qualquer coisa\n", encoding="utf-8")
    with pytest.raises(FinanceError, match="formato não reconhecido"):
        detect(p)
