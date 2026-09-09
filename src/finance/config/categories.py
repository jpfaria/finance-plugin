"""Load categories.yaml: two-level tree flattened to 'group/item' paths."""

from pathlib import Path
from typing import Any

import yaml

from finance.model.errors import FinanceError


def load_categories(path: Path) -> frozenset[str]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise FinanceError(f"{path}: esperado um mapa grupo -> lista de itens")
    paths: set[str] = set()
    for group, items in raw.items():
        if not isinstance(items, list) or not items:
            raise FinanceError(f"{path}: grupo {group!r} precisa de uma lista de itens")
        for item in items:
            paths.add(f"{group}/{item}")
    return frozenset(paths)
