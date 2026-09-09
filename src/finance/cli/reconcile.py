"""`finance reconcile`: match manual entries against imported ones."""

from collections.abc import Sequence
from datetime import date
from typing import Annotated

import typer

from finance.actions.reconcile import merge
from finance.actions.reconcile import reconcile as reconcile_entries
from finance.cli.context import load_context, run
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.render.output import emit_json, emit_table

DEFAULT_WINDOW_DAYS = 3
DEFAULT_STALE_DAYS = 45
ENTRY_COLUMNS = ["data", "conta", "valor", "descrição"]


def reconcile(
    window: Annotated[int, typer.Option("--window", min=0, help="janela em dias")] = (
        DEFAULT_WINDOW_DAYS
    ),
    stale_days: Annotated[
        int, typer.Option("--stale-days", min=1, help="idade que torna um manual pendente")
    ] = DEFAULT_STALE_DAYS,
    as_json: Annotated[bool, typer.Option("--json", help="Saída em JSON")] = False,
) -> None:
    """Casa lançamentos manuais com os importados e relata as sobras."""

    def _go() -> None:
        ctx = load_context()
        store = LedgerStore(ctx.data_root)
        result = reconcile_entries(store.load_all(), window, stale_days, date.today())
        merged = [merge(m.manual, m.imported) for m in result.matches]
        store.replace(merged, removed_ids={m.imported.id for m in result.matches})
        if as_json:
            emit_json(
                {
                    "matched": len(result.matches),
                    "unmatched_imported": result.unmatched_imported,
                    "stale_manual": result.stale_manual,
                }
            )
            return
        typer.echo(f"conciliados: {len(result.matches)}")
        _table("Importados sem par", result.unmatched_imported)
        _table("Manuais antigos sem par", result.stale_manual)

    run(_go)


def _table(title: str, entries: Sequence[Entry]) -> None:
    if not entries:
        return
    emit_table(
        title,
        ENTRY_COLUMNS,
        [[e.date, e.account, e.amount, e.description] for e in entries],
    )
