from datetime import date

from finance.reports.invoice_period import due_date, invoice_month_for, invoice_period


def test_period_is_prev_close_plus_one_to_close() -> None:
    assert invoice_period(2026, 9, 3) == (date(2026, 8, 4), date(2026, 9, 3))


def test_period_clamps_short_months() -> None:
    assert invoice_period(2026, 3, 31) == (date(2026, 3, 1), date(2026, 3, 31))
    assert invoice_period(2026, 2, 31) == (date(2026, 2, 1), date(2026, 2, 28))


def test_month_for_purchase_date() -> None:
    assert invoice_month_for(date(2026, 9, 3), 3) == (2026, 9)
    assert invoice_month_for(date(2026, 9, 4), 3) == (2026, 10)
    assert invoice_month_for(date(2026, 12, 20), 3) == (2027, 1)


def test_due_date() -> None:
    assert due_date(2026, 9, 10) == date(2026, 9, 10)
