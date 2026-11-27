"""`finance report *`: read-only views over the cache."""

from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from finance.cache.connection import open_db
from finance.cli.context import Context, load_context, resolve_account, resolve_group, run
from finance.model.dates import add_months, parse_month
from finance.model.errors import FinanceError
from finance.render.output import emit_json, emit_table
from finance.render.pdf import html_to_pdf
from finance.render.report_html import forecast_html
from finance.reports.balance import account_balances
from finance.reports.cash import cash_report
from finance.reports.forecast import (
    DEFAULT_BASE_MONTHS,
    Forecast,
    base_before,
    months_between,
)
from finance.reports.forecast import forecast as build_forecast
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


def _next_month(text: str | None) -> tuple[int, int]:
    if text is not None:
        return parse_month(text)
    nxt = add_months(date.today().replace(day=1), 1)
    return nxt.year, nxt.month


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
            ["conta", "tipo", "saldo", "fonte", "fatura aberta", "mês"],
            [
                [
                    r.name,
                    r.type,
                    r.balance,
                    "banco" if r.real else "só movimento",
                    r.open_invoice,
                    r.open_invoice_month,
                ]
                for r in rows
            ],
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


def _forecast(
    month: str | None, base: int, since: str | None, until: str | None, group: str | None
) -> Forecast:
    ctx = load_context()
    year, m = _next_month(month)
    if since is not None or until is not None:
        if since is None or until is None:
            raise FinanceError("use --from e --to juntos")
        months = months_between(parse_month(since), parse_month(until))
    else:
        months = base_before(year, m, base)
    selected = resolve_group(ctx, group)
    conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
    return build_forecast(
        conn,
        (year, m),
        months,
        accounts=None if group is None else set(selected),
        group=group,
    )


@report_app.command("forecast")
def forecast(
    month: Annotated[
        str | None, typer.Option("--month", help="AAAA-MM a prever, default o mês que vem")
    ] = None,
    base: Annotated[
        int, typer.Option("--base", help="quantos meses fechados usar de base")
    ] = DEFAULT_BASE_MONTHS,
    since: Annotated[str | None, typer.Option("--from", help="1º mês da base, AAAA-MM")] = None,
    until: Annotated[str | None, typer.Option("--to", help="último mês da base, AAAA-MM")] = None,
    group: GroupOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Previsão por categoria: o que cada uma costuma custar por mês."""

    def _go() -> None:
        result = _forecast(month, base, since, until, group)
        if as_json:
            emit_json(result)
            return
        window = f"{result.base[0]} a {result.base[-1]}" if len(result.base) > 1 else result.base[0]
        columns = ["categoria", "previsto/mês", "meses", *result.base]
        total = len(result.base)
        for title, lines in (
            ("Todo mês", [ln for ln in result.lines if ln.every_month]),
            ("Eventual", [ln for ln in result.lines if not ln.every_month]),
        ):
            emit_table(
                title,
                columns,
                [
                    [ln.category, ln.average, f"{ln.months_present}/{total}", *ln.per_month]
                    for ln in lines
                ],
            )
        emit_table(
            f"Previsão {result.target}{_scope(result.group)} — base {window}",
            ["receitas", "despesas", "saldo"],
            [[result.income, result.expenses, result.net]],
        )

    run(_go)


@report_app.command("pdf")
def pdf(
    out: Annotated[Path, typer.Option("--out", help="arquivo .pdf a gerar")],
    month: Annotated[
        str | None, typer.Option("--month", help="AAAA-MM a prever, default o mês que vem")
    ] = None,
    base: Annotated[
        int, typer.Option("--base", help="quantos meses fechados usar de base")
    ] = DEFAULT_BASE_MONTHS,
    since: Annotated[str | None, typer.Option("--from", help="1º mês da base, AAAA-MM")] = None,
    until: Annotated[str | None, typer.Option("--to", help="último mês da base, AAAA-MM")] = None,
    group: GroupOpt = None,
) -> None:
    """Gera a previsão em PDF, com gráficos, imprimindo pelo navegador da máquina."""

    def _go() -> None:
        result = _forecast(month, base, since, until, group)
        target = out if out.suffix.lower() == ".pdf" else out.with_suffix(".pdf")
        html = target.with_suffix(".html")
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text(forecast_html(result), encoding="utf-8")
        html_to_pdf(html, target)
        typer.echo(f"PDF: {target}")
        typer.echo(f"HTML: {html}")

    run(_go)


@report_app.command("cash")
def cash(month: MonthOpt = None, group: GroupOpt = None, as_json: JsonOpt = False) -> None:
    """Caixa do mês: o que entrou e saiu das contas de verdade, e o saldo no fim."""

    def _go() -> None:
        ctx = load_context()
        year, m = _month(month)
        selected = resolve_group(ctx, group)
        conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
        result = cash_report(conn, selected, year, m, group)
        if as_json:
            emit_json(result)
            return
        emit_table(
            f"Caixa {year:04d}-{m:02d}{_scope(group)}",
            ["conta", "saldo inicial", "entrou", "saiu", "movimento", "saldo final"],
            [
                [ln.name, ln.opening, ln.income, ln.outflow, ln.movement, ln.closing]
                for ln in result.lines
            ],
        )
        emit_table(
            "Total",
            ["saldo inicial", "entrou", "saiu", "movimento", "saldo final"],
            [[result.opening, result.income, result.outflow, result.movement, result.closing]],
        )
        if result.accounts_without_opening:
            faltam = ", ".join(result.accounts_without_opening)
            typer.echo(
                f"sem saldo inicial em accounts.yaml: {faltam} "
                "(opening_balance + opening_date); sem isso o saldo fica em branco"
            )

    run(_go)
