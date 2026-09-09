"""Turn parsed statement records into confirmed ledger entries (dedupe + rules)."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from finance.config.rules import Rule, apply_rules
from finance.imports.record import ImportedRecord, record_hash
from finance.model.account import Account
from finance.model.entry import Entry, Status


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
    seen = set(existing_hashes)
    for record in records:
        digest = record_hash(account.id, record)
        if digest in seen:
            duplicates += 1
            continue
        seen.add(digest)
        new.append(
            Entry(
                id=next(ids),
                date=record.date,
                account=account.id,
                amount=record.amount,
                description=record.description,
                category=apply_rules(rules, record.description),
                status=Status.CONFIRMED,
                source=source,
                import_hash=digest,
            )
        )
    uncategorized = sum(1 for e in new if not e.category)
    return ImportResult(new, duplicates, uncategorized)
