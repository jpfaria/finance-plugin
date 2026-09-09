from decimal import Decimal
from pathlib import Path

import pytest

from finance.config.budget import load_budget
from finance.model.errors import FinanceError

CATS = frozenset({"transporte/uber", "casa/luz", "renda/salario"})


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "budget.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_general_only(tmp_path: Path) -> None:
    budget = load_budget(_write(tmp_path, "geral:\n  transporte/uber: 300\n"), CATS)
    assert budget.limits(None) == {"transporte/uber": Decimal("300.00")}
    assert budget.limits("pj") == {"transporte/uber": Decimal("300.00")}


def test_group_overrides_general_and_adds_its_own(tmp_path: Path) -> None:
    text = (
        "geral:\n"
        "  transporte/uber: 300\n"
        "  casa/luz: 250\n"
        "grupos:\n"
        "  pj:\n"
        "    transporte/uber: 500\n"
    )
    budget = load_budget(_write(tmp_path, text), CATS)
    assert budget.limits(None) == {
        "transporte/uber": Decimal("300.00"),
        "casa/luz": Decimal("250.00"),
    }
    assert budget.limits("pj") == {
        "transporte/uber": Decimal("500.00"),
        "casa/luz": Decimal("250.00"),
    }
    assert budget.limits("pessoal") == budget.limits(None)


def test_empty_file_is_an_empty_budget(tmp_path: Path) -> None:
    assert load_budget(_write(tmp_path, "{}\n"), CATS).limits(None) == {}


def test_unknown_category_rejected_in_group_too(tmp_path: Path) -> None:
    text = "grupos:\n  pj:\n    lazer/bar: 100\n"
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        load_budget(_write(tmp_path, text), CATS)


def test_flat_legacy_shape_is_rejected_with_a_clear_message(tmp_path: Path) -> None:
    with pytest.raises(FinanceError, match="geral"):
        load_budget(_write(tmp_path, "transporte/uber: 300\n"), CATS)


def test_budget_is_empty_when_file_missing(tmp_path: Path) -> None:
    assert load_budget(tmp_path / "nope.yaml", CATS).limits(None) == {}
