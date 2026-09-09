from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.ledger.csv_io import (
    COLUMNS,
    entry_to_row,
    read_month_file,
    row_to_entry,
    write_month_file,
)
from finance.ledger.ids import new_id
from finance.model.entry import Entry, Status


def _entry(id_: str = "01HZZZZZZZZZZZZZZZZZZZZZZZ", when: date = date(2026, 9, 5)) -> Entry:
    return Entry(
        id=id_,
        date=when,
        account="nu-card",
        amount=Decimal("-120.00"),
        description="celular 1/10",
        category="casa/luz",
        tags=("pessoal", "eletronico"),
        installment="1/10",
        installment_group="G1",
        status=Status.MANUAL,
    )


def test_new_id_is_ulid_shaped() -> None:
    a, b = new_id(), new_id()
    assert len(a) == 26
    assert a != b


def test_row_roundtrip() -> None:
    e = _entry()
    row = entry_to_row(e)
    assert tuple(row) == COLUMNS
    assert row["amount"] == "-120.00"
    assert row["tags"] == "pessoal;eletronico"
    assert row["status"] == "manual"
    assert row_to_entry(row) == e


def test_write_then_read_sorted(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "2026-09.csv"
    later = _entry("01HZZZZZZZZZZZZZZZZZZZZZZB", date(2026, 9, 20))
    earlier = _entry("01HZZZZZZZZZZZZZZZZZZZZZZA", date(2026, 9, 1))
    write_month_file(path, [later, earlier])
    assert read_month_file(path) == [earlier, later]
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(COLUMNS)


def test_read_missing_file_is_empty(tmp_path: Path) -> None:
    assert read_month_file(tmp_path / "nope.csv") == []
