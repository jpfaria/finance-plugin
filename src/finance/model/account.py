"""Account: a checking account or a credit card."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class AccountType(StrEnum):
    CHECKING = "checking"
    CREDIT = "credit"


@dataclass(frozen=True)
class Account:
    """`opening_balance` é o saldo da conta ANTES de qualquer lançamento de `opening_date`.

    É o que o extrato mostrava na véspera do primeiro lançamento importado. Sem ele,
    os relatórios só sabem somar movimento — o saldo que imprimem não é o do banco.
    """

    id: str
    name: str
    bank: str
    type: AccountType
    closing_day: int | None = None
    due_day: int | None = None
    group: str = ""
    opening_balance: Decimal | None = None
    opening_date: date | None = None

    @property
    def is_credit(self) -> bool:
        return self.type is AccountType.CREDIT

    @property
    def has_opening(self) -> bool:
        return self.opening_balance is not None and self.opening_date is not None
