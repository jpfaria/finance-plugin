"""Account: a checking account or a credit card."""

from dataclasses import dataclass
from enum import StrEnum


class AccountType(StrEnum):
    CHECKING = "checking"
    CREDIT = "credit"


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    bank: str
    type: AccountType
    closing_day: int | None = None
    due_day: int | None = None
    group: str = ""

    @property
    def is_credit(self) -> bool:
        return self.type is AccountType.CREDIT
