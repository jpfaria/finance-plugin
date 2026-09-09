"""Decimal parsing and formatting for BRL amounts."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from finance.model.errors import FinanceError

CENTS = Decimal("0.01")


def parse_amount(text: str) -> Decimal:
    raw = text.strip().replace("R$", "").replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw).quantize(CENTS, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise FinanceError(f"valor inválido: {text!r}") from exc


def format_amount(value: Decimal) -> str:
    return f"{value.quantize(CENTS, rounding=ROUND_HALF_UP):.2f}"
