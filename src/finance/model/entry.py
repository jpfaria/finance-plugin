"""Entry: one ledger line (a purchase, income, or one leg of a transfer)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Status(StrEnum):
    MANUAL = "manual"
    CONFIRMED = "confirmed"


class CategorySource(StrEnum):
    """Where `Entry.category` came from — what `finance recategorize` may overwrite.

    NONE: no category yet. RULE: applied by `rules.yaml` (on import or on
    recategorize), so a later run of the rules may replace it. MANUAL: the user
    chose it by hand (`categorize set`, `add --category`); no run of the rules ever
    touches it, `--force` included.
    """

    NONE = ""
    RULE = "rule"
    MANUAL = "manual"


@dataclass(frozen=True)
class Entry:
    id: str
    date: date
    account: str
    amount: Decimal
    description: str
    category: str = ""
    category_source: CategorySource = CategorySource.NONE
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
