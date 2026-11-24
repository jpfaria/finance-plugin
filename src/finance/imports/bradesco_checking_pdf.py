"""Extrato de conta do Bradesco em PDF — o único formato com o nome do favorecido.

O CSV do mesmo extrato traz só o histórico (`PIX ENVIADO`), sem dizer pra quem;
o PDF traz o nome numa segunda linha, logo abaixo da linha de valores. Por isso
este parser existe apesar de já haver o `bradesco-checking-csv`.

Geometria medida no extrato real (não inventada):

- cada página repete um cabeçalho de 5 linhas que termina na linha de colunas
  `Data Histórico Docto. Crédito (R$) Débito (R$) Saldo (R$)`;
- a linha de valores é `[DD/MM/AAAA] <histórico> <docto de 7 dígitos> <valor>
  <saldo>`. A data só aparece na primeira linha do dia e as seguintes a herdam;
- o detalhe vem na linha de baixo: `REM: <nome> DD/MM` (quem enviou),
  `DES: <nome> DD/MM` (pra quem foi), ou um dado do banco (código da conta de
  luz, `ENCARGO - 07,73%`, nome do empregador). Só `REM:`/`DES:` entram na
  descrição, como `<histórico> — <nome>`; o resto é ruído do banco e fica fora;
- crédito e débito são colunas distintas, então o sinal sai da coluna onde o
  valor termina, comparada com o fim de `Crédito (R$)` e de `Débito (R$)` no
  cabeçalho da própria página — os offsets variam alguns caracteres de página
  pra página, por isso são lidos por página, nunca fixos;
- a coluna Saldo é ignorada: ela não fecha com o movimento linha a linha (há
  crédito de 10.000,00 entre saldos 4.024,72 e 5.975,28 no extrato real).

Como as colunas só existem no texto com `extraction_mode="layout"`, é esse
texto que o parser lê, uma string por página.
"""

import re
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

from finance.imports.pdf_text import extract_layout_pages, extract_text
from finance.imports.record import ImportedRecord
from finance.model.errors import FinanceError
from finance.model.money import parse_amount

PDF_EXTENSION = ".pdf"
PDF_MAGIC = "%PDF"
MARKERS = ("Extrato de:", "Docto.", "Saldo (R$)")

CREDIT_HEADER = "Crédito (R$)"
DEBIT_HEADER = "Débito (R$)"
DATE_FORMAT = "%d/%m/%Y"
DESCRIPTION_SEPARATOR = " — "

AMOUNT = r"\d{1,3}(?:\.\d{3})*,\d{2}"
ROW = re.compile(
    rf"^\s*(?:(\d{{2}}/\d{{2}}/\d{{4}})\s+)?(\S.*?)\s+(\d{{7}})\s+({AMOUNT})\s+{AMOUNT}\s*$"
)
TWO_AMOUNTS = re.compile(rf"{AMOUNT}\s+{AMOUNT}\s*$")
TOTAL = re.compile(r"^\s*Total\b")
COUNTERPARTY = re.compile(r"^(?:REM|DES):\s*(.+?)(?:\s+\d{2}/\d{2})?$")
WHITESPACE = re.compile(r"\s+")


class BradescoCheckingPdf:
    name = "bradesco-checking-pdf"

    def matches(self, path: Path, head: str) -> bool:
        if path.suffix.lower() != PDF_EXTENSION or not head.startswith(PDF_MAGIC):
            return False
        text = extract_text(path)
        return all(marker in text for marker in MARKERS)

    def parse(self, path: Path) -> list[ImportedRecord]:
        return parse_statement_pages(extract_layout_pages(path))


def parse_statement_pages(pages: list[str]) -> list[ImportedRecord]:
    """Lançamentos do extrato, na ordem do documento.

    `pages` é o texto de cada página em modo layout: as colunas viram espaços e
    é a posição do valor na linha que diz se é crédito ou débito.
    """
    records: list[ImportedRecord] = []
    day: date | None = None
    for page in pages:
        columns: tuple[int, int] | None = None
        for line in page.splitlines():
            if not line.strip():
                continue
            if CREDIT_HEADER in line and DEBIT_HEADER in line:
                columns = _columns(line)
                continue
            match = ROW.match(line.rstrip())
            if columns is None:
                if match is not None or TWO_AMOUNTS.search(line.rstrip()):
                    raise FinanceError(
                        "página do extrato do Bradesco com lançamento antes da linha "
                        f"de cabeçalho {CREDIT_HEADER!r}: {line.strip()!r}. "
                        "O layout mudou — não importe adivinhando."
                    )
                continue
            if TOTAL.match(line):
                return records
            if match is None:
                if TWO_AMOUNTS.search(line.rstrip()):
                    raise FinanceError(
                        f"linha com valores fora do layout no extrato do Bradesco: "
                        f"{line.strip()!r}. O layout mudou — não importe adivinhando."
                    )
                if records:
                    records[-1] = _with_counterparty(records[-1], line)
                continue
            record, day = _read_row(match, day, columns)
            records.append(record)
    return records


def _columns(header: str) -> tuple[int, int]:
    """Onde terminam as colunas de crédito e de débito nesta página."""
    return (
        header.index(CREDIT_HEADER) + len(CREDIT_HEADER),
        header.index(DEBIT_HEADER) + len(DEBIT_HEADER),
    )


def _read_row(
    match: re.Match[str], day: date | None, columns: tuple[int, int]
) -> tuple[ImportedRecord, date]:
    stamp, history, docto, amount = match.groups()
    if stamp:
        day = _date(stamp)
    if day is None:
        raise FinanceError(
            f"primeiro lançamento do extrato do Bradesco sem data: {match.group(0).strip()!r}"
        )
    value = parse_amount(amount)
    credit_end, debit_end = columns
    end = match.end(4)
    credit = abs(end - credit_end) < abs(end - debit_end)
    record = ImportedRecord(
        date=day,
        amount=value if credit else -value,
        description=WHITESPACE.sub(" ", history).strip(),
        external_id=docto,
    )
    return record, day


def _with_counterparty(record: ImportedRecord, line: str) -> ImportedRecord:
    """Nome do favorecido da linha de detalhe, quando ela traz um."""
    match = COUNTERPARTY.match(line.strip())
    if match is None:
        return record
    name = WHITESPACE.sub(" ", match.group(1)).strip()
    if not name:
        return record
    return replace(record, description=f"{record.description}{DESCRIPTION_SEPARATOR}{name}")


def _date(text: str) -> date:
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as exc:
        raise FinanceError(f"data inválida no extrato do Bradesco: {text!r}") from exc
