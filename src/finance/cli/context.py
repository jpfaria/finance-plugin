"""Resolve data/cache dirs from the environment, load config once, map FinanceError to exit 1."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import typer

from finance.config.accounts import accounts_in_group, load_accounts
from finance.config.budget import Budget, load_budget
from finance.config.categories import load_categories
from finance.model.account import Account
from finance.model.errors import FinanceError

DATA_DIR_ENV = "FINANCE_DATA_DIR"
CACHE_DIR_ENV = "FINANCE_CACHE_DIR"
DEFAULT_DATA_DIR = "data"
DEFAULT_CACHE_DIR = ".cache"


@dataclass(frozen=True)
class Context:
    data_root: Path
    cache_root: Path
    accounts: dict[str, Account]
    categories: frozenset[str]
    budget: Budget


def resolve_dirs() -> tuple[Path, Path]:
    data_root = Path(os.environ.get(DATA_DIR_ENV, DEFAULT_DATA_DIR))
    cache_root = Path(os.environ.get(CACHE_DIR_ENV, DEFAULT_CACHE_DIR))
    return data_root, cache_root


def load_context() -> Context:
    data_root, cache_root = resolve_dirs()
    categories = load_categories(data_root / "categories.yaml")
    return Context(
        data_root=data_root,
        cache_root=cache_root,
        accounts=load_accounts(data_root / "accounts.yaml"),
        categories=categories,
        budget=load_budget(data_root / "budget.yaml", categories),
    )


def resolve_account(ctx: Context, text: str) -> Account:
    if text in ctx.accounts:
        return ctx.accounts[text]
    needle = text.strip().lower()
    matches = [a for a in ctx.accounts.values() if needle in a.name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FinanceError(f"conta desconhecida: {text!r}")
    names = ", ".join(a.id for a in matches)
    raise FinanceError(f"conta ambígua: {text!r} casa com {names}")


def resolve_group(ctx: Context, group: str | None) -> dict[str, Account]:
    """Accounts in `group`; every account when `group` is None. Unknown group is an error."""
    if group is None:
        return ctx.accounts
    selected = accounts_in_group(ctx.accounts, group)
    if not selected:
        known = ", ".join(sorted({a.group for a in ctx.accounts.values() if a.group})) or "nenhum"
        raise FinanceError(f"grupo desconhecido: {group!r}. Grupos declarados: {known}")
    return selected


def run(fn: Callable[[], None]) -> None:
    try:
        fn()
    except FinanceError as exc:
        typer.echo(f"erro: {exc}", err=True)
        raise typer.Exit(1) from exc
