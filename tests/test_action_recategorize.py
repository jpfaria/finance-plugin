from datetime import date
from decimal import Decimal

from finance.actions.recategorize import reapply_rules
from finance.config.rules import Rule
from finance.model.entry import CategorySource, Entry

UBER = Rule("uber", "transporte/uber")
LUZ = Rule("enel", "casa/luz")


def _e(
    id_: str,
    description: str,
    *,
    when: date = date(2026, 9, 1),
    account: str = "nu",
    category: str = "",
    source: CategorySource = CategorySource.NONE,
    transfer: str = "",
) -> Entry:
    return Entry(
        id=id_,
        date=when,
        account=account,
        amount=Decimal("-10.00"),
        description=description,
        category=category,
        category_source=source,
        transfer_group=transfer,
    )


def test_new_rule_catches_old_uncategorized_entry() -> None:
    entries = [_e("a", "UBER TRIP 123")]
    result = reapply_rules(entries, [UBER])
    assert [(c.before, c.entry.category) for c in result.changes] == [("", "transporte/uber")]
    assert result.changes[0].entry.category_source is CategorySource.RULE
    assert result.changes[0].entry.id == "a"
    assert result.uncategorized == 0
    assert result.scanned == 1


def test_manual_category_survives_force() -> None:
    entries = [_e("a", "UBER TRIP", category="casa/luz", source=CategorySource.MANUAL)]
    result = reapply_rules(entries, [UBER], force=True)
    assert result.changes == []
    assert result.uncategorized == 0


def test_rule_category_is_untouched_without_force() -> None:
    entries = [_e("a", "UBER TRIP", category="casa/luz", source=CategorySource.RULE)]
    assert reapply_rules(entries, [UBER]).changes == []


def test_force_reevaluates_rule_category() -> None:
    entries = [_e("a", "UBER TRIP", category="casa/luz", source=CategorySource.RULE)]
    [change] = reapply_rules(entries, [UBER], force=True).changes
    assert change.before == "casa/luz"
    assert change.entry.category == "transporte/uber"
    assert change.entry.category_source is CategorySource.RULE


def test_force_keeps_category_when_no_rule_matches() -> None:
    entries = [_e("a", "PADARIA", category="casa/luz", source=CategorySource.RULE)]
    result = reapply_rules(entries, [UBER], force=True)
    assert result.changes == []
    assert result.uncategorized == 0


def test_no_matching_rule_leaves_entry_uncategorized() -> None:
    result = reapply_rules([_e("a", "PADARIA")], [UBER])
    assert result.changes == []
    assert result.uncategorized == 1
    assert result.scanned == 1


def test_month_filter_limits_the_scope() -> None:
    entries = [
        _e("a", "UBER TRIP", when=date(2026, 9, 10)),
        _e("b", "UBER TRIP", when=date(2026, 10, 10)),
        _e("c", "UBER TRIP", when=date(2025, 9, 10)),
    ]
    result = reapply_rules(entries, [UBER], year=2026, month=9)
    assert [c.entry.id for c in result.changes] == ["a"]
    assert result.scanned == 1


def test_account_filter_limits_the_scope() -> None:
    entries = [
        _e("a", "UBER TRIP", account="nu"),
        _e("b", "UBER TRIP", account="bra"),
    ]
    result = reapply_rules(entries, [UBER], account_ids=frozenset({"bra"}))
    assert [c.entry.id for c in result.changes] == ["b"]
    assert result.scanned == 1


def test_transfers_are_out_of_scope() -> None:
    entries = [_e("a", "UBER TRIP", transfer="T1"), _e("b", "UBER TRIP")]
    result = reapply_rules(entries, [UBER])
    assert [c.entry.id for c in result.changes] == ["b"]
    assert result.scanned == 1


def test_first_matching_rule_wins_and_report_counts_the_rest() -> None:
    entries = [
        _e("a", "UBER TRIP"),
        _e("b", "ENEL SP"),
        _e("c", "PADARIA"),
        _e("d", "FEIRA"),
    ]
    result = reapply_rules(entries, [UBER, LUZ])
    assert [(c.entry.id, c.entry.category) for c in result.changes] == [
        ("a", "transporte/uber"),
        ("b", "casa/luz"),
    ]
    assert result.scanned == 4
    assert result.uncategorized == 2


def test_rule_that_matches_the_same_category_is_not_a_change() -> None:
    entries = [_e("a", "UBER TRIP", category="transporte/uber", source=CategorySource.RULE)]
    assert reapply_rules(entries, [UBER], force=True).changes == []


def test_entries_are_never_mutated() -> None:
    entry = _e("a", "UBER TRIP")
    reapply_rules([entry], [UBER])
    assert entry.category == ""
    assert entry.category_source is CategorySource.NONE
