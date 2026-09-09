from pathlib import Path

import pytest

ACCOUNTS_YAML = """
accounts:
  - id: nu
    name: Nubank conta
    bank: nubank
    type: checking
  - id: nu-card
    name: Nubank cartão
    bank: nubank
    type: credit
    closing_day: 3
    due_day: 10
  - id: bra
    name: Bradesco conta
    bank: bradesco
    type: checking
"""

CATEGORIES_YAML = """
casa: [aluguel, condominio, luz]
transporte: [uber, combustivel]
renda: [salario]
"""

BUDGET_YAML = """
transporte/uber: 300
casa/luz: 250
"""


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    (root / "ledger").mkdir(parents=True)
    (root / "accounts.yaml").write_text(ACCOUNTS_YAML, encoding="utf-8")
    (root / "categories.yaml").write_text(CATEGORIES_YAML, encoding="utf-8")
    (root / "budget.yaml").write_text(BUDGET_YAML, encoding="utf-8")
    (root / "rules.yaml").write_text("rules: []\n", encoding="utf-8")
    return root


@pytest.fixture
def cache_root(tmp_path: Path) -> Path:
    root = tmp_path / "cache"
    root.mkdir()
    return root
