"""Monthly cash-flow summary: income, expenses by category vs budget."""

import sqlite3
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from finance.model.entry import Status
from finance.reports.sums import ZERO

UNCATEGORIZED = "(sem categoria)"
PCT_PLACES = Decimal("0.1")


@dataclass(frozen=True)
class CategoryLine:
    category: str
    spent: Decimal
    budget: Decimal | None
    pct: str | None


@dataclass(frozen=True)
class MonthSummary:
    year: int
    month: int
    group: str | None
    income: Decimal
    expenses: Decimal
    net: Decimal
    lines: list[CategoryLine]
    uncategorized: int
    pending_manual: int


def month_summary(
    conn: sqlite3.Connection,
    year: int,
    month: int,
    budget: dict[str, Decimal],
    accounts: set[str] | None = None,
    group: str | None = None,
) -> MonthSummary:
    rows = [
        row
        for row in conn.execute(
            "select amount, category, status, account from entries "
            "where year_month = ? and transfer_group = ''",
            (f"{year:04d}-{month:02d}",),
        ).fetchall()
        if accounts is None or row["account"] in accounts
    ]
    income = ZERO
    spent_by_category: dict[str, Decimal] = dict.fromkeys(budget, ZERO)
    uncategorized = 0
    pending_manual = 0
    for row in rows:
        amount = Decimal(row["amount"])
        if row["status"] == Status.MANUAL.value:
            pending_manual += 1
        if amount > 0:
            income += amount
            continue
        if not row["category"]:
            uncategorized += 1
        category = row["category"] or UNCATEGORIZED
        spent_by_category[category] = spent_by_category.get(category, ZERO) - amount
    lines = [
        CategoryLine(category, spent, budget.get(category), _pct(spent, budget.get(category)))
        for category, spent in spent_by_category.items()
    ]
    lines.sort(key=lambda line: (-line.spent, line.category))
    expenses = sum((line.spent for line in lines), ZERO)
    return MonthSummary(
        year,
        month,
        group,
        income,
        expenses,
        income - expenses,
        lines,
        uncategorized,
        pending_manual,
    )


def _pct(spent: Decimal, cap: Decimal | None) -> str | None:
    if cap is None or cap == 0:
        return None
    return str((spent / cap * 100).quantize(PCT_PLACES, rounding=ROUND_HALF_UP))
