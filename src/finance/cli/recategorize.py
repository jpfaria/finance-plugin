"""`finance recategorize`: reapply rules.yaml to entries already in data/ledger/."""

from typing import Annotated

import typer

from finance.actions.recategorize import reapply_rules
from finance.cli.context import load_context, resolve_group, run
from finance.config.rules import load_rules
from finance.ledger.store import LedgerStore
from finance.model.dates import parse_month

RULES_FILE = "rules.yaml"
NO_CATEGORY = "(sem categoria)"


def recategorize(
    month: Annotated[str | None, typer.Option("--month", help="AAAA-MM")] = None,
    group: Annotated[str | None, typer.Option("--group", help="grupo de contas")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="só mostra, não grava")] = False,
    force: Annotated[
        bool, typer.Option("--force", help="reavalia também categoria vinda de regra")
    ] = False,
) -> None:
    """Reaplica rules.yaml nos lançamentos já gravados (nunca em categoria manual)."""

    def _go() -> None:
        ctx = load_context()
        year, m = parse_month(month) if month else (None, None)
        account_ids = None if group is None else frozenset(resolve_group(ctx, group))
        store = LedgerStore(ctx.data_root)
        result = reapply_rules(
            store.load_all(),
            load_rules(ctx.data_root / RULES_FILE, ctx.categories),
            year=year,
            month=m,
            account_ids=account_ids,
            force=force,
        )
        for change in result.changes:
            entry = change.entry
            typer.echo(
                f"{entry.id}  {entry.date}  {entry.description}: "
                f"{change.before or NO_CATEGORY} -> {entry.category}"
            )
        if result.changes and not dry_run:
            store.replace([c.entry for c in result.changes], removed_ids=set())
        prefix = "dry-run: " if dry_run else ""
        typer.echo(
            f"{prefix}{len(result.changes)} recategorizado(s), {result.uncategorized} sem categoria"
        )

    run(_go)
