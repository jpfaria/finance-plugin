"""Forecast: what each category usually costs per month, from the months already closed.

A média é sempre sobre TODOS os meses da base, mesmo onde a categoria não apareceu:
gasto que só aconteceu uma vez em três meses entra como um terço. `months_present`
e `every_month` dizem em quantos meses a categoria apareceu, pra separar o que se
repete todo mês do que foi eventual.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from finance.model.dates import add_months
from finance.model.errors import FinanceError
from finance.reports.month import UNCATEGORIZED
from finance.reports.sums import ZERO

CENTS = Decimal("0.01")
DEFAULT_BASE_MONTHS = 3


@dataclass(frozen=True)
class ForecastLine:
    category: str
    per_month: list[Decimal]
    months_present: int
    average: Decimal
    every_month: bool


@dataclass(frozen=True)
class Forecast:
    target: str
    base: list[str]
    group: str | None
    income: Decimal
    expenses: Decimal
    net: Decimal
    lines: list[ForecastLine]
    income_by_month: dict[str, Decimal]
    expenses_by_month: dict[str, Decimal]


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def months_between(start: tuple[int, int], end: tuple[int, int]) -> list[str]:
    """Os meses de `start` a `end`, inclusive."""
    first = start[0] * 12 + start[1] - 1
    last = end[0] * 12 + end[1] - 1
    if last < first:
        raise FinanceError(f"intervalo invertido: {month_key(*start)} depois de {month_key(*end)}")
    keys = []
    for index in range(first, last + 1):
        year, month0 = divmod(index, 12)
        keys.append(month_key(year, month0 + 1))
    return keys


def base_before(year: int, month: int, count: int) -> list[str]:
    """Os `count` meses imediatamente anteriores a `year-month`."""
    if count < 1:
        raise FinanceError(f"a base precisa de pelo menos 1 mês: {count}")
    end = add_months(date(year, month, 1), -1)
    start = add_months(end, -(count - 1))
    return months_between((start.year, start.month), (end.year, end.month))


def forecast(
    conn: sqlite3.Connection,
    target: tuple[int, int],
    base: list[str],
    accounts: set[str] | None = None,
    group: str | None = None,
) -> Forecast:
    if not base:
        raise FinanceError("previsão precisa de pelo menos um mês de base")
    spent: dict[str, dict[str, Decimal]] = {}
    income_by_month: dict[str, Decimal] = dict.fromkeys(base, ZERO)
    placeholders = ",".join("?" for _ in base)
    rows = conn.execute(
        "select amount, category, year_month, account from entries "
        f"where transfer_group = '' and year_month in ({placeholders})",
        tuple(base),
    ).fetchall()
    for row in rows:
        if accounts is not None and row["account"] not in accounts:
            continue
        amount = Decimal(row["amount"])
        month = row["year_month"]
        if amount > 0:
            income_by_month[month] += amount
            continue
        category = row["category"] or UNCATEGORIZED
        spent.setdefault(category, dict.fromkeys(base, ZERO))[month] -= amount
    lines = [_line(category, by_month, base) for category, by_month in spent.items()]
    lines.sort(key=lambda line: (-line.average, line.category))
    expenses = sum((line.average for line in lines), ZERO)
    income = _average(sum(income_by_month.values(), ZERO), len(base))
    return Forecast(
        target=month_key(*target),
        base=base,
        group=group,
        income=income,
        expenses=expenses,
        net=income - expenses,
        lines=lines,
        income_by_month=income_by_month,
        expenses_by_month={
            month: sum((line.per_month[index] for line in lines), ZERO)
            for index, month in enumerate(base)
        },
    )


def _line(category: str, by_month: dict[str, Decimal], base: list[str]) -> ForecastLine:
    per_month = [by_month[month] for month in base]
    present = sum(1 for value in per_month if value != ZERO)
    return ForecastLine(
        category=category,
        per_month=per_month,
        months_present=present,
        average=_average(sum(per_month, ZERO), len(base)),
        every_month=present == len(base),
    )


def _average(total: Decimal, count: int) -> Decimal:
    return (total / count).quantize(CENTS, rounding=ROUND_HALF_UP)
