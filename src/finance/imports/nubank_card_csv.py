"""Nubank credit-card CSV export: date,title,amount (positive amount = purchase).

Amounts come in BRL notation as the app exports them: `1.111,00`, and a
credit as `- 54,95`. Parsing goes through `parse_amount`, the single place
that knows that notation.
"""

from datetime import date
from pathlib import Path

from finance.imports.csv_rows import header_line, read_rows
from finance.imports.record import ImportedRecord
from finance.model.money import parse_amount

HEADER = "date,title,amount"


class NubankCardCsv:
    name = "nubank-card-csv"

    def matches(self, path: Path, head: str) -> bool:
        return header_line(head) == HEADER

    def parse(self, path: Path) -> list[ImportedRecord]:
        return [
            ImportedRecord(
                date=date.fromisoformat(row["date"]),
                amount=-parse_amount(row["amount"]),
                description=row["title"].strip(),
            )
            for row in read_rows(path)
        ]
