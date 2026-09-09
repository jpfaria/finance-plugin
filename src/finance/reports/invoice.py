"""One credit-card invoice: its lines and totals."""

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.model.account import Account
from finance.model.errors import FinanceError
from finance.reports.invoice_period import due_date, invoice_period
from finance.reports.sums import sum_amounts


@dataclass(frozen=True)
class InvoiceLine:
    id: str
    date: date
    description: str
    amount: Decimal
    category: str
    installment: str
    status: str


@dataclass(frozen=True)
class Invoice:
    account_id: str
    year: int
    month: int
    start: date
    end: date
    due: date
    lines: list[InvoiceLine]
    purchases: Decimal
    payments: Decimal
    total_due: Decimal


def invoice(conn: sqlite3.Connection, account: Account, year: int, month: int) -> Invoice:
    if not account.is_credit or account.closing_day is None or account.due_day is None:
        raise FinanceError(f"conta {account.id!r} não é cartão de crédito")
    start, end = invoice_period(year, month, account.closing_day)
    rows = conn.execute(
        "select id, date, description, amount, category, installment, status, transfer_group "
        "from entries where account = ? and date between ? and ? order by date, id",
        (account.id, start.isoformat(), end.isoformat()),
    ).fetchall()
    lines = [
        InvoiceLine(
            id=r["id"],
            date=date.fromisoformat(r["date"]),
            description=r["description"],
            amount=Decimal(r["amount"]),
            category=r["category"],
            installment=r["installment"],
            status=r["status"],
        )
        for r in rows
    ]
    purchases = -sum_amounts(r for r in rows if _is_purchase(r))
    payments = sum_amounts(r for r in rows if _is_payment(r))
    return Invoice(
        account_id=account.id,
        year=year,
        month=month,
        start=start,
        end=end,
        due=due_date(year, month, account.due_day),
        lines=lines,
        purchases=purchases,
        payments=payments,
        total_due=-sum_amounts(rows),
    )


def _is_purchase(row: sqlite3.Row) -> bool:
    return Decimal(row["amount"]) < 0 and not row["transfer_group"]


def _is_payment(row: sqlite3.Row) -> bool:
    return Decimal(row["amount"]) > 0 and bool(row["transfer_group"])
