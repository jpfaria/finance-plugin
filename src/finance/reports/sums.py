"""Decimal sums over cache rows (SQLite stores amounts as text)."""

import sqlite3
from collections.abc import Iterable
from decimal import Decimal

ZERO = Decimal("0.00")


def sum_amounts(rows: Iterable[sqlite3.Row]) -> Decimal:
    return sum((Decimal(row["amount"]) for row in rows), ZERO)


def query_sum(conn: sqlite3.Connection, sql: str, params: tuple[object, ...]) -> Decimal:
    return sum_amounts(conn.execute(sql, params).fetchall())
