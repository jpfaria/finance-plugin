"""Normalized statement line and its dedupe hash."""

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.model.money import format_amount

HASH_SEPARATOR = "|"
OCCURRENCE_PREFIX = "#"


@dataclass(frozen=True)
class ImportedRecord:
    date: date
    amount: Decimal
    description: str
    external_id: str = ""


def record_key(account_id: str, record: ImportedRecord) -> str:
    """Identity of a statement line, shared by every repetition of it.

    Two real purchases of the same value, at the same place, on the same day
    share this key; the occurrence ordinal is what tells them apart.
    """
    return HASH_SEPARATOR.join(
        (
            account_id,
            record.date.isoformat(),
            format_amount(record.amount),
            record.description.strip(),
            record.external_id,
        )
    )


def record_hash(account_id: str, record: ImportedRecord, occurrence: int = 0) -> str:
    """Dedupe hash of the `occurrence`-th line with this record's identity.

    `occurrence` counts, from 0, the identical lines seen before this one in the
    same statement. Occurrence 0 keeps the historical key, so entries imported
    before occurrence counting existed still match on re-import.
    """
    key = record_key(account_id, record)
    if occurrence:
        key = f"{key}{HASH_SEPARATOR}{OCCURRENCE_PREFIX}{occurrence}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
