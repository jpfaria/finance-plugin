"""Render a Forecast as a printable HTML page: inline SVG charts, no external assets.

A página é impressa em PDF pelo navegador (`finance report pdf`), então tudo é
inline: nenhuma fonte, folha de estilo ou imagem de fora, pra o PDF sair igual
sem rede. Todo número vem do `Forecast`; esta camada só desenha.
"""

from decimal import ROUND_HALF_UP, Decimal
from html import escape

from finance.reports.forecast import Forecast, ForecastLine

CHART_WIDTH = 760
LABEL_WIDTH = 250
VALUE_WIDTH = 86
BAR_HEIGHT = 20
BAR_GAP = 7
AXIS_HEIGHT = 18

MONTH_CHART_HEIGHT = 240
MONTH_BAR_WIDTH = 46
MONTH_GROUP_GAP = 34

INK = "#1b1b1d"
MUTED = "#70707a"
GRID = "#e4e4ea"
RECURRING = "#3c6098"
OCCASIONAL = "#9aa3b0"
INCOME = "#2f6f5e"
EXPENSE = "#b5533c"
ZERO = Decimal("0.00")
CENTS = Decimal("0.01")
MONTH_NAMES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def brl(value: Decimal) -> str:
    """1234.5 -> '1.234,50'."""
    quantized = value.quantize(CENTS, rounding=ROUND_HALF_UP)
    sign = "-" if quantized < 0 else ""
    reais, cents = divmod(abs(quantized), 1)
    digits = f"{int(reais):,}".replace(",", ".")
    return f"{sign}{digits},{int(cents * 100):02d}"


def month_label(key: str) -> str:
    """'2027-02' -> 'fevereiro de 2027'."""
    year, month = key.split("-")
    return f"{MONTH_NAMES[int(month) - 1]} de {year}"


def short_month(key: str) -> str:
    """'2026-10' -> 'out/26'."""
    year, month = key.split("-")
    return f"{MONTH_NAMES[int(month) - 1][:3]}/{year[2:]}"


def forecast_html(result: Forecast) -> str:
    """A página inteira, a partir do que o `Forecast` já calculou."""
    recurring = [line for line in result.lines if line.every_month]
    occasional = [line for line in result.lines if not line.every_month]
    parts = [
        _head(result),
        _kpis(result),
        _section("O que se repete todo mês", _bar_chart(recurring, RECURRING)),
        _section("Eventual — apareceu em parte dos meses", _bar_chart(occasional, OCCASIONAL)),
        _section("Mês a mês", _month_chart(result)),
        _section("Todas as categorias", _table(result)),
        _notes(result),
    ]
    return _document(f"Previsão {month_label(result.target)}", "\n".join(parts))


def _document(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
@page {{ size: A4; margin: 14mm 13mm; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; color: {INK}; background: #fff;
  font: 11px/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}}
h1 {{ font-size: 22px; margin: 0 0 2px; letter-spacing: -0.2px; }}
h2 {{ font-size: 13px; margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.08em; }}
.sub {{ color: {MUTED}; margin: 0 0 18px; }}
section {{ margin: 0 0 22px; break-inside: avoid; }}
.kpis {{ display: flex; gap: 10px; margin: 0 0 22px; }}
.kpi {{ flex: 1; border: 1px solid {GRID}; border-radius: 6px; padding: 10px 12px; }}
.kpi .label {{ color: {MUTED}; font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.08em; }}
.kpi .value {{ font-size: 19px; font-variant-numeric: tabular-nums; margin-top: 3px; }}
.kpi.negative .value {{ color: {EXPENSE}; }}
.kpi.positive .value {{ color: {INCOME}; }}
svg {{ display: block; width: 100%; height: auto; }}
table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
thead {{ display: table-header-group; }}
tr {{ break-inside: avoid; }}
th, td {{ padding: 4px 6px; border-bottom: 1px solid {GRID}; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
thead th {{ color: {MUTED}; font-weight: 600; font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.06em; }}
tbody tr.occasional td:first-child {{ color: {MUTED}; }}
tfoot td {{ font-weight: 600; border-top: 1px solid {INK}; border-bottom: none; }}
.notes {{ border-top: 1px solid {GRID}; padding-top: 10px; color: {MUTED}; }}
.notes li {{ margin: 0 0 4px; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _head(result: Forecast) -> str:
    window = (
        f"{short_month(result.base[0])} a {short_month(result.base[-1])}"
        if len(result.base) > 1
        else short_month(result.base[0])
    )
    scope = f" · {escape(result.group)}" if result.group else ""
    return (
        f"<h1>Previsão de {escape(month_label(result.target))}</h1>\n"
        f'<p class="sub">Média de {len(result.base)} mês(es) fechado(s): '
        f"{escape(window)}{scope}</p>"
    )


def _kpis(result: Forecast) -> str:
    cards = [
        ("Receitas por mês", result.income, "positive"),
        ("Despesas por mês", result.expenses, "negative"),
        ("Sobra por mês", result.net, "positive" if result.net >= ZERO else "negative"),
    ]
    inner = "".join(
        f'<div class="kpi {kind}"><div class="label">{escape(label)}</div>'
        f'<div class="value">{brl(value)}</div></div>'
        for label, value, kind in cards
    )
    return f'<div class="kpis">{inner}</div>'


def _section(title: str, body: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{body}</section>"


def _bar_chart(lines: list[ForecastLine], color: str) -> str:
    if not lines:
        return '<p class="sub">Nada aqui nos meses da base.</p>'
    top = max(line.average for line in lines)
    span = CHART_WIDTH - LABEL_WIDTH - VALUE_WIDTH
    height = len(lines) * (BAR_HEIGHT + BAR_GAP)
    rows = []
    for index, line in enumerate(lines):
        y = index * (BAR_HEIGHT + BAR_GAP)
        width = 0 if top == ZERO else int(span * (line.average / top))
        rows.append(
            f'<text x="0" y="{y + 14}" font-size="11" fill="{INK}">'
            f"{escape(_clip(line.category))}</text>"
            f'<rect x="{LABEL_WIDTH}" y="{y}" width="{max(width, 1)}" height="{BAR_HEIGHT}" '
            f'rx="2" fill="{color}"/>'
            f'<text x="{LABEL_WIDTH + width + 7}" y="{y + 14}" font-size="11" fill="{MUTED}">'
            f"{brl(line.average)}</text>"
        )
    return (
        f'<svg viewBox="0 0 {CHART_WIDTH} {height}" role="img" '
        f'xmlns="http://www.w3.org/2000/svg">{"".join(rows)}</svg>'
    )


def _clip(text: str, limit: int = 34) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _month_chart(result: Forecast) -> str:
    """Receita e despesa de cada mês da base, pra ver se a média esconde um mês fora da curva."""
    months = result.base
    values = [
        (month, result.income_by_month.get(month, ZERO), result.expenses_by_month.get(month, ZERO))
        for month in months
    ]
    top = max((max(inc, exp) for _, inc, exp in values), default=ZERO)
    plot = MONTH_CHART_HEIGHT - AXIS_HEIGHT
    group = MONTH_BAR_WIDTH * 2 + MONTH_GROUP_GAP
    width = max(len(months) * group, CHART_WIDTH)
    offset = (width - len(months) * group) / 2
    bars = [
        f'<line x1="0" y1="{plot}" x2="{width}" y2="{plot}" stroke="{GRID}"/>',
    ]
    for index, (month, income, expense) in enumerate(values):
        base_x = offset + index * group + MONTH_GROUP_GAP / 2
        for slot, (value, color) in enumerate(((income, INCOME), (expense, EXPENSE))):
            height = 0 if top == ZERO else int((plot - 22) * (value / top))
            x = base_x + slot * MONTH_BAR_WIDTH
            y = plot - height
            bars.append(
                f'<rect x="{x:.0f}" y="{y}" width="{MONTH_BAR_WIDTH - 6}" '
                f'height="{max(height, 1)}" rx="2" fill="{color}"/>'
                f'<text x="{x + (MONTH_BAR_WIDTH - 6) / 2:.0f}" y="{y - 5}" font-size="10" '
                f'fill="{MUTED}" text-anchor="middle">{brl(value)}</text>'
            )
        bars.append(
            f'<text x="{base_x + MONTH_BAR_WIDTH - 3:.0f}" y="{plot + 13}" font-size="11" '
            f'fill="{INK}" text-anchor="middle">{escape(short_month(month))}</text>'
        )
    legend = (
        f'<rect x="0" y="0" width="9" height="9" rx="2" fill="{INCOME}"/>'
        f'<text x="14" y="9" font-size="10" fill="{MUTED}">receitas</text>'
        f'<rect x="76" y="0" width="9" height="9" rx="2" fill="{EXPENSE}"/>'
        f'<text x="90" y="9" font-size="10" fill="{MUTED}">despesas</text>'
    )
    return (
        f'<svg viewBox="0 0 {width} {MONTH_CHART_HEIGHT}" role="img" '
        f'xmlns="http://www.w3.org/2000/svg">{legend}{"".join(bars)}</svg>'
    )


def _table(result: Forecast) -> str:
    head = "".join(f"<th>{escape(short_month(month))}</th>" for month in result.base)
    rows = []
    for line in result.lines:
        cells = "".join(f"<td>{brl(value)}</td>" for value in line.per_month)
        css = "" if line.every_month else ' class="occasional"'
        rows.append(
            f"<tr{css}><td>{escape(line.category)}</td><td>{brl(line.average)}</td>"
            f"<td>{line.months_present}/{len(result.base)}</td>{cells}</tr>"
        )
    return (
        "<table><thead><tr><th>categoria</th><th>previsto/mês</th><th>meses</th>"
        f"{head}</tr></thead><tbody>{''.join(rows)}</tbody>"
        f"<tfoot><tr><td>total</td><td>{brl(result.expenses)}</td><td></td>"
        f"{''.join('<td></td>' for _ in result.base)}</tr></tfoot></table>"
    )


def _notes(result: Forecast) -> str:
    items = [
        f"A média divide por todos os {len(result.base)} meses da base, mesmo onde a categoria "
        "não apareceu: gasto único entra como fração. A coluna <em>meses</em> mostra em quantos "
        "ele apareceu de verdade.",
        "Não há sazonalidade: a previsão repete a média da base. Décimo terceiro, IPVA, IPTU, "
        "matrícula e Natal só aparecem se estiverem nos meses da base.",
        "Competência: compra no cartão conta no mês da compra, e transferência entre contas "
        "próprias não conta como gasto.",
    ]
    if any(line.category == "(sem categoria)" for line in result.lines):
        items.append(
            "Há gasto em <em>(sem categoria)</em>. Categorizar redistribui esse valor entre as "
            "categorias — não reduz o total."
        )
    return '<div class="notes"><ul>' + "".join(f"<li>{item}</li>" for item in items) + "</ul></div>"
