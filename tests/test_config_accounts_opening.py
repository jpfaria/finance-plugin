"""Saldo inicial em accounts.yaml: é ele que transforma movimento em saldo de banco."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.config.accounts import load_accounts
from finance.model.errors import FinanceError


def _write(tmp_path: Path, line: str) -> Path:
    p = tmp_path / "accounts.yaml"
    p.write_text(f"accounts:\n  - {line}\n", encoding="utf-8")
    return p


def test_opening_balance_and_date_are_read(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "{id: bra, name: B, bank: bradesco, type: checking, "
        "opening_balance: -3675.37, opening_date: 2026-09-28}",
    )
    account = load_accounts(p)["bra"]
    assert account.opening_balance == Decimal("-3675.37")
    assert account.opening_date == date(2026, 9, 28)
    assert account.has_opening is True


def test_an_account_without_them_has_no_opening(tmp_path: Path) -> None:
    account = load_accounts(_write(tmp_path, "{id: a, name: A, bank: nubank, type: checking}"))["a"]
    assert account.opening_balance is None
    assert account.has_opening is False


def test_one_without_the_other_is_an_error(tmp_path: Path) -> None:
    p = _write(tmp_path, "{id: a, name: A, bank: nubank, type: checking, opening_balance: 10}")
    with pytest.raises(FinanceError, match="andam juntos"):
        load_accounts(p)


def test_a_broken_date_is_an_error(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "{id: a, name: A, bank: nubank, type: checking, "
        "opening_balance: 10, opening_date: '28/09/2026'}",
    )
    with pytest.raises(FinanceError, match="conta inválida"):
        load_accounts(p)
