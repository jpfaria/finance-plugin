import os
import sqlite3
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.cache.connection import is_stale, open_db
from finance.cache.rebuild import rebuild
from finance.config.accounts import load_accounts
from finance.config.budget import Budget
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry


def _e(id_: str, d: date, amount: str) -> Entry:
    return Entry(id=id_, date=d, account="nu", amount=Decimal(amount), description=id_)


def _seed(data_root: Path) -> None:
    LedgerStore(data_root).append(
        [_e("A", date(2026, 9, 1), "-10.00"), _e("B", date(2026, 10, 1), "20.00")]
    )


def test_rebuild_loads_entries_accounts_budget(data_root: Path, cache_root: Path) -> None:
    _seed(data_root)
    accounts = load_accounts(data_root / "accounts.yaml")
    db = cache_root / "finance.db"
    n = rebuild(data_root, db, accounts, Budget(general={"casa/luz": Decimal("250.00")}))
    assert n == 2
    conn = sqlite3.connect(db)
    assert conn.execute("select count(*) from entries").fetchone()[0] == 2
    assert conn.execute("select year_month from entries where id='B'").fetchone()[0] == "2026-10"
    assert conn.execute("select count(*) from accounts").fetchone()[0] == 3
    assert conn.execute("select amount from budget where category='casa/luz'").fetchone()[0] == (
        "250.00"
    )


def test_open_db_rebuilds_when_stale(data_root: Path, cache_root: Path) -> None:
    _seed(data_root)
    accounts = load_accounts(data_root / "accounts.yaml")
    db = cache_root / "finance.db"
    assert is_stale(data_root, db)
    conn = open_db(data_root, cache_root, accounts, Budget())
    assert conn.execute("select count(*) from entries").fetchone()[0] == 2
    conn.close()
    assert not is_stale(data_root, db)
    LedgerStore(data_root).append([_e("C", date(2026, 9, 3), "-1.00")])
    future = time.time() + 5
    os.utime(data_root / "ledger" / "2026-09.csv", (future, future))
    assert is_stale(data_root, db)
    conn = open_db(data_root, cache_root, accounts, Budget())
    assert conn.execute("select count(*) from entries").fetchone()[0] == 3
