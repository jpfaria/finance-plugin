from datetime import date
from decimal import Decimal

from finance.model.account import Account, AccountType
from finance.model.entry import Entry, Status


def test_account_is_credit() -> None:
    card = Account(
        id="nu-card",
        name="Nubank cartão",
        bank="nubank",
        type=AccountType.CREDIT,
        closing_day=3,
        due_day=10,
    )
    conta = Account(id="nu", name="Nubank conta", bank="nubank", type=AccountType.CHECKING)
    assert card.is_credit
    assert not conta.is_credit


def test_entry_defaults_and_transfer_flag() -> None:
    e = Entry(
        id="01H", date=date(2026, 9, 1), account="nu", amount=Decimal("-50.00"), description="uber"
    )
    assert e.status is Status.MANUAL
    assert e.source == "manual"
    assert e.category == ""
    assert e.tags == ()
    assert not e.is_transfer
    t = Entry(
        id="01J",
        date=date(2026, 9, 1),
        account="nu",
        amount=Decimal("-500.00"),
        description="fatura",
        transfer_group="G1",
    )
    assert t.is_transfer
