"""OFX statements (any bank): amounts already signed per the OFX spec."""

from decimal import Decimal
from pathlib import Path

from ofxparse import OfxParser as _OfxParser

from finance.imports.record import ImportedRecord
from finance.model.money import CENTS

OFX_EXTENSION = ".ofx"
OFX_MARKERS = ("OFXHEADER", "<OFX>")


class OfxParser:
    name = "ofx"

    def matches(self, path: Path, head: str) -> bool:
        return path.suffix.lower() == OFX_EXTENSION or any(m in head for m in OFX_MARKERS)

    def parse(self, path: Path) -> list[ImportedRecord]:
        with path.open("rb") as fh:
            ofx = _OfxParser.parse(fh)
        records: list[ImportedRecord] = []
        for trn in ofx.account.statement.transactions:
            records.append(
                ImportedRecord(
                    date=trn.date.date(),
                    amount=Decimal(str(trn.amount)).quantize(CENTS),
                    description=str(trn.memo or trn.payee or "").strip(),
                    external_id=str(trn.id or ""),
                )
            )
        return records
