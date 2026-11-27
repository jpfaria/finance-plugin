"""Rateio: uma cobrança só paga duas coisas; as partes somam o valor original."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest

from finance.actions.split import Part, split
from finance.model.entry import CategorySource, Entry, Status
from finance.model.errors import FinanceError

CATEGORIES = frozenset({"casa/luz", "casa/aluguel", "transporte/uber"})


def _entry(amount: str, **kwargs: object) -> Entry:
    base = {
        "id": "A",
        "date": date(2026, 11, 24),
        "account": "bra-card",
        "amount": Decimal(amount),
        "description": "STARLINK",
        "status": Status.CONFIRMED,
        "source": "bradesco-card-pdf",
        "import_hash": "h1",
    }
    return Entry(**{**base, **kwargs})  # type: ignore[arg-type]


def _ids() -> Iterator[str]:
    return iter(["B", "C"])


def test_parts_keep_the_sign_the_hash_and_the_first_id() -> None:
    entries = [_entry("-868.00")]
    parts = [Part(Decimal("576.00"), "casa/luz"), Part(Decimal("292.00"), "casa/aluguel")]
    new = split(entries, "A", parts, CATEGORIES, iter(["B"]))
    assert [(e.id, e.amount, e.category) for e in new] == [
        ("A", Decimal("-576.00"), "casa/luz"),
        ("B", Decimal("-292.00"), "casa/aluguel"),
    ]
    assert all(e.import_hash == "h1" for e in new)
    assert all(e.category_source is CategorySource.MANUAL for e in new)
    assert sum(e.amount for e in new) == Decimal("-868.00")


def test_description_says_which_part_it_is() -> None:
    parts = [Part(Decimal("500.00"), "casa/luz"), Part(Decimal("368.00"), "casa/aluguel")]
    new = split([_entry("-868.00")], "A", parts, CATEGORIES, iter(["B"]))
    assert [e.description for e in new] == [
        "STARLINK - Rateio 1/2",
        "STARLINK - Rateio 2/2",
    ]


def test_income_is_split_as_income() -> None:
    parts = [Part(Decimal("100.00"), "casa/luz"), Part(Decimal("50.00"), "casa/aluguel")]
    new = split([_entry("150.00")], "A", parts, CATEGORIES, iter(["B"]))
    assert [e.amount for e in new] == [Decimal("100.00"), Decimal("50.00")]


def test_parts_that_do_not_add_up_are_an_error() -> None:
    parts = [Part(Decimal("576.00"), "casa/luz"), Part(Decimal("200.00"), "casa/aluguel")]
    with pytest.raises(FinanceError, match=r"somam 776\.00 em vez de 868\.00"):
        split([_entry("-868.00")], "A", parts, CATEGORIES, iter(["B"]))


def test_a_single_part_is_not_a_split() -> None:
    with pytest.raises(FinanceError, match="pelo menos 2 partes"):
        split([_entry("-868.00")], "A", [Part(Decimal("868.00"), "casa/luz")], CATEGORIES, _ids())


def test_unknown_category_is_an_error() -> None:
    parts = [Part(Decimal("568.00"), "casa/inexistente"), Part(Decimal("300.00"), "casa/luz")]
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        split([_entry("-868.00")], "A", parts, CATEGORIES, _ids())


def test_zero_or_negative_part_is_an_error() -> None:
    parts = [Part(Decimal("968.00"), "casa/luz"), Part(Decimal("-100.00"), "casa/aluguel")]
    with pytest.raises(FinanceError, match="valor de parte inválido"):
        split([_entry("-868.00")], "A", parts, CATEGORIES, _ids())


def test_a_transfer_leg_cannot_be_split() -> None:
    entries = [_entry("-868.00", transfer_group="A")]
    parts = [Part(Decimal("576.00"), "casa/luz"), Part(Decimal("292.00"), "casa/aluguel")]
    with pytest.raises(FinanceError, match="perna de transferência"):
        split(entries, "A", parts, CATEGORIES, _ids())


def test_unknown_entry_is_an_error() -> None:
    parts = [Part(Decimal("576.00"), "casa/luz"), Part(Decimal("292.00"), "casa/aluguel")]
    with pytest.raises(FinanceError, match="não encontrado"):
        split([_entry("-868.00")], "Z", parts, CATEGORIES, _ids())
