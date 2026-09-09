"""`finance categorize`: list uncategorized entries and assign categories."""

from typing import Annotated

import typer

from finance.actions.categorize import pending, set_category
from finance.cli.context import load_context, run
from finance.config.rules import Rule, append_rule
from finance.ledger.store import LedgerStore
from finance.model.dates import parse_month
from finance.render.output import emit_json, emit_table

categorize_app = typer.Typer(
    no_args_is_help=False, invoke_without_command=True, help="Categorização de pendentes."
)

RULES_FILE = "rules.yaml"


@categorize_app.callback()
def list_pending(
    ctx: typer.Context,
    month: Annotated[str | None, typer.Option("--month", help="AAAA-MM")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Saída em JSON")] = False,
) -> None:
    """Lista os lançamentos sem categoria."""
    if ctx.invoked_subcommand is not None:
        return

    def _go() -> None:
        context = load_context()
        year, m = parse_month(month) if month else (None, None)
        rows = pending(LedgerStore(context.data_root).load_all(), year, m)
        if as_json:
            emit_json(
                [
                    {
                        "id": e.id,
                        "date": e.date,
                        "account": e.account,
                        "amount": e.amount,
                        "description": e.description,
                    }
                    for e in rows
                ]
            )
            return
        emit_table(
            "Sem categoria",
            ["id", "data", "conta", "valor", "descrição"],
            [[e.id, e.date, e.account, e.amount, e.description] for e in rows],
        )

    run(_go)


@categorize_app.command("set")
def set_one(
    entry_id: Annotated[str, typer.Argument(help="id do lançamento")],
    category: Annotated[str, typer.Argument(help="caminho da categoria")],
    rule: Annotated[str | None, typer.Option("--rule", help="regex a gravar em rules.yaml")] = None,
) -> None:
    """Aplica uma categoria e, opcionalmente, grava a regra."""

    def _go() -> None:
        context = load_context()
        store = LedgerStore(context.data_root)
        updated = set_category(store.load_all(), entry_id, category, context.categories)
        store.replace([updated], removed_ids=set())
        if rule:
            append_rule(context.data_root / RULES_FILE, Rule(rule, category))
        suffix = f" (regra gravada: {rule})" if rule else ""
        typer.echo(f"categoria aplicada: {category}{suffix}")

    run(_go)
