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
from finance.model.entry import CategorySource, Entry, Status

LEGACY_HEADER = (
    "id,date,account,amount,description,category,tags,installment,"
    "installment_group,transfer_group,status,source,import_hash"
)


def _entry(id_: str = "01HZZZZZZZZZZZZZZZZZZZZZZZ", when: date = date(2026, 9, 5)) -> Entry:
    return Entry(
        id=id_,
        date=when,
        account="nu-card",
        amount=Decimal("-120.00"),
        description="celular 1/10",
        category="casa/luz",
        category_source=CategorySource.MANUAL,
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
    assert row["category_source"] == "manual"
    assert row_to_entry(row) == e


def test_legacy_file_without_the_column_counts_a_category_as_rule_applied(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "2026-09.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"{LEGACY_HEADER}\n"
        "A,2026-09-05,nu,-10.00,UBER TRIP,transporte/uber,,,,,confirmed,extrato.ofx,H1\n"
        "B,2026-09-06,nu,-20.00,PADARIA,,,,,,confirmed,extrato.ofx,H2\n",
        encoding="utf-8",
    )
    uber, padaria = read_month_file(path)
    assert (uber.category, uber.category_source) == ("transporte/uber", CategorySource.RULE)
    assert (padaria.category, padaria.category_source) == ("", CategorySource.NONE)


def test_rewriting_a_legacy_file_adds_the_column(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "2026-09.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"{LEGACY_HEADER}\n"
        "A,2026-09-05,nu,-10.00,UBER TRIP,transporte/uber,,,,,confirmed,extrato.ofx,H1\n",
        encoding="utf-8",
    )
    write_month_file(path, read_month_file(path))
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(COLUMNS)
    assert read_month_file(path)[0].category_source is CategorySource.RULE


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
