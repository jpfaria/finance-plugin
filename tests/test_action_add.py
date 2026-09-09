from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from itertools import count

import pytest

from finance.actions.add import AddRequest, build_manual_entries, split_installments
from finance.model.account import Account, AccountType
from finance.model.entry import Status
from finance.model.errors import FinanceError

CARD = Account(
    id="nu-card",
    name="Nubank cartão",
    bank="nubank",
    type=AccountType.CREDIT,
    closing_day=3,
    due_day=10,
)
CHECKING = Account(id="nu", name="Nubank conta", bank="nubank", type=AccountType.CHECKING)
CATS = frozenset({"casa/luz", "transporte/uber"})


def _id_iter() -> Iterator[str]:
    return (f"ID{n}" for n in count())


def test_split_installments_exact_sum() -> None:
    parts = split_installments(Decimal("-100.00"), 3)
    assert parts == [Decimal("-33.33"), Decimal("-33.33"), Decimal("-33.34")]
    assert sum(parts) == Decimal("-100.00")
    assert split_installments(Decimal("-10.00"), 1) == [Decimal("-10.00")]


def test_split_installments_rejects_zero() -> None:
    with pytest.raises(FinanceError, match="parcelas"):
        split_installments(Decimal("-10.00"), 0)


def test_single_entry() -> None:
    req = AddRequest(
        CHECKING, Decimal("-50.00"), date(2026, 9, 5), "uber", "transporte/uber", ("viagem",), 1
    )
    [e] = build_manual_entries(req, CATS, _id_iter())
    assert e.id == "ID0"
    assert e.account == "nu"
    assert e.amount == Decimal("-50.00")
    assert e.status is Status.MANUAL
    assert e.source == "manual"
    assert e.installment == ""
    assert e.tags == ("viagem",)


def test_installments_spread_over_months_with_group() -> None:
    req = AddRequest(CARD, Decimal("-1000.00"), date(2026, 1, 31), "celular", "", (), 3)
    entries = build_manual_entries(req, CATS, _id_iter())
    assert [e.date for e in entries] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
    assert [e.installment for e in entries] == ["1/3", "2/3", "3/3"]
    assert {e.installment_group for e in entries} == {"ID0"}
    assert sum(e.amount for e in entries) == Decimal("-1000.00")


def test_installments_only_on_credit() -> None:
    req = AddRequest(CHECKING, Decimal("-90.00"), date(2026, 9, 5), "x", "", (), 3)
    with pytest.raises(FinanceError, match="cartão"):
        build_manual_entries(req, CATS, _id_iter())


def test_unknown_category_rejected() -> None:
    req = AddRequest(CHECKING, Decimal("-5.00"), date(2026, 9, 5), "x", "lazer/bar", (), 1)
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        build_manual_entries(req, CATS, _id_iter())
