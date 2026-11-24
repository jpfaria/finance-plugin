"""Build manual ledger entries from a user request (installments included)."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, Decimal

from finance.model.account import Account
from finance.model.dates import add_months
from finance.model.entry import CategorySource, Entry, Status
from finance.model.errors import FinanceError
from finance.model.money import CENTS

MANUAL_SOURCE = "manual"


@dataclass(frozen=True)
class AddRequest:
    account: Account
    amount: Decimal
    date: date
    description: str
    category: str
    tags: tuple[str, ...]
    installments: int


def split_installments(total: Decimal, count: int) -> list[Decimal]:
    if count < 1:
        raise FinanceError(f"número de parcelas inválido: {count}")
    base = (total / count).quantize(CENTS, rounding=ROUND_DOWN)
    parts = [base] * count
    parts[-1] = total - base * (count - 1)
    return parts


def build_manual_entries(
    req: AddRequest, categories: frozenset[str], ids: Iterator[str]
) -> list[Entry]:
    if req.category and req.category not in categories:
        raise FinanceError(f"categoria desconhecida: {req.category!r}")
    installed = req.installments > 1
    if installed and not req.account.is_credit:
        raise FinanceError("parcelas só existem em cartão de crédito")
    parts = split_installments(req.amount, req.installments)
    # A category typed on the command line is the user's own call, not a rule's:
    # `recategorize --force` must never replace it.
    category_source = CategorySource.MANUAL if req.category else CategorySource.NONE
    group = ""
    entries: list[Entry] = []
    for index, part in enumerate(parts):
        entry_id = next(ids)
        if installed and index == 0:
            group = entry_id
        entries.append(
            Entry(
                id=entry_id,
                date=add_months(req.date, index),
                account=req.account.id,
                amount=part,
                description=req.description,
                category=req.category,
                category_source=category_source,
                tags=req.tags,
                installment=f"{index + 1}/{req.installments}" if installed else "",
                installment_group=group,
                status=Status.MANUAL,
                source=MANUAL_SOURCE,
            )
        )
    return entries
