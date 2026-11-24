from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.imports.bradesco_checking_csv import BradescoCheckingCsv
from finance.imports.record import record_hash
from finance.model.errors import FinanceError

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "bradesco_checking.csv"
PREAMBLE = "Extrato de: Ag: 0000 | Conta: 00000-0;;;;;"
HEADER = "Data;Histórico;Docto.;Crédito (R$);Débito (R$);Saldo (R$)"


def _statement(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "extrato.csv"
    path.write_text("\n".join((PREAMBLE, HEADER, *rows)) + "\n", encoding="utf-8-sig")
    return path


def test_matches_header_on_the_second_line_not_the_preamble() -> None:
    """A linha 1 do extrato é preâmbulo; o cabeçalho está na linha 2."""
    parser = BradescoCheckingCsv()
    assert parser.matches(FIXTURE, FIXTURE.read_text(encoding="utf-8")[:512])
    assert not parser.matches(FIXTURE, "Data,Valor,Identificador,Descrição\n01/09/2026,-1,x,y")
    assert not parser.matches(FIXTURE, "date,title,amount\n2026-09-02,Ifood,42.50")


def test_parses_credit_and_debit_ignoring_preamble_and_footer() -> None:
    records = BradescoCheckingCsv().parse(FIXTURE)
    assert [(r.date, r.amount, r.description, r.external_id) for r in records] == [
        (date(2026, 10, 1), Decimal("1234.56"), "PIX RECEBIDO", "1000001"),
        (date(2026, 10, 2), Decimal("-89.90"), "CONTA DE LUZ", "1000002"),
        (date(2026, 10, 3), Decimal("-50.00"), "PIX ENVIADO", "1000003"),
        (date(2026, 10, 3), Decimal("-50.00"), "PIX ENVIADO", "1000004"),
        (date(2026, 10, 4), Decimal("10000.00"), "TRANSF SALDO C/SAL P/CC", "1000005"),
    ]


def test_docto_keeps_two_identical_entries_apart() -> None:
    """Mesma data, mesmo histórico, mesmo valor: só o Docto. os distingue."""
    records = BradescoCheckingCsv().parse(FIXTURE)
    assert record_hash("bradesco", records[2]) != record_hash("bradesco", records[3])


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("05/10/2026;PIX ENVIADO;1;10,00;20,00;0,00", "crédito e débito"),
        ("05/10/2026;PIX ENVIADO;1; ; ;0,00", "sem crédito nem débito"),
        ("05 de outubro;PIX ENVIADO;1;10,00; ;0,00", "data inválida"),
        ("05/10/2026;PIX ENVIADO;1", "linha incompleta"),
    ],
)
def test_unexpected_line_in_the_block_fails_loud(tmp_path: Path, row: str, message: str) -> None:
    with pytest.raises(FinanceError, match=message):
        BradescoCheckingCsv().parse(_statement(tmp_path, row))


def test_file_without_the_header_is_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "extrato.csv"
    path.write_text(PREAMBLE + "\n", encoding="utf-8-sig")
    with pytest.raises(FinanceError, match="cabeçalho"):
        BradescoCheckingCsv().parse(path)
