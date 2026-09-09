from datetime import date
from decimal import Decimal

from finance.imports.record import ImportedRecord, record_hash


def test_hash_is_stable_and_account_scoped() -> None:
    rec = ImportedRecord(date(2026, 9, 1), Decimal("-10.00"), " uber ", "abc")
    same = ImportedRecord(date(2026, 9, 1), Decimal("-10"), "uber", "abc")
    assert record_hash("nu", rec) == record_hash("nu", same)
    assert record_hash("nu", rec) != record_hash("bra", rec)
    assert len(record_hash("nu", rec)) == 64


def test_hash_changes_with_external_id() -> None:
    a = ImportedRecord(date(2026, 9, 1), Decimal("-10.00"), "x", "1")
    b = ImportedRecord(date(2026, 9, 1), Decimal("-10.00"), "x", "2")
    assert record_hash("nu", a) != record_hash("nu", b)
