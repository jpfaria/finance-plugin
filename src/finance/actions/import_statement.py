"""Turn parsed statement records into confirmed ledger entries (dedupe + rules)."""

from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from finance.config.rules import Rule, apply_rules
from finance.imports.record import ImportedRecord, record_hash, record_key
from finance.model.account import Account
from finance.model.entry import CategorySource, Entry, Status


@dataclass(frozen=True)
class ImportResult:
    new: list[Entry]
    duplicates: int
    uncategorized: int


def build_import_entries(
    records: Sequence[ImportedRecord],
    account: Account,
    source: str,
    existing_hashes: set[str],
    rules: Sequence[Rule],
    ids: Iterator[str],
) -> ImportResult:
    new: list[Entry] = []
    duplicates = 0
    occurrences: Counter[str] = Counter()
    for record in records:
        key = record_key(account.id, record)
        digest = record_hash(account.id, record, occurrences[key])
        occurrences[key] += 1
        if digest in existing_hashes:
            duplicates += 1
            continue
        category = apply_rules(rules, record.description)
        new.append(
            Entry(
                id=next(ids),
                date=record.date,
                account=account.id,
                amount=record.amount,
                description=record.description,
                category=category,
                category_source=CategorySource.RULE if category else CategorySource.NONE,
                status=Status.CONFIRMED,
                source=source,
                import_hash=digest,
            )
        )
    uncategorized = sum(1 for e in new if not e.category)
    return ImportResult(new, duplicates, uncategorized)
