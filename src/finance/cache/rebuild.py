"""Rebuild the SQLite cache from data/ (yaml + ledger CSVs)."""

import sqlite3
from pathlib import Path

from finance.cache.schema import SCHEMA
from finance.config.budget import Budget
from finance.ledger.csv_io import COLUMNS, entry_to_row
from finance.ledger.store import LedgerStore
from finance.model.account import Account
from finance.model.money import format_amount

YEAR_MONTH_FORMAT = "%Y-%m"
_ENTRY_COLUMNS = (*COLUMNS, "year_month")
_ENTRY_SQL = (
    f"insert into entries ({', '.join(_ENTRY_COLUMNS)}) "
    f"values ({', '.join('?' for _ in _ENTRY_COLUMNS)})"
)


def rebuild(data_root: Path, db_path: Path, accounts: dict[str, Account], budget: Budget) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    entries = LedgerStore(data_root).load_all()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            _ENTRY_SQL,
            [
                (*(entry_to_row(e)[c] for c in COLUMNS), e.date.strftime(YEAR_MONTH_FORMAT))
                for e in entries
            ],
        )
        conn.executemany(
            "insert into accounts values (?, ?, ?, ?, ?, ?)",
            [
                (a.id, a.name, a.bank, a.type.value, a.closing_day, a.due_day)
                for a in accounts.values()
            ],
        )
        conn.executemany(
            "insert into budget values (?, ?)",
            [(category, format_amount(amount)) for category, amount in budget.general.items()],
        )
    return len(entries)
