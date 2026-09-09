"""Open the cache, rebuilding it whenever data/ is newer."""

import sqlite3
from decimal import Decimal
from pathlib import Path

from finance.cache.rebuild import rebuild
from finance.ledger.paths import ledger_files
from finance.model.account import Account

DB_NAME = "finance.db"
CONFIG_FILES = ("accounts.yaml", "categories.yaml", "budget.yaml", "rules.yaml")


def is_stale(data_root: Path, db_path: Path) -> bool:
    if not db_path.is_file():
        return True
    built = db_path.stat().st_mtime
    sources = [data_root / name for name in CONFIG_FILES] + ledger_files(data_root)
    return any(p.is_file() and p.stat().st_mtime > built for p in sources)


def open_db(
    data_root: Path, cache_root: Path, accounts: dict[str, Account], budget: dict[str, Decimal]
) -> sqlite3.Connection:
    db_path = cache_root / DB_NAME
    if is_stale(data_root, db_path):
        rebuild(data_root, db_path, accounts, budget)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
