"""Which purchase dates fall into which credit-card invoice."""

from datetime import date, timedelta

from finance.model.dates import add_months, clamp_day


def invoice_period(year: int, month: int, closing_day: int) -> tuple[date, date]:
    end = clamp_day(year, month, closing_day)
    previous = add_months(date(year, month, 1), -1)
    start = clamp_day(previous.year, previous.month, closing_day) + timedelta(days=1)
    return start, end


def invoice_month_for(d: date, closing_day: int) -> tuple[int, int]:
    if d.day <= closing_day:
        return d.year, d.month
    following = add_months(date(d.year, d.month, 1), 1)
    return following.year, following.month


def due_date(year: int, month: int, due_day: int) -> date:
    return clamp_day(year, month, due_day)
