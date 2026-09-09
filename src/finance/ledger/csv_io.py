"""Entry <-> CSV row, and reading/writing one month file."""

import csv
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.model.entry import Entry, Status
from finance.model.money import format_amount

TAG_SEPARATOR = ";"

COLUMNS: tuple[str, ...] = (
    "id",
    "date",
    "account",
    "amount",
    "description",
    "category",
    "tags",
    "installment",
    "installment_group",
    "transfer_group",
    "status",
    "source",
    "import_hash",
)


def entry_to_row(entry: Entry) -> dict[str, str]:
    return {
        "id": entry.id,
        "date": entry.date.isoformat(),
        "account": entry.account,
        "amount": format_amount(entry.amount),
        "description": entry.description,
        "category": entry.category,
        "tags": TAG_SEPARATOR.join(entry.tags),
        "installment": entry.installment,
        "installment_group": entry.installment_group,
        "transfer_group": entry.transfer_group,
        "status": entry.status.value,
        "source": entry.source,
        "import_hash": entry.import_hash,
    }


def row_to_entry(row: dict[str, str]) -> Entry:
    return Entry(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        account=row["account"],
        amount=Decimal(row["amount"]),
        description=row["description"],
        category=row.get("category", ""),
        tags=tuple(t for t in row.get("tags", "").split(TAG_SEPARATOR) if t),
        installment=row.get("installment", ""),
        installment_group=row.get("installment_group", ""),
        transfer_group=row.get("transfer_group", ""),
        status=Status(row.get("status") or Status.MANUAL.value),
        source=row.get("source") or "manual",
        import_hash=row.get("import_hash", ""),
    )


def read_month_file(path: Path) -> list[Entry]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [row_to_entry(row) for row in csv.DictReader(fh)]


def write_month_file(path: Path, entries: Sequence[Entry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries, key=lambda e: (e.date, e.id))
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for entry in ordered:
            writer.writerow(entry_to_row(entry))
