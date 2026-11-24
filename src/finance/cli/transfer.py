"""`finance transfer`: marca as pernas de uma transferência pra ela sair dos relatórios."""

from typing import Annotated

import typer

from finance.actions.transfer import DEFAULT_WINDOW_DAYS, candidates, clear, link
from finance.cli.context import load_context, run
from finance.ledger.store import LedgerStore
from finance.render.output import emit_json, emit_table

transfer_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help="Transferências: dinheiro que só muda de lugar.",
)


@transfer_app.callback()
def list_candidates(
    ctx: typer.Context,
    days: Annotated[
        int, typer.Option("--days", help="janela entre as duas pernas")
    ] = DEFAULT_WINDOW_DAYS,
    as_json: Annotated[bool, typer.Option("--json", help="Saída em JSON")] = False,
) -> None:
    """Lista os pares que parecem transferência e ainda não estão marcados."""
    if ctx.invoked_subcommand is not None:
        return

    def _go() -> None:
        context = load_context()
        rows = candidates(LedgerStore(context.data_root).load_all(), window_days=days)
        if as_json:
            emit_json(
                [
                    {
                        "ids": [c.out_leg.id, c.in_leg.id],
                        "amount": abs(c.out_leg.amount),
                        "days_apart": c.days_apart,
                        "out": {
                            "id": c.out_leg.id,
                            "date": c.out_leg.date,
                            "account": c.out_leg.account,
                            "description": c.out_leg.description,
                        },
                        "in": {
                            "id": c.in_leg.id,
                            "date": c.in_leg.date,
                            "account": c.in_leg.account,
                            "description": c.in_leg.description,
                        },
                    }
                    for c in rows
                ]
            )
            return
        emit_table(
            "Candidatos a transferência",
            ["valor", "saída", "entrada", "ids"],
            [
                [
                    abs(c.out_leg.amount),
                    f"{c.out_leg.date} {c.out_leg.account} {c.out_leg.description}",
                    f"{c.in_leg.date} {c.in_leg.account} {c.in_leg.description}",
                    f"{c.out_leg.id} {c.in_leg.id}",
                ]
                for c in rows
            ],
        )

    run(_go)


@transfer_app.command("set")
def set_transfer(
    entry_ids: Annotated[list[str], typer.Argument(help="ids das pernas")],
    force: Annotated[
        bool, typer.Option("--force", help="aceita perna sozinha (soma diferente de zero)")
    ] = False,
) -> None:
    """Marca os lançamentos como as pernas de uma mesma transferência."""

    def _go() -> None:
        context = load_context()
        store = LedgerStore(context.data_root)
        updated = link(store.load_all(), entry_ids, force=force)
        store.replace(updated, removed_ids=set())
        typer.echo(
            f"transferência marcada: {len(updated)} perna(s), grupo {updated[0].transfer_group}"
        )

    run(_go)


@transfer_app.command("clear")
def clear_transfer(
    entry_ids: Annotated[list[str], typer.Argument(help="ids das pernas")],
) -> None:
    """Tira a marca de transferência dos lançamentos."""

    def _go() -> None:
        context = load_context()
        store = LedgerStore(context.data_root)
        updated = clear(store.load_all(), entry_ids)
        store.replace(updated, removed_ids=set())
        typer.echo(f"marca removida: {len(updated)} lançamento(s)")

    run(_go)
