from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.imports.bradesco_checking_pdf import (
    BradescoCheckingPdf,
    parse_statement_pages,
)
from finance.model.errors import FinanceError

FIXTURES = Path(__file__).parent / "fixtures"
PDF = FIXTURES / "bradesco_checking.pdf"
CARD_PDF = FIXTURES / "bradesco_card.pdf"
HEAD = "%PDF-1.4"

# A fixture tem a geometria do extrato real: duas páginas, cabeçalho repetido,
# data só na primeira linha do dia, detalhe (REM:/DES:) em linha própria.
EXPECTED = [
    (date(2026, 3, 2), Decimal("1234.56"), "PIX RECEBIDO — EMPRESA EXEMPLO S.A.", "1000001"),
    (date(2026, 3, 2), Decimal("-200.00"), "PIX ENVIADO — Fulano de Exemplo", "1000002"),
    (date(2026, 3, 2), Decimal("-158.00"), "CONTA DE LUZ", "1000003"),
    (date(2026, 3, 2), Decimal("-23.95"), "IOF S/ UTILIZACAO LIMITE", "0000569"),
    (date(2026, 3, 5), Decimal("-77.25"), "ENCARGOS LIMITE DE CRED", "0000569"),
    (date(2026, 3, 6), Decimal("-1920.00"), "PIX QR CODE ESTATICO — LOJA EXEMPLO LTDA", "1000006"),
    (date(2026, 3, 6), Decimal("3000.00"), "TRANSF SALDO C/SAL P/CC", "1000007"),
    (date(2026, 3, 7), Decimal("-1000.00"), "GASTOS CARTAO DE CREDITO", "1000008"),
]

HEADER = (
    "Data                Histórico                      Docto.         "
    "    Crédito (R$)         Débito (R$)          Saldo (R$)"
)
CREDIT_ROW = (
    "02/03/2026         PIX RECEBIDO                   1000001         "
    "        1.234,56                              5.000,00"
)


def test_parses_every_line_in_document_order() -> None:
    records = BradescoCheckingPdf().parse(PDF)
    assert [(r.date, r.amount, r.description, r.external_id) for r in records] == EXPECTED


def test_pix_takes_the_name_from_the_line_below_and_other_entries_keep_the_history() -> None:
    by_docto = {r.external_id: r.description for r in BradescoCheckingPdf().parse(PDF)}
    assert by_docto["1000001"] == "PIX RECEBIDO — EMPRESA EXEMPLO S.A."
    assert by_docto["1000002"] == "PIX ENVIADO — Fulano de Exemplo"
    # Detalhe que não é REM:/DES: é dado do banco, não favorecido: fica fora.
    assert by_docto["1000003"] == "CONTA DE LUZ"
    assert by_docto["1000007"] == "TRANSF SALDO C/SAL P/CC"


def test_entry_without_a_detail_line_keeps_only_the_history() -> None:
    records = BradescoCheckingPdf().parse(PDF)
    assert [r.description for r in records if r.external_id == "0000569"] == [
        "IOF S/ UTILIZACAO LIMITE",
        "ENCARGOS LIMITE DE CRED",
    ]


def test_date_is_inherited_from_the_previous_line() -> None:
    records = BradescoCheckingPdf().parse(PDF)
    assert [r.date for r in records[:4]] == [date(2026, 3, 2)] * 4


def test_credit_is_positive_and_debit_negative() -> None:
    records = BradescoCheckingPdf().parse(PDF)
    credits = sum(r.amount for r in records if r.amount > 0)
    debits = sum(-r.amount for r in records if r.amount < 0)
    assert (credits, debits) == (Decimal("4234.56"), Decimal("3379.20"))


def test_page_header_and_total_line_are_ignored() -> None:
    records = BradescoCheckingPdf().parse(PDF)
    assert len(records) == len(EXPECTED)
    assert all("Histórico" not in r.description for r in records)
    assert all(r.amount != Decimal("-4234.56") for r in records)


def test_matches_only_a_bradesco_checking_pdf(tmp_path: Path) -> None:
    parser = BradescoCheckingPdf()
    assert parser.matches(PDF, HEAD)
    assert not parser.matches(CARD_PDF, HEAD)
    not_pdf = tmp_path / "extrato.csv"
    not_pdf.write_text("date,title,amount\n", encoding="utf-8")
    assert not parser.matches(not_pdf, "date,title,amount\n")
    fake = tmp_path / "fake.pdf"
    fake.write_text("não é um PDF\n", encoding="utf-8")
    assert not parser.matches(fake, "não é um PDF\n")


def test_the_card_parser_does_not_match_the_checking_pdf() -> None:
    from finance.imports.bradesco_card_pdf import BradescoCardPdf

    assert not BradescoCardPdf().matches(PDF, HEAD)


def test_first_entry_without_a_date_is_a_clear_error() -> None:
    undated = CREDIT_ROW.replace("02/03/2026", "          ")
    with pytest.raises(FinanceError, match="sem data"):
        parse_statement_pages([f"{HEADER}\n{undated}\n"])


def test_entry_line_that_does_not_match_the_layout_is_a_clear_error() -> None:
    without_docto = CREDIT_ROW.replace("1000001", "       ")
    with pytest.raises(FinanceError, match="layout"):
        parse_statement_pages([f"{HEADER}\n{without_docto}\n"])


def test_page_without_the_column_header_is_a_clear_error() -> None:
    with pytest.raises(FinanceError, match="cabeçalho"):
        parse_statement_pages([f"Bradesco Celular\n{CREDIT_ROW}\n"])


def test_invalid_date_is_a_clear_error() -> None:
    broken = CREDIT_ROW.replace("02/03/2026", "30/02/2026")
    with pytest.raises(FinanceError, match="data inválida"):
        parse_statement_pages([f"{HEADER}\n{broken}\n"])
