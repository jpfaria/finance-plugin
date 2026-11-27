"""`finance split`: divide uma cobrança em partes com categorias diferentes."""

from typing import Annotated

import typer

from finance.actions.split import Part, split
from finance.cli.context import load_context, run
from finance.ledger.ids import new_id
from finance.ledger.store import LedgerStore
from finance.model.errors import FinanceError
from finance.model.money import parse_amount

PART_SEPARATOR = ":"


def split_entry(
    entry_id: Annotated[str, typer.Argument(help="id do lançamento")],
    parts: Annotated[
        list[str], typer.Option("--part", help="valor:categoria (repita para cada parte)")
    ],
) -> None:
    """Rateia um lançamento em partes que somam o mesmo valor."""

    def _go() -> None:
        ctx = load_context()
        store = LedgerStore(ctx.data_root)
        pieces = [_part(text) for text in parts]
        new = split(store.load_all(), entry_id, pieces, ctx.categories, iter(new_id, None))
        store.replace(new[:1], removed_ids=set())
        store.append(new[1:])
        typer.echo(f"rateado em {len(new)} parte(s): " + ", ".join(e.id for e in new))

    run(_go)


def _part(text: str) -> Part:
    value, separator, category = text.partition(PART_SEPARATOR)
    if not separator:
        raise FinanceError(f"parte sem categoria: {text!r} (use valor:categoria)")
    return Part(amount=parse_amount(value), category=category.strip())
