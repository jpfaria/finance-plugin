"""Turn report dataclasses into JSON or a rich table."""

import dataclasses
import json
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import typer
from rich.console import Console
from rich.table import Table

from finance.model.money import format_amount

EMPTY_CELL = "-"
TABLE_WIDTH = 120


def to_jsonable(obj: object) -> object:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Decimal):
        return format_amount(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, list | tuple):
        return [to_jsonable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    return obj


def emit_json(obj: object) -> None:
    typer.echo(json.dumps(to_jsonable(obj), ensure_ascii=False, indent=2))


def _cell(value: object) -> str:
    if value is None:
        return EMPTY_CELL
    if isinstance(value, Decimal):
        return format_amount(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def emit_table(title: str, columns: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*(_cell(v) for v in row))
    Console(width=TABLE_WIDTH).print(table)
