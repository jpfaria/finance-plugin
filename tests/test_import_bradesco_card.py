from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.imports.bradesco_card_pdf import BradescoCardPdf, parse_statement_text
from finance.model.errors import FinanceError

FIXTURES = Path(__file__).parent / "fixtures"
PDF = FIXTURES / "bradesco_card.pdf"
HEAD = "%PDF-1.4"

# A fatura só traz dia/mês; o ano vem do vencimento (20/09/2026 na fixture).
# Parcela fica no 1º do mês do vencimento, não no dia da compra (ver `_charge_date`).
EXPECTED = [
    (date(2026, 8, 20), Decimal("900.00"), "PAGTO. POR DEB EM C/C"),
    (date(2026, 9, 4), Decimal("-2.50"), "CUSTO TRANS. EXTERIOR-IOF"),
    (date(2026, 9, 4), Decimal("-38.50"), "IOF S/ TRANS INTER REAIS"),
    (date(2026, 9, 1), Decimal("-10.00"), "LOJA EXEMPLO ASSINA CIDADE EXEMP - Parcela 5/21"),
    (date(2026, 8, 20), Decimal("-50.00"), "SERVICO EXEMPLO USD 10,00 EXEMPLOPASSC US"),
    (date(2026, 8, 31), Decimal("-100.00"), "MERCADO EXEMPLO CIDADE EXEMP"),
    (date(2026, 9, 2), Decimal("-20.00"), "RESTAURANTE EXEMPL ANGRA DOS REI"),
    (date(2026, 9, 1), Decimal("-25.00"), "MP*LOJAEXEMPLO BAURU - Parcela 10/12"),
    (date(2026, 9, 1), Decimal("-30.00"), "MP*OUTRALOJAEXEM CAJAMAR - Parcela 10/12"),
    (date(2026, 9, 1), Decimal("-45.00"), "MP*LOJAEXEMPLOTRES SANTANA DE PA - Parcela 11/12"),
    (date(2026, 8, 6), Decimal("-100.00"), "SERVICO EXEMPLO DOIS 100,00 EXEMPLO.C OM"),
    (date(2026, 9, 3), Decimal("18.50"), "ESTORNO EXEMPLO CIDADE EXEMP"),
    (date(2026, 9, 4), Decimal("-600.00"), "ULTIMA COMPRA EXEMPLO CIDADE EXEMP"),
]


def test_parses_the_whole_invoice_in_document_order() -> None:
    records = BradescoCardPdf().parse(PDF)
    assert [(r.date, r.amount, r.description) for r in records] == EXPECTED
    assert all(r.external_id == "" for r in records)


def test_total_matches_the_invoice_total() -> None:
    """Soma assinada = -total da fatura + pagamento: prova que nada sumiu."""
    records = BradescoCardPdf().parse(PDF)
    payment = Decimal("900.00")
    assert sum(r.amount for r in records) == -Decimal("1002.50") + payment


def test_matches_only_a_bradesco_card_pdf(tmp_path: Path) -> None:
    parser = BradescoCardPdf()
    assert parser.matches(PDF, HEAD)
    not_pdf = tmp_path / "extrato.csv"
    not_pdf.write_text("date,title,amount\n", encoding="utf-8")
    assert not parser.matches(not_pdf, "date,title,amount\n")
    fake = tmp_path / "fake.pdf"
    fake.write_text("não é um PDF\n", encoding="utf-8")
    assert not parser.matches(fake, "não é um PDF\n")


def test_does_not_match_a_pdf_from_another_bank(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    other = tmp_path / "outro-banco.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with other.open("wb") as fh:
        writer.write(fh)
    assert not BradescoCardPdf().matches(other, other.read_text(errors="replace")[:8])


def test_credit_is_positive_and_debit_negative() -> None:
    text = (
        "Vencimento\n20/09/2026\n"
        "20/08 PAGTO. POR DEB EM C/C 900,00 -\n"
        "31/08 MERCADO EXEMPLO CIDADE EXEMP 100,00\n"
    )
    assert [r.amount for r in parse_statement_text(text)] == [
        Decimal("900.00"),
        Decimal("-100.00"),
    ]


def test_date_without_year_before_the_due_date_is_the_previous_year() -> None:
    text = "Vencimento\n20/09/2026\n21/09 COMPRA EXEMPLO CIDADE EXEMP 10,00\n"
    assert parse_statement_text(text)[0].date == date(2025, 9, 21)


def test_installment_is_dated_in_the_month_of_the_invoice() -> None:
    """A parcela é cobrada agora; a data da compra deixaria a despesa num mês que já passou."""
    text = "Vencimento\n20/09/2026\n29/03 LOJA EXEMPLO 08/12 CIDADE EXEMP 10,00\n"
    record = parse_statement_text(text)[0]
    assert record.date == date(2026, 9, 1)
    assert record.description == "LOJA EXEMPLO CIDADE EXEMP - Parcela 8/12"


def test_invoice_without_due_date_is_a_clear_error() -> None:
    with pytest.raises(FinanceError, match="sem data de vencimento"):
        parse_statement_text("31/08 MERCADO EXEMPLO CIDADE EXEMP 100,00\n")


def test_transaction_line_without_an_amount_is_a_clear_error() -> None:
    text = "Vencimento\n20/09/2026\n31/08 MERCADO EXEMPLO SEM VALOR\nrodapé qualquer\n"
    with pytest.raises(FinanceError, match="sem valor"):
        parse_statement_text(text)


def test_impossible_date_is_a_clear_error() -> None:
    text = "Vencimento\n20/09/2026\n30/02 COMPRA EXEMPLO CIDADE EXEMP 10,00\n"
    with pytest.raises(FinanceError, match="data inválida"):
        parse_statement_text(text)
