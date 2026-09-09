"""Load accounts.yaml into Account objects."""

from pathlib import Path
from typing import Any

import yaml

from finance.model.account import Account, AccountType
from finance.model.errors import FinanceError


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
        )
    except (KeyError, ValueError) as exc:
        raise FinanceError(f"{path}: conta inválida: {item!r} ({exc})") from exc
    if account.is_credit and (account.closing_day is None or account.due_day is None):
        raise FinanceError(f"{path}: cartão {account.id!r} precisa de closing_day e due_day")
    return account


def _optional_day(value: Any) -> int | None:
    if value is None:
        return None
    day = int(value)
    if not 1 <= day <= 31:
        raise ValueError(f"dia fora de 1..31: {day}")
    return day
