from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.imports.nubank_card_csv import NubankCardCsv
from finance.imports.nubank_checking_csv import NubankCheckingCsv

FIXTURES = Path(__file__).parent / "fixtures"


def test_checking_matches_and_parses() -> None:
    parser = NubankCheckingCsv()
    path = FIXTURES / "nubank_checking.csv"
    assert parser.matches(path, path.read_text(encoding="utf-8")[:100])
    assert not parser.matches(path, "date,title,amount")
    records = parser.parse(path)
    assert [(r.date, r.amount, r.external_id) for r in records] == [
        (date(2026, 9, 1), Decimal("-35.90"), "aaaa-1111"),
        (date(2026, 9, 3), Decimal("1200.00"), "bbbb-2222"),
    ]
    assert records[0].description == "Transferência enviada pelo Pix - UBER"


def test_card_matches_and_parses_with_inverted_sign() -> None:
    parser = NubankCardCsv()
    path = FIXTURES / "nubank_card.csv"
    assert parser.matches(path, "date,title,amount\n")
    assert not parser.matches(path, "Data,Valor,Identificador,Descrição")
    records = parser.parse(path)
    assert [(r.date, r.amount, r.description, r.external_id) for r in records] == [
        (date(2026, 9, 2), Decimal("-42.50"), "Ifood", ""),
        (date(2026, 9, 4), Decimal("500.00"), "Pagamento recebido", ""),
    ]
