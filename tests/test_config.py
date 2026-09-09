from decimal import Decimal
from pathlib import Path

import pytest

from finance.config.accounts import load_accounts
from finance.config.budget import load_budget
from finance.config.categories import load_categories
from finance.model.account import AccountType
from finance.model.errors import FinanceError


def test_load_accounts(data_root: Path) -> None:
    accounts = load_accounts(data_root / "accounts.yaml")
    assert set(accounts) == {"nu", "nu-card", "bra"}
    assert accounts["nu-card"].type is AccountType.CREDIT
    assert accounts["nu-card"].closing_day == 3
    assert accounts["nu"].closing_day is None


def test_load_accounts_credit_requires_days(tmp_path: Path) -> None:
    p = tmp_path / "a.yaml"
    p.write_text("accounts:\n  - {id: c, name: C, bank: nubank, type: credit}\n", encoding="utf-8")
    with pytest.raises(FinanceError, match="closing_day"):
        load_accounts(p)


def test_load_accounts_rejects_duplicate_id(tmp_path: Path) -> None:
    p = tmp_path / "a.yaml"
    p.write_text(
        "accounts:\n"
        "  - {id: x, name: A, bank: nubank, type: checking}\n"
        "  - {id: x, name: B, bank: nubank, type: checking}\n",
        encoding="utf-8",
    )
    with pytest.raises(FinanceError, match="duplicad"):
        load_accounts(p)


def test_load_categories(data_root: Path) -> None:
    cats = load_categories(data_root / "categories.yaml")
    assert "casa/aluguel" in cats
    assert "renda/salario" in cats
    assert "casa" not in cats


def test_load_budget(data_root: Path) -> None:
    cats = load_categories(data_root / "categories.yaml")
    budget = load_budget(data_root / "budget.yaml", cats)
    assert budget == {"transporte/uber": Decimal("300.00"), "casa/luz": Decimal("250.00")}


def test_load_budget_rejects_unknown_category(tmp_path: Path) -> None:
    p = tmp_path / "b.yaml"
    p.write_text("lazer/cinema: 100\n", encoding="utf-8")
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        load_budget(p, frozenset({"casa/luz"}))
