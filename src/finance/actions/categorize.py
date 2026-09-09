"""List uncategorized entries and assign a category to one of them."""

from collections.abc import Sequence
from dataclasses import replace

from finance.model.entry import Entry
from finance.model.errors import FinanceError


def pending(entries: Sequence[Entry], year: int | None, month: int | None) -> list[Entry]:
    return [
        e
        for e in entries
        if not e.category
        and not e.is_transfer
        and (year is None or e.date.year == year)
        and (month is None or e.date.month == month)
    ]


def set_category(
    entries: Sequence[Entry], entry_id: str, category: str, categories: frozenset[str]
) -> Entry:
    if category not in categories:
        raise FinanceError(f"categoria desconhecida: {category!r}")
    for entry in entries:
        if entry.id == entry_id:
            return replace(entry, category=category)
    raise FinanceError(f"lançamento não encontrado: {entry_id!r}")
