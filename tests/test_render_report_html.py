"""A página da previsão: números em pt-BR, barras proporcionais, nada vindo de fora."""

from decimal import Decimal

from finance.render.report_html import brl, forecast_html, month_label, short_month
from finance.reports.forecast import Forecast, ForecastLine


def _line(category: str, average: str, per_month: list[str], every: bool) -> ForecastLine:
    values = [Decimal(v) for v in per_month]
    return ForecastLine(
        category=category,
        per_month=values,
        months_present=sum(1 for v in values if v != Decimal("0.00")),
        average=Decimal(average),
        every_month=every,
    )


def _forecast() -> Forecast:
    lines = [
        _line("casa/mercado", "500.00", ["400.00", "600.00"], True),
        _line("lazer/viagem", "450.00", ["0.00", "900.00"], False),
    ]
    return Forecast(
        target="2027-02",
        base=["2026-10", "2026-11"],
        group=None,
        income=Decimal("3000.00"),
        expenses=Decimal("950.00"),
        net=Decimal("2050.00"),
        lines=lines,
        income_by_month={"2026-10": Decimal("3000.00"), "2026-11": Decimal("3000.00")},
        expenses_by_month={"2026-10": Decimal("400.00"), "2026-11": Decimal("1500.00")},
    )


def test_brl_uses_the_brazilian_format() -> None:
    assert brl(Decimal("1234.5")) == "1.234,50"
    assert brl(Decimal("0")) == "0,00"
    assert brl(Decimal("-4361.77")) == "-4.361,77"
    assert brl(Decimal("1234567.89")) == "1.234.567,89"


def test_month_labels() -> None:
    assert month_label("2027-02") == "fevereiro de 2027"
    assert short_month("2026-10") == "out/26"


def test_the_page_carries_the_numbers_and_the_caveats() -> None:
    html = forecast_html(_forecast())
    assert "Previsão de fevereiro de 2027" in html
    assert "casa/mercado" in html and "500,00" in html
    assert "3.000,00" in html and "950,00" in html
    assert "out/26" in html and "nov/26" in html
    assert "sazonalidade" in html
    assert "<svg" in html and "</table>" in html


def test_nothing_is_loaded_from_outside() -> None:
    """O PDF é impresso offline: link, script ou imagem externa sairia em branco."""
    html = forecast_html(_forecast())
    for forbidden in ("<link", "<script", "<img", "@import", "src=", "url("):
        assert forbidden not in html


def test_the_biggest_bar_fills_the_span() -> None:
    html = forecast_html(_forecast())
    assert 'width="424"' in html  # 760 - 250 de rótulo - 86 de valor


def test_uncategorized_adds_its_own_note() -> None:
    forecast = _forecast()
    with_pending = Forecast(
        **{
            **forecast.__dict__,
            "lines": [*forecast.lines, _line("(sem categoria)", "10.00", ["10.00", "10.00"], True)],
        }
    )
    assert "Categorizar redistribui" in forecast_html(with_pending)
    assert "Categorizar redistribui" not in forecast_html(forecast)
