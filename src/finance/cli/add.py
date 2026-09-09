"""`finance add`: record manual entries."""

from datetime import date
from typing import Annotated

import typer

from finance.actions.add import AddRequest, build_manual_entries
from finance.cli.context import load_context, resolve_account, run
from finance.ledger.ids import new_id
from finance.ledger.store import LedgerStore
from finance.model.money import parse_amount

TAG_LIST_SEPARATOR = ","


def add(
    account: Annotated[str, typer.Option("--account", help="id ou parte do nome da conta")],
    amount: Annotated[str, typer.Option("--amount", help="negativo = saída, positivo = entrada")],
    desc: Annotated[str, typer.Option("--desc")],
    date_text: Annotated[
        str | None, typer.Option("--date", help="AAAA-MM-DD, default hoje")
    ] = None,
    category: Annotated[str, typer.Option("--category")] = "",
    installments: Annotated[int, typer.Option("--installments", min=1)] = 1,
    tags: Annotated[str, typer.Option("--tags", help="separadas por vírgula")] = "",
) -> None:
    """Grava um lançamento manual (parcelado ou não)."""

    def _go() -> None:
        ctx = load_context()
        req = AddRequest(
            account=resolve_account(ctx, account),
            amount=parse_amount(amount),
            date=date.fromisoformat(date_text) if date_text else date.today(),
            description=desc,
            category=category,
            tags=tuple(t.strip() for t in tags.split(TAG_LIST_SEPARATOR) if t.strip()),
            installments=installments,
        )
        entries = build_manual_entries(req, ctx.categories, iter(new_id, None))
        LedgerStore(ctx.data_root).append(entries)
        ids = ", ".join(e.id for e in entries)
        typer.echo(f"{len(entries)} lançamento(s) gravado(s): {ids}")

    run(_go)
