from datetime import date
from decimal import Decimal

from finance.actions.reconcile import merge, reconcile
from finance.model.entry import Entry, Status


def _manual(id_: str, d: date, amount: str, installment: str = "") -> Entry:
    return Entry(
        id=id_,
        date=d,
        account="nu-card",
        amount=Decimal(amount),
        description="celular",
        category="pessoal/eletronicos",
        installment=installment,
        installment_group="G",
    )


def _imported(id_: str, d: date, amount: str, account: str = "nu-card") -> Entry:
    return Entry(
        id=id_,
        date=d,
        account=account,
        amount=Decimal(amount),
        description="CELULAR 01/10",
        status=Status.CONFIRMED,
        source="fatura.csv",
        import_hash=f"h-{id_}",
    )


def test_matches_by_amount_window_and_installment() -> None:
    entries = [
        _manual("m1", date(2026, 9, 5), "-100.00", "1/10"),
        _manual("m2", date(2026, 10, 5), "-100.00", "2/10"),
        _imported("i1", date(2026, 9, 7), "-100.00"),
        _imported("i2", date(2026, 9, 7), "-100.00", account="nu"),
        _imported("i3", date(2026, 9, 20), "-55.00"),
    ]
    result = reconcile(entries, window_days=3, stale_days=45, today=date(2026, 9, 30))
    assert [(m.manual.id, m.imported.id) for m in result.matches] == [("m1", "i1")]
    assert [e.id for e in result.unmatched_imported] == ["i2", "i3"]
    assert result.stale_manual == []


def test_greedy_closest_date_and_each_imported_once() -> None:
    entries = [
        _manual("m1", date(2026, 9, 1), "-50.00"),
        _manual("m2", date(2026, 9, 3), "-50.00"),
        _imported("i1", date(2026, 9, 3), "-50.00"),
    ]
    result = reconcile(entries, window_days=3, stale_days=45, today=date(2026, 9, 30))
    assert [(m.manual.id, m.imported.id) for m in result.matches] == [("m2", "i1")]


def test_stale_manual() -> None:
    entries = [
        _manual("old", date(2026, 6, 1), "-10.00"),
        _manual("new", date(2026, 9, 20), "-10.00"),
    ]
    result = reconcile(entries, window_days=3, stale_days=45, today=date(2026, 9, 30))
    assert [e.id for e in result.stale_manual] == ["old"]


def test_merge_keeps_manual_identity_and_takes_import_trace() -> None:
    manual = _manual("m1", date(2026, 9, 5), "-100.00", "1/10")
    imported = _imported("i1", date(2026, 9, 7), "-100.00")
    merged = merge(manual, imported)
    assert merged.id == "m1"
    assert merged.category == "pessoal/eletronicos"
    assert merged.description == "celular"
    assert merged.date == date(2026, 9, 5)
    assert merged.status is Status.CONFIRMED
    assert merged.import_hash == "h-i1"
    assert merged.source == "fatura.csv"
