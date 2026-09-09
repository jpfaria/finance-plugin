"""`finance report *`: read-only views over the cache."""

from datetime import date
from typing import Annotated

import typer

from finance.cache.connection import open_db
from finance.cli.context import Context, load_context, resolve_account, resolve_group, run
from finance.model.dates import parse_month
from finance.render.output import emit_json, emit_table
from finance.reports.balance import account_balances
from finance.reports.invoice import invoice as build_invoice
from finance.reports.month import MonthSummary, month_summary

report_app = typer.Typer(no_args_is_help=True, help="Relatórios.")

MonthOpt = Annotated[str | None, typer.Option("--month", help="AAAA-MM, default mês atual")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Saída em JSON")]
GroupOpt = Annotated[
    str | None, typer.Option("--group", help="grupo de contas; sem a flag, agrega tudo")
]

CATEGORY_COLUMNS = ["categoria", "gasto", "orçamento", "%"]


def _scope(group: str | None) -> str:
    return f" — {group}" if group else ""


def _month(text: str | None) -> tuple[int, int]:
    if text is None:
        today = date.today()
        return today.year, today.month
    return parse_month(text)


def _summary(ctx: Context, month: str | None, group: str | None) -> MonthSummary:
    year, m = _month(month)
    selected = resolve_group(ctx, group)
    conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
    return month_summary(
        conn,
        year,
        m,
        ctx.budget.limits(group),
        accounts=None if group is None else set(selected),
        group=group,
    )


@report_app.command("month")
def month(month: MonthOpt = None, group: GroupOpt = None, as_json: JsonOpt = False) -> None:
    """Receitas, despesas por categoria vs orçamento e saldo do mês."""

    def _go() -> None:
        summary = _summary(load_context(), month, group)
        if as_json:
            emit_json(summary)
            return
        emit_table(
            f"Resumo {summary.year:04d}-{summary.month:02d}{_scope(summary.group)}",
            ["receitas", "despesas", "saldo", "sem categoria", "manuais pendentes"],
            [
                [
                    summary.income,
                    summary.expenses,
                    summary.net,
                    summary.uncategorized,
                    summary.pending_manual,
                ]
            ],
        )
        emit_table(
            "Por categoria",
            CATEGORY_COLUMNS,
            [[line.category, line.spent, line.budget, line.pct] for line in summary.lines],
        )

    run(_go)


@report_app.command("budget")
def budget(month: MonthOpt = None, group: GroupOpt = None, as_json: JsonOpt = False) -> None:
    """Categoria, orçamento e realizado."""

    def _go() -> None:
        summary = _summary(load_context(), month, group)
        lines = [line for line in summary.lines if line.budget is not None]
        if as_json:
            emit_json(lines)
            return
        emit_table(
            f"Orçamento {summary.year:04d}-{summary.month:02d}{_scope(summary.group)}",
            CATEGORY_COLUMNS,
            [[line.category, line.spent, line.budget, line.pct] for line in lines],
        )

    run(_go)


@report_app.command("balance")
def balance(group: GroupOpt = None, as_json: JsonOpt = False) -> None:
    """Saldo por conta e fatura aberta por cartão."""

    def _go() -> None:
        ctx = load_context()
        selected = resolve_group(ctx, group)
        conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
        rows = account_balances(conn, selected, date.today())
        if as_json:
            emit_json(rows)
            return
        emit_table(
            f"Saldos{_scope(group)}",
            ["conta", "tipo", "saldo", "fatura aberta", "mês"],
            [[r.name, r.type, r.balance, r.open_invoice, r.open_invoice_month] for r in rows],
        )

    run(_go)


@report_app.command("invoice")
def invoice(
    account: Annotated[str, typer.Option("--account")],
    month: MonthOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Detalhe da fatura de um cartão."""

    def _go() -> None:
        ctx = load_context()
        acct = resolve_account(ctx, account)
        year, m = _month(month)
        conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
        inv = build_invoice(conn, acct, year, m)
        if as_json:
            emit_json(inv)
            return
        emit_table(
            f"Fatura {acct.name} {year:04d}-{m:02d} ({inv.start} a {inv.end}, vence {inv.due})",
            ["data", "descrição", "valor", "categoria", "parcela", "status"],
            [
                [ln.date, ln.description, ln.amount, ln.category, ln.installment, ln.status]
                for ln in inv.lines
            ],
        )
        emit_table(
            "Totais",
            ["compras", "pagamentos", "a pagar"],
            [[inv.purchases, inv.payments, inv.total_due]],
        )

    run(_go)
