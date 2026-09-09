from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.imports.ofx import OfxParser

FIXTURE = Path(__file__).parent / "fixtures" / "sample.ofx"


def test_matches_by_extension_or_header() -> None:
    parser = OfxParser()
    assert parser.matches(Path("x.ofx"), "")
    assert parser.matches(Path("x.txt"), "OFXHEADER:100\n")
    assert not parser.matches(Path("x.csv"), "date,title,amount")


def test_parse_transactions() -> None:
    records = OfxParser().parse(FIXTURE)
    assert [(r.date, r.amount, r.description, r.external_id) for r in records] == [
        (date(2026, 9, 1), Decimal("-35.90"), "UBER TRIP", "T1"),
        (date(2026, 9, 3), Decimal("1200.00"), "PIX RECEBIDO", "T2"),
    ]
