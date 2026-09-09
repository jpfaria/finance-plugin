"""Load budget.yaml: monthly cap per category path."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from finance.model.errors import FinanceError
from finance.model.money import parse_amount


def load_budget(path: Path, categories: frozenset[str]) -> dict[str, Decimal]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise FinanceError(f"{path}: esperado um mapa categoria -> valor")
    budget: dict[str, Decimal] = {}
    for category, value in raw.items():
        if category not in categories:
            raise FinanceError(f"{path}: categoria desconhecida: {category!r}")
        budget[str(category)] = parse_amount(str(value))
    return budget
