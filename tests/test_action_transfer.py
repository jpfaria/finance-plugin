from datetime import date
from decimal import Decimal

import pytest

from finance.actions.transfer import candidates, clear, link
from finance.model.entry import Entry
from finance.model.errors import FinanceError


def _e(id_: str, account: str, amount: str, day: int, transfer: str = "") -> Entry:
    return Entry(
        id=id_,
        date=date(2026, 11, day),
        account=account,
        amount=Decimal(amount),
        description=id_,
        transfer_group=transfer,
    )


def test_candidates_pairs_opposite_amounts_in_different_accounts() -> None:
    pay = _e("b", "bra", "-17100.90", 9)
    credit = _e("c", "nu-card", "17100.90", 7)
    noise = _e("d", "bra", "-50.00", 9)
    found = candidates([pay, credit, noise])
    assert [(c.out_leg.id, c.in_leg.id, c.days_apart) for c in found] == [("b", "c", 2)]


def test_candidates_ignores_the_same_account_and_what_is_far_apart() -> None:
    same_account = [_e("a", "bra", "-100.00", 1), _e("b", "bra", "100.00", 1)]
    far = [_e("c", "bra", "-100.00", 1), _e("d", "nu", "100.00", 20)]
    assert candidates(same_account) == []
    assert candidates(far) == []
    assert [c.in_leg.id for c in candidates(far, window_days=30)] == ["d"]


def test_candidates_leaves_out_what_is_already_marked() -> None:
    marked = [_e("a", "bra", "-100.00", 1, transfer="g"), _e("b", "nu", "100.00", 1)]
    assert candidates(marked) == []


def test_each_leg_is_used_in_one_pair_only() -> None:
    out = _e("a", "bra", "-100.00", 10)
    near = _e("b", "nu", "100.00", 10)
    far = _e("c", "nu", "100.00", 12)
    found = candidates([out, near, far])
    assert [(c.out_leg.id, c.in_leg.id) for c in found] == [("a", "b")]


def test_link_puts_both_legs_in_the_group_of_the_smallest_id() -> None:
    entries = [_e("b", "bra", "-17100.90", 9), _e("a", "nu-card", "17100.90", 7)]
    linked = link(entries, ["b", "a"])
    assert [e.id for e in linked] == ["b", "a"]
    assert {e.transfer_group for e in linked} == {"a"}
    assert all(e.is_transfer for e in linked)


def test_link_refuses_legs_that_do_not_cancel_out() -> None:
    entries = [_e("a", "bra", "-100.00", 1), _e("b", "nu", "90.00", 1)]
    with pytest.raises(FinanceError, match=r"somam -10\.00"):
        link(entries, ["a", "b"])


def test_link_marks_a_lone_leg_only_with_force() -> None:
    entries = [_e("a", "bra", "-100.00", 1)]
    with pytest.raises(FinanceError, match="não parece transferência"):
        link(entries, ["a"])
    assert link(entries, ["a"], force=True)[0].transfer_group == "a"


def test_link_refuses_an_entry_that_is_already_a_transfer() -> None:
    entries = [_e("a", "bra", "-100.00", 1, transfer="old"), _e("b", "nu", "100.00", 1)]
    with pytest.raises(FinanceError, match="já marcado"):
        link(entries, ["a", "b"])


def test_link_refuses_an_empty_list_a_repeated_id_and_an_unknown_id() -> None:
    entries = [_e("a", "bra", "-100.00", 1)]
    with pytest.raises(FinanceError, match="pelo menos um"):
        link(entries, [])
    with pytest.raises(FinanceError, match="id repetido"):
        link(entries, ["a", "a"], force=True)
    with pytest.raises(FinanceError, match="não encontrado: zz"):
        link(entries, ["zz"])


def test_clear_only_touches_what_is_marked() -> None:
    entries = [_e("a", "bra", "-100.00", 1, transfer="g"), _e("b", "nu", "100.00", 1)]
    assert clear(entries, ["a"])[0].transfer_group == ""
    with pytest.raises(FinanceError, match="não está marcado"):
        clear(entries, ["b"])
