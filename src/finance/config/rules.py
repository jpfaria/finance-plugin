"""rules.yaml: ordered description-regex -> category rules."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from finance.model.errors import FinanceError

RULES_KEY = "rules"


@dataclass(frozen=True)
class Rule:
    pattern: str
    category: str


def load_rules(path: Path, categories: frozenset[str]) -> list[Rule]:
    rules: list[Rule] = []
    for item in _read(path):
        if not isinstance(item, dict) or "pattern" not in item or "category" not in item:
            raise FinanceError(f"{path}: regra inválida: {item!r}")
        rule = Rule(str(item["pattern"]), str(item["category"]))
        if rule.category not in categories:
            raise FinanceError(f"{path}: categoria desconhecida: {rule.category!r}")
        try:
            re.compile(rule.pattern)
        except re.error as exc:
            raise FinanceError(f"{path}: regex inválida {rule.pattern!r}: {exc}") from exc
        rules.append(rule)
    return rules


def apply_rules(rules: Sequence[Rule], description: str) -> str:
    for rule in rules:
        if re.search(rule.pattern, description, re.IGNORECASE):
            return rule.category
    return ""


def append_rule(path: Path, rule: Rule) -> None:
    items = _read(path)
    items.append({"pattern": rule.pattern, "category": rule.category})
    path.write_text(
        yaml.safe_dump({RULES_KEY: items}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _read(path: Path) -> list[Any]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    items = (raw or {}).get(RULES_KEY, []) if isinstance(raw or {}, dict) else None
    if not isinstance(items, list):
        raise FinanceError(f"{path}: esperado uma lista em '{RULES_KEY}'")
    return items
