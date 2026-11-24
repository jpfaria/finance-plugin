"""Extrato de conta do Bradesco em CSV (`;`), como o internet banking exporta.

O arquivo não é a tabela única que o nome sugere: a linha 1 é um preâmbulo com
agência e conta, o cabeçalho vem na linha 2 e, depois dos lançamentos, vem um
rodapé (linhas vazias, a frase com a data-base, um bloco "Lançamentos
periódicos" com outro cabeçalho e uma linha de total). O bloco de lançamentos
termina na primeira linha toda vazia; dentro dele, linha inesperada é erro.

Crédito e débito vêm em colunas separadas, em notação brasileira (`1.234,56`);
a coluna que não se aplica vem com um espaço. `Docto.` não é único no extrato,
mas é a única coisa que distingue dois lançamentos de mesma data, mesmo
histórico e mesmo valor — por isso vai em `external_id`, senão o dedupe por
hash engoliria um dos dois.
"""

import csv
from collections.abc import Iterator, Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from finance.imports.record import ImportedRecord
from finance.model.errors import FinanceError
from finance.model.money import parse_amount

DELIMITER = ";"
ENCODING = "utf-8-sig"
DATE_FORMAT = "%d/%m/%Y"
HEADER_FIELDS = ("Data", "Histórico", "Docto.", "Crédito (R$)", "Débito (R$)")
HEADER = DELIMITER.join((*HEADER_FIELDS, "Saldo (R$)"))


class BradescoCheckingCsv:
    name = "bradesco-checking-csv"

    def matches(self, path: Path, head: str) -> bool:
        return any(line.strip() == HEADER for line in head.splitlines())

    def parse(self, path: Path) -> list[ImportedRecord]:
        with path.open(encoding=ENCODING, newline="") as fh:
            rows = list(csv.reader(fh, delimiter=DELIMITER))
        return [_record(row) for row in _entry_rows(rows)]


def _entry_rows(rows: Sequence[Sequence[str]]) -> Iterator[Sequence[str]]:
    """Lançamentos: o que vem depois do cabeçalho e antes da primeira linha vazia."""
    for row in rows[_header_index(rows) + 1 :]:
        if all(not cell.strip() for cell in row):
            return
        yield row


def _header_index(rows: Sequence[Sequence[str]]) -> int:
    for index, row in enumerate(rows):
        if [cell.strip() for cell in row[: len(HEADER_FIELDS)]] == list(HEADER_FIELDS):
            return index
    raise FinanceError(f"extrato do Bradesco sem a linha de cabeçalho {HEADER!r}")


def _record(row: Sequence[str]) -> ImportedRecord:
    line = DELIMITER.join(row)
    if len(row) < len(HEADER_FIELDS):
        raise FinanceError(f"linha incompleta no extrato do Bradesco: {line!r}")
    raw_date, history, docto, credit, debit = (cell.strip() for cell in row[: len(HEADER_FIELDS)])
    return ImportedRecord(
        date=_date(raw_date, line),
        amount=_amount(credit, debit, line),
        description=history,
        external_id=docto,
    )


def _date(text: str, line: str) -> date:
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as exc:
        raise FinanceError(f"data inválida no extrato do Bradesco: {line!r}") from exc


def _amount(credit: str, debit: str, line: str) -> Decimal:
    """Crédito é entrada (positivo), débito é saída (negativo)."""
    if credit and debit:
        raise FinanceError(f"lançamento com crédito e débito na mesma linha: {line!r}")
    if credit:
        return parse_amount(credit)
    if debit:
        return -parse_amount(debit)
    raise FinanceError(f"lançamento sem crédito nem débito: {line!r}")
