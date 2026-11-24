"""Reapply rules.yaml over entries already in the ledger, sparing manual categories."""

from collections.abc import Sequence
from dataclasses import dataclass, replace

from finance.config.rules import Rule, apply_rules
from finance.model.entry import CategorySource, Entry


@dataclass(frozen=True)
class CategoryChange:
    """One entry a rule would move: `entry` already carries the new category."""

    entry: Entry
    before: str


@dataclass(frozen=True)
class RecategorizeResult:
    """`changes` are the entries to write back; the counts describe the scope."""

    changes: list[CategoryChange]
    uncategorized: int
    scanned: int


def reapply_rules(
    entries: Sequence[Entry],
    rules: Sequence[Rule],
    *,
    year: int | None = None,
    month: int | None = None,
    account_ids: frozenset[str] | None = None,
    force: bool = False,
) -> RecategorizeResult:
    """Run `rules` over the entries in scope and report what changes.

    Scope is every entry that is not a transfer and matches `year`/`month` (both
    or neither) and `account_ids` when given. Without `force` only entries with no
    category are evaluated; with `force`, those whose category came from a rule as
    well. A manual category is never evaluated. A rule that no longer matches does
    NOT clear the category it once set — an empty `rules.yaml` must not wipe the
    ledger. Nothing is written here: the caller persists `changes`.
    """
    changes: list[CategoryChange] = []
    uncategorized = 0
    scanned = 0
    for entry in entries:
        if not _in_scope(entry, year, month, account_ids):
            continue
        scanned += 1
        updated = _reapplied(entry, rules, force=force)
        if updated is not None:
            changes.append(CategoryChange(updated, entry.category))
        elif not entry.category:
            uncategorized += 1
    return RecategorizeResult(changes=changes, uncategorized=uncategorized, scanned=scanned)


def _in_scope(
    entry: Entry, year: int | None, month: int | None, account_ids: frozenset[str] | None
) -> bool:
    return (
        not entry.is_transfer
        and (year is None or entry.date.year == year)
        and (month is None or entry.date.month == month)
        and (account_ids is None or entry.account in account_ids)
    )


def _reapplied(entry: Entry, rules: Sequence[Rule], *, force: bool) -> Entry | None:
    """The entry with its new rule-applied category, or None when nothing changes."""
    if entry.category_source is CategorySource.MANUAL:
        return None
    if entry.category and not force:
        return None
    category = apply_rules(rules, entry.description)
    if not category or category == entry.category:
        return None
    return replace(entry, category=category, category_source=CategorySource.RULE)
