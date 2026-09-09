"""Normalized statement line and its dedupe hash."""

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.model.money import format_amount

HASH_SEPARATOR = "|"


@dataclass(frozen=True)
class ImportedRecord:
    date: date
    amount: Decimal
    description: str
    external_id: str = ""


def record_hash(account_id: str, record: ImportedRecord) -> str:
    key = HASH_SEPARATOR.join(
        (
            account_id,
            record.date.isoformat(),
            format_amount(record.amount),
            record.description.strip(),
            record.external_id,
        )
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
