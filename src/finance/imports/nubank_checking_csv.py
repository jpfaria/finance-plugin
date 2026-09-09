"""Nubank checking-account CSV export: Data,Valor,Identificador,Descrição."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from finance.imports.csv_rows import header_line, read_rows
from finance.imports.record import ImportedRecord
from finance.model.money import CENTS

HEADER = "Data,Valor,Identificador,Descrição"
DATE_FORMAT = "%d/%m/%Y"


class NubankCheckingCsv:
    name = "nubank-checking-csv"

    def matches(self, path: Path, head: str) -> bool:
        return header_line(head) == HEADER

    def parse(self, path: Path) -> list[ImportedRecord]:
        return [
            ImportedRecord(
                date=datetime.strptime(row["Data"], DATE_FORMAT).date(),
                amount=Decimal(row["Valor"]).quantize(CENTS),
                description=row["Descrição"].strip(),
                external_id=row["Identificador"].strip(),
            )
            for row in read_rows(path)
        ]
