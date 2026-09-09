"""Nubank credit-card CSV export: date,title,amount (positive amount = purchase)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.imports.csv_rows import header_line, read_rows
from finance.imports.record import ImportedRecord
from finance.model.money import CENTS

HEADER = "date,title,amount"


class NubankCardCsv:
    name = "nubank-card-csv"

    def matches(self, path: Path, head: str) -> bool:
        return header_line(head) == HEADER

    def parse(self, path: Path) -> list[ImportedRecord]:
        return [
            ImportedRecord(
                date=date.fromisoformat(row["date"]),
                amount=-Decimal(row["amount"]).quantize(CENTS),
                description=row["title"].strip(),
            )
            for row in read_rows(path)
        ]
