"""`finance rebuild`: regenerate the SQLite cache from data/."""

import typer

from finance.cache.connection import DB_NAME
from finance.cache.rebuild import rebuild as rebuild_cache
from finance.cli.context import load_context, run


def rebuild() -> None:
    """Recria .cache/finance.db a partir de data/."""

    def _go() -> None:
        ctx = load_context()
        db_path = ctx.cache_root / DB_NAME
        n = rebuild_cache(ctx.data_root, db_path, ctx.accounts, ctx.budget)
        typer.echo(f"cache reconstruído: {n} lançamento(s) em {db_path}")

    run(_go)
