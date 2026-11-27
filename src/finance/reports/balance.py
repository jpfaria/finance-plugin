"""Per-account balance and, for cards, the invoice currently open."""

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.model.account import Account
from finance.reports.cash import balance_now
from finance.reports.invoice_period import invoice_month_for, invoice_period
from finance.reports.sums import query_sum


@dataclass(frozen=True)
class AccountBalance:
    """`balance` é o saldo do banco quando a conta declarou saldo inicial.

    Sem `opening_balance` em `accounts.yaml` ele é só a soma do que foi importado —
    `real` diz qual dos dois você está lendo.
    """

    account_id: str
    name: str
    type: str
    balance: Decimal
    real: bool
    open_invoice: Decimal | None
    open_invoice_month: str | None


def account_balances(
    conn: sqlite3.Connection, accounts: dict[str, Account], today: date
) -> list[AccountBalance]:
    result: list[AccountBalance] = []
    for account in accounts.values():
        moved = query_sum(conn, "select amount from entries where account = ?", (account.id,))
        actual = balance_now(conn, account)
        balance = moved if actual is None else actual
        open_invoice: Decimal | None = None
        open_month: str | None = None
        if account.is_credit and account.closing_day is not None:
            year, month = invoice_month_for(today, account.closing_day)
            start, end = invoice_period(year, month, account.closing_day)
            in_period = query_sum(
                conn,
                "select amount from entries where account = ? and date between ? and ?",
                (account.id, start.isoformat(), end.isoformat()),
            )
            open_invoice = -in_period
            open_month = f"{year:04d}-{month:02d}"
        result.append(
            AccountBalance(
                account.id,
                account.name,
                account.type.value,
                balance,
                actual is not None,
                open_invoice,
                open_month,
            )
        )
    return result
