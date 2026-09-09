"""Calendar helpers: month arithmetic and YYYY-MM parsing."""

import calendar
import re
from datetime import date

from finance.model.errors import FinanceError

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def clamp_day(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def add_months(d: date, n: int) -> date:
    index = d.year * 12 + (d.month - 1) + n
    year, month0 = divmod(index, 12)
    return clamp_day(year, month0 + 1, d.day)


def parse_month(text: str) -> tuple[int, int]:
    match = _MONTH_RE.match(text.strip())
    if not match:
        raise FinanceError(f"mês inválido: {text!r} (use AAAA-MM)")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise FinanceError(f"mês inválido: {text!r} (use AAAA-MM)")
    return year, month
