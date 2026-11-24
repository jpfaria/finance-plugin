from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.imports.bradesco_checking_pdf import BradescoCheckingPdf, parse_statement_pages
from finance.model.errors import FinanceError

FIXTURES = Path(__file__).parent / "fixtures"
PDF = FIXTURES / "bradesco_checking.pdf"
CARD_PDF = FIXTURES / "bradesco_card.pdf"
HEAD = "%PDF-1.4"

# A fixture tem duas páginas, com o cabeçalho repetido e a linha de total no fim.
EXPECTED = [
    (date(2026, 10, 1), Decimal("1234.56"), "PIX RECEBIDO — LOJA EXEMPLO LTDA", "1000001"),
    (date(2026, 10, 1), Decimal("-50.00"), "PIX ENVIADO — JOSE DA SILVA EXEMPLO", "1000002"),
    (date(2026, 10, 1), Decimal("-89.90"), "CONTA DE LUZ", "1000003"),
    (date(2026, 10, 2), Decimal("10000.00"), "LIB EMPRESTIM/FINANCIAM", "1000004"),
    (date(2026, 10, 3), Decimal("-1000.00"), "PIX ENVIADO — MARIA DE EXEMPLO SOU", "1000005"),
    (date(2026, 10, 3), Decimal("500.00"), "TRANSF SALDO C/SAL P/CC", "1000006"),
    (date(2026, 10, 3), Decimal("-94.66"), "GASTOS CARTAO DE CREDITO", "1000007"),
]

# Texto com as colunas preservadas, como `extract_layout_pages` devolve cada página.
HEADER = "Data        Histórico           Docto.    Crédito (R$)   Débito (R$)    Saldo (R$)"
RECEIVED = "01/10/2026  PIX RECEBIDO       1000001        1.234,56                    1.234,56"
RECEIVED_NAME = "            REM: LOJA EXEMPLO LTDA 01/10"
SENT = "            PIX ENVIADO        1000002                         50,00      1.184,56"
SENT_NAME = "            DES: JOSE DA SILVA EXEMPLO 01/10"
POWER_BILL = "01/10/2026  CONTA DE LUZ       1000003                         89,90      1.094,66"
POWER_BILL_DETAIL = "            DISTRIBUIDORA EXEMPLO-00012345"
TOTAL = "Total                                         1.234,56        139,90      1.094,66"


def page(*lines: str) -> str:
    return "\n".join(("Bradesco Celular", "Folha: 1/1", "", HEADER, *lines))


def test_parses_the_whole_statement_in_document_order() -> None:
    records = BradescoCheckingPdf().parse(PDF)
    assert [(r.date, r.amount, r.description, r.external_id) for r in records] == EXPECTED


def test_credit_column_is_positive_and_debit_column_negative() -> None:
    records = parse_statement_pages([page(RECEIVED, RECEIVED_NAME, SENT, SENT_NAME, POWER_BILL)])
    assert [r.amount for r in records] == [
        Decimal("1234.56"),
        Decimal("-50.00"),
        Decimal("-89.90"),
    ]


def test_pix_name_goes_in_the_description() -> None:
    records = parse_statement_pages([page(RECEIVED, RECEIVED_NAME, SENT, SENT_NAME)])
    assert [r.description for r in records] == [
        "PIX RECEBIDO — LOJA EXEMPLO LTDA",
        "PIX ENVIADO — JOSE DA SILVA EXEMPLO",
    ]


def test_entry_without_a_name_keeps_the_history() -> None:
    records = parse_statement_pages([page(POWER_BILL, POWER_BILL_DETAIL)])
    assert records[0].description == "CONTA DE LUZ"


def test_date_is_inherited_from_the_first_transaction_of_the_day() -> None:
    records = parse_statement_pages([page(RECEIVED, RECEIVED_NAME, SENT, SENT_NAME)])
    assert [r.date for r in records] == [date(2026, 10, 1), date(2026, 10, 1)]


def test_repeated_page_header_and_total_line_are_not_entries() -> None:
    first = page(RECEIVED, RECEIVED_NAME)
    second = page(SENT, SENT_NAME, POWER_BILL, TOTAL)
    assert len(parse_statement_pages([first, second])) == 3


def test_document_number_goes_to_external_id() -> None:
    records = parse_statement_pages([page(RECEIVED, RECEIVED_NAME)])
    assert records[0].external_id == "1000001"


def test_total_that_does_not_match_the_sum_is_a_clear_error() -> None:
    """Linha perdida na extração não pode entrar no ledger em silêncio."""
    with pytest.raises(FinanceError, match="não fecha com a linha Total"):
        parse_statement_pages([page(RECEIVED, RECEIVED_NAME, SENT, SENT_NAME, TOTAL)])


def test_statement_without_the_column_header_is_a_clear_error() -> None:
    with pytest.raises(FinanceError, match="sem o cabeçalho"):
        parse_statement_pages(["Bradesco Celular\n" + RECEIVED])


def test_first_transaction_without_a_date_is_a_clear_error() -> None:
    with pytest.raises(FinanceError, match="sem data"):
        parse_statement_pages([page(SENT, SENT_NAME)])


def test_impossible_date_is_a_clear_error() -> None:
    with pytest.raises(FinanceError, match="data inválida"):
        parse_statement_pages([page(RECEIVED.replace("01/10/2026", "30/02/2026"), RECEIVED_NAME)])


def test_matches_only_a_bradesco_checking_pdf(tmp_path: Path) -> None:
    parser = BradescoCheckingPdf()
    assert parser.matches(PDF, HEAD)
    assert not parser.matches(CARD_PDF, HEAD)
    not_pdf = tmp_path / "extrato.csv"
    not_pdf.write_text("Data;Histórico\n", encoding="utf-8")
    assert not parser.matches(not_pdf, "Data;Histórico\n")
    fake = tmp_path / "fake.pdf"
    fake.write_text("não é um PDF\n", encoding="utf-8")
    assert not parser.matches(fake, "não é um PDF\n")


def test_the_card_parser_does_not_take_the_checking_statement() -> None:
    from finance.imports.bradesco_card_pdf import BradescoCardPdf

    assert not BradescoCardPdf().matches(PDF, HEAD)
