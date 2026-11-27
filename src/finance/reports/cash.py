"""Cash view: the money that actually went in and out of each checking account.

Diferente do `report month`, que é competência: aqui a compra no cartão não conta
no mês da compra, quem conta é o pagamento da fatura saindo da conta. Por isso
perna de transferência ENTRA — o dinheiro saiu da conta de verdade.

O saldo só aparece pra conta que declarou `opening_balance`/`opening_date` em
`accounts.yaml`; sem isso dá pra somar o movimento, mas não dá pra dizer saldo.
"""

import sqlite3
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.model.account import Account, AccountType
from finance.reports.sums import ZERO, query_sum


@dataclass(frozen=True)
class CashLine:
    account_id: str
    name: str
    opening: Decimal | None
    income: Decimal
    outflow: Decimal
    movement: Decimal
    closing: Decimal | None


@dataclass(frozen=True)
class CashReport:
    year: int
    month: int
    group: str | None
    lines: list[CashLine]
    income: Decimal
    outflow: Decimal
    movement: Decimal
    opening: Decimal | None
    closing: Decimal | None
    accounts_without_opening: list[str]


def month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def cash_report(
    conn: sqlite3.Connection, accounts: dict[str, Account], year: int, month: int, group: str | None
) -> CashReport:
    start, end = month_bounds(year, month)
    lines = [
        _line(conn, account, start, end)
        for account in accounts.values()
        if account.type is AccountType.CHECKING
    ]
    lines.sort(key=lambda line: line.name)
    missing = [line.account_id for line in lines if line.opening is None]
    income = sum((line.income for line in lines), ZERO)
    outflow = sum((line.outflow for line in lines), ZERO)
    opening = None if missing else sum((line.opening or ZERO for line in lines), ZERO)
    return CashReport(
        year=year,
        month=month,
        group=group,
        lines=lines,
        income=income,
        outflow=outflow,
        movement=income - outflow,
        opening=opening,
        closing=None if opening is None else opening + income - outflow,
        accounts_without_opening=missing,
    )


def _line(conn: sqlite3.Connection, account: Account, start: date, end: date) -> CashLine:
    income = query_sum(
        conn,
        "select amount from entries where account = ? and date between ? and ? and amount > 0",
        (account.id, start.isoformat(), end.isoformat()),
    )
    outflow = -query_sum(
        conn,
        "select amount from entries where account = ? and date between ? and ? and amount < 0",
        (account.id, start.isoformat(), end.isoformat()),
    )
    opening = balance_before(conn, account, start)
    return CashLine(
        account_id=account.id,
        name=account.name,
        opening=opening,
        income=income,
        outflow=outflow,
        movement=income - outflow,
        closing=None if opening is None else opening + income - outflow,
    )


def balance_before(conn: sqlite3.Connection, account: Account, day: date) -> Decimal | None:
    """O saldo da conta na véspera de `day`, ou None se ela não tem saldo inicial declarado."""
    if account.opening_balance is None or account.opening_date is None:
        return None
    moved = query_sum(
        conn,
        "select amount from entries where account = ? and date >= ? and date < ?",
        (account.id, account.opening_date.isoformat(), day.isoformat()),
    )
    return account.opening_balance + moved


def balance_now(conn: sqlite3.Connection, account: Account) -> Decimal | None:
    """O saldo da conta hoje, contando tudo que está no ledger."""
    if account.opening_balance is None or account.opening_date is None:
        return None
    moved = query_sum(
        conn,
        "select amount from entries where account = ? and date >= ?",
        (account.id, account.opening_date.isoformat()),
    )
    return account.opening_balance + moved
