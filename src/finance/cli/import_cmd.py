"""`finance import`: read a statement file into the ledger."""

from pathlib import Path
from typing import Annotated

import typer

from finance.actions.import_statement import build_import_entries
from finance.cli.context import load_context, resolve_account, run
from finance.config.rules import load_rules
from finance.imports.registry import detect
from finance.ledger.ids import new_id
from finance.ledger.store import LedgerStore


def import_statement(
    path: Annotated[Path, typer.Argument(help="arquivo de extrato (OFX ou CSV)")],
    account: Annotated[str, typer.Option("--account", help="id ou parte do nome da conta")],
) -> None:
    """Importa um extrato, ignorando o que já foi importado antes."""

    def _go() -> None:
        ctx = load_context()
        acct = resolve_account(ctx, account)
        parser = detect(path)
        records = parser.parse(path)
        store = LedgerStore(ctx.data_root)
        existing = {e.import_hash for e in store.load_all() if e.import_hash}
        rules = load_rules(ctx.data_root / "rules.yaml", ctx.categories)
        result = build_import_entries(records, acct, path.name, existing, rules, iter(new_id, None))
        store.append(result.new)
        typer.echo(
            f"importados: {len(result.new)}, duplicados: {result.duplicates}, "
            f"sem categoria: {result.uncategorized}"
        )

    run(_go)
