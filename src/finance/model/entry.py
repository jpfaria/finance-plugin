"""Entry: one ledger line (a purchase, income, or one leg of a transfer)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Status(StrEnum):
    MANUAL = "manual"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class Entry:
    id: str
    date: date
    account: str
    amount: Decimal
    description: str
    category: str = ""
    tags: tuple[str, ...] = ()
    installment: str = ""
    installment_group: str = ""
    transfer_group: str = ""
    status: Status = Status.MANUAL
    source: str = "manual"
    import_hash: str = ""

    @property
    def is_transfer(self) -> bool:
        return self.transfer_group != ""
