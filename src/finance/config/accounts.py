"""Load accounts.yaml into Account objects."""

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from finance.model.account import Account, AccountType
from finance.model.errors import FinanceError
from finance.model.money import CENTS


def load_accounts(path: Path) -> dict[str, Account]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = raw.get("accounts") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        raise FinanceError(f"{path}: esperado uma lista em 'accounts'")
    accounts: dict[str, Account] = {}
    for item in items:
        account = _parse(item, path)
        if account.id in accounts:
            raise FinanceError(f"{path}: id de conta duplicado: {account.id!r}")
        accounts[account.id] = account
    return accounts


def _parse(item: Any, path: Path) -> Account:
    if not isinstance(item, dict):
        raise FinanceError(f"{path}: conta inválida: {item!r}")
    try:
        account = Account(
            id=str(item["id"]),
            name=str(item["name"]),
            bank=str(item["bank"]),
            type=AccountType(str(item["type"])),
            closing_day=_optional_day(item.get("closing_day")),
            due_day=_optional_day(item.get("due_day")),
            group=str(item.get("group", "")).strip(),
            opening_balance=_optional_amount(item.get("opening_balance")),
            opening_date=_optional_date(item.get("opening_date")),
        )
    except (KeyError, ValueError) as exc:
        raise FinanceError(f"{path}: conta inválida: {item!r} ({exc})") from exc
    if account.is_credit and (account.closing_day is None or account.due_day is None):
        raise FinanceError(f"{path}: cartão {account.id!r} precisa de closing_day e due_day")
    if (account.opening_balance is None) != (account.opening_date is None):
        raise FinanceError(
            f"{path}: conta {account.id!r}: opening_balance e opening_date andam juntos"
        )
    return account


def accounts_in_group(accounts: dict[str, Account], group: str | None) -> dict[str, Account]:
    if group is None:
        return accounts
    return {i: a for i, a in accounts.items() if a.group == group}


def _optional_amount(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(CENTS)
    except InvalidOperation as exc:
        raise ValueError(f"saldo inválido: {value!r}") from exc


def _optional_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _optional_day(value: Any) -> int | None:
    if value is None:
        return None
    day = int(value)
    if not 1 <= day <= 31:
        raise ValueError(f"dia fora de 1..31: {day}")
    return day
