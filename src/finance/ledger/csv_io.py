"""Entry <-> CSV row, and reading/writing one month file."""

import csv
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.model.entry import CategorySource, Entry, Status
from finance.model.money import format_amount

TAG_SEPARATOR = ";"
CATEGORY_SOURCE_COLUMN = "category_source"

COLUMNS: tuple[str, ...] = (
    "id",
    "date",
    "account",
    "amount",
    "description",
    "category",
    CATEGORY_SOURCE_COLUMN,
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
        CATEGORY_SOURCE_COLUMN: entry.category_source.value,
        "tags": TAG_SEPARATOR.join(entry.tags),
        "installment": entry.installment,
        "installment_group": entry.installment_group,
        "transfer_group": entry.transfer_group,
        "status": entry.status.value,
        "source": entry.source,
        "import_hash": entry.import_hash,
    }


def _category_source(row: dict[str, str], category: str) -> CategorySource:
    """The recorded origin; absent column -> a category counts as rule-applied.

    Lines written before the column existed carry no origin. Treating them as
    rule-applied is what keeps the migration free of a manual step: `recategorize`
    without `--force` ignores them anyway (they have a category), and with
    `--force` they are exactly the ones the user wants re-evaluated.
    """
    recorded = row.get(CATEGORY_SOURCE_COLUMN)
    if recorded is None:
        return CategorySource.RULE if category else CategorySource.NONE
    return CategorySource(recorded)


def row_to_entry(row: dict[str, str]) -> Entry:
    category = row.get("category", "")
    return Entry(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        account=row["account"],
        amount=Decimal(row["amount"]),
        description=row["description"],
        category=category,
        category_source=_category_source(row, category),
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
