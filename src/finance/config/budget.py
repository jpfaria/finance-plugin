"""budget.yaml: monthly cap per category, general and per account group."""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from finance.model.errors import FinanceError
from finance.model.money import parse_amount

GENERAL_KEY = "geral"
GROUPS_KEY = "grupos"


@dataclass(frozen=True)
class Budget:
    """Caps by category: the general set, overridden per group where declared."""

    general: dict[str, Decimal] = field(default_factory=dict)
    by_group: dict[str, dict[str, Decimal]] = field(default_factory=dict)

    def limits(self, group: str | None) -> dict[str, Decimal]:
        if group is None:
            return dict(self.general)
        return {**self.general, **self.by_group.get(group, {})}


def load_budget(path: Path, categories: frozenset[str]) -> Budget:
    if not path.is_file():
        return Budget()
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise FinanceError(f"{path}: esperado um mapa com '{GENERAL_KEY}' e/ou '{GROUPS_KEY}'")
    unknown = set(raw) - {GENERAL_KEY, GROUPS_KEY}
    if unknown:
        raise FinanceError(
            f"{path}: chaves inesperadas: {', '.join(sorted(unknown))}. "
            f"Os limites vão sob '{GENERAL_KEY}:' e, por grupo, sob '{GROUPS_KEY}:'."
        )
    groups_raw = raw.get(GROUPS_KEY) or {}
    if not isinstance(groups_raw, dict):
        raise FinanceError(f"{path}: '{GROUPS_KEY}' precisa ser um mapa grupo -> limites")
    return Budget(
        general=_caps(raw.get(GENERAL_KEY), path, categories, GENERAL_KEY),
        by_group={
            str(name): _caps(caps, path, categories, f"{GROUPS_KEY}/{name}")
            for name, caps in groups_raw.items()
        },
    )


def _caps(raw: Any, path: Path, categories: frozenset[str], where: str) -> dict[str, Decimal]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise FinanceError(f"{path}: '{where}' precisa ser um mapa categoria -> valor")
    caps: dict[str, Decimal] = {}
    for category, value in raw.items():
        if category not in categories:
            raise FinanceError(f"{path}: categoria desconhecida em '{where}': {category!r}")
        caps[str(category)] = parse_amount(str(value))
    return caps
