from pathlib import Path

import pytest

from finance.config.rules import Rule, append_rule, apply_rules, load_rules
from finance.model.errors import FinanceError

CATS = frozenset({"transporte/uber", "alimentacao/delivery", "renda/salario"})


def test_load_apply_order_and_case(tmp_path: Path) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text(
        "rules:\n"
        "  - {pattern: 'uber', category: transporte/uber}\n"
        "  - {pattern: 'ifood|uber eats', category: alimentacao/delivery}\n",
        encoding="utf-8",
    )
    rules = load_rules(p, CATS)
    assert apply_rules(rules, "UBER EATS pedido") == "transporte/uber"
    assert apply_rules(rules, "IFOOD") == "alimentacao/delivery"
    assert apply_rules(rules, "padaria") == ""


def test_empty_file_means_no_rules(tmp_path: Path) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text("rules: []\n", encoding="utf-8")
    assert load_rules(p, CATS) == []


def test_unknown_category_rejected(tmp_path: Path) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text("rules:\n  - {pattern: x, category: lazer/bar}\n", encoding="utf-8")
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        load_rules(p, CATS)


def test_append_persists(tmp_path: Path) -> None:
    p = tmp_path / "rules.yaml"
    p.write_text("rules: []\n", encoding="utf-8")
    append_rule(p, Rule("pix recebido", "renda/salario"))
    append_rule(p, Rule("uber", "transporte/uber"))
    assert [r.category for r in load_rules(p, CATS)] == ["renda/salario", "transporte/uber"]
