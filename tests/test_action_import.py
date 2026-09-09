from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from itertools import count

from finance.actions.import_statement import build_import_entries
from finance.config.rules import Rule
from finance.imports.record import ImportedRecord, record_hash
from finance.model.account import Account, AccountType
from finance.model.entry import Status

NU = Account(id="nu", name="Nubank conta", bank="nubank", type=AccountType.CHECKING)


def _ids() -> Iterator[str]:
    return (f"ID{n}" for n in count())


def test_dedupe_rules_and_uncategorized() -> None:
    records = [
        ImportedRecord(date(2026, 9, 1), Decimal("-35.90"), "UBER TRIP", "T1"),
        ImportedRecord(date(2026, 9, 3), Decimal("1200.00"), "PIX RECEBIDO", "T2"),
        ImportedRecord(date(2026, 9, 4), Decimal("-9.00"), "PADARIA", "T3"),
    ]
    existing = {record_hash("nu", records[2])}
    rules = [Rule("uber", "transporte/uber")]
    result = build_import_entries(records, NU, "extrato.ofx", existing, rules, _ids())
    assert result.duplicates == 1
    assert result.uncategorized == 1
    assert [e.id for e in result.new] == ["ID0", "ID1"]
    uber, pix = result.new
    assert uber.category == "transporte/uber"
    assert uber.status is Status.CONFIRMED
    assert uber.source == "extrato.ofx"
    assert uber.import_hash == record_hash("nu", records[0])
    assert pix.category == ""
    assert pix.account == "nu"
