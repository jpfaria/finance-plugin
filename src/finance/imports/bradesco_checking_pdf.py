"""Extrato de conta do Bradesco em PDF (Bradesco Celular → Extrato → exportar).

O CSV do mesmo extrato traz `PIX ENVIADO` / `PIX RECEBIDO` sem nome nenhum. O
PDF traz o favorecido numa segunda linha do lançamento — `DES:` quando é saída,
`REM:` quando é entrada —, truncado em 21 caracteres e seguido do dia/mês da
operação.

O texto plano do PDF perde o que diz se o valor é crédito ou débito: as duas
colunas existem, e a única diferença entre elas é a posição horizontal. Por isso
o parser lê o texto COM layout e classifica cada valor pela coluna onde ele
termina, usando as legendas do cabeçalho (`Crédito (R$)`, `Débito (R$)`,
`Saldo (R$)`) como régua. O saldo é ignorado: o PDF imprime saldo negativo sem
sinal, então ele não serve pra deduzir nada.

Mais o que a amostra real mostra:

- A data só aparece na primeira transação do dia; as seguintes herdam.
- O cabeçalho se repete a cada folha (`Folha: N/M`), e toda folha tem o seu —
  folha sem cabeçalho é erro, porque sem a régua não dá pra saber a coluna.
- A última folha fecha com `Total <créditos> <débitos> <saldo>`. Quando ela
  existe, as somas são conferidas: linha perdida na extração não entra no ledger
  em silêncio.
- `Docto.` vai pra `external_id`, igual ao CSV — é o que distingue dois
  lançamentos de mesma data, mesmo histórico e mesmo valor.

Gramática validada contra o extrato real (de setembro a novembro de 2026, 9 folhas, 139
lançamentos): a cadeia de saldo fecha linha a linha e as somas batem com a linha
`Total`.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from finance.imports.pdf_text import extract_layout_pages, extract_text
from finance.imports.record import ImportedRecord
from finance.model.errors import FinanceError
from finance.model.money import format_amount, parse_amount

PDF_EXTENSION = ".pdf"
PDF_MAGIC = "%PDF"
CREDIT_CAPTION = "Crédito (R$)"
DEBIT_CAPTION = "Débito (R$)"
BALANCE_CAPTION = "Saldo (R$)"
MARKERS = ("Bradesco", "Docto.", CREDIT_CAPTION, DEBIT_CAPTION)
DATE_FORMAT = "%d/%m/%Y"
DOCUMENT_DIGITS = 7
NAME_SEPARATOR = " — "
ZERO = Decimal("0")

AMOUNT = r"\d{1,3}(?:\.\d{3})*,\d{2}"
VALUES = rf"(?P<values>{AMOUNT}(?:\s+{AMOUNT})*)"
TRANSACTION = re.compile(
    rf"^\s*(?:(?P<date>\d{{2}}/\d{{2}}/\d{{4}})\s+)?(?P<history>\S.*?)\s+"
    rf"(?P<document>\d{{{DOCUMENT_DIGITS}}})\s+{VALUES}\s*$"
)
TOTAL = re.compile(rf"^\s*Total\s+{VALUES}\s*$")
AMOUNT_IN_VALUES = re.compile(AMOUNT)
COUNTERPARTY = re.compile(r"^(?:DES|REM):\s*(?P<name>\S.*?)(?:\s+\d{2}/\d{2})?$")
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


@dataclass(frozen=True)
class _Ruler:
    """Onde uma coluna acaba e a próxima começa, lida das legendas do cabeçalho."""

    credit_edge: float
    debit_edge: float


@dataclass
class _Row:
    date: date
    amount: Decimal
    history: str
    document: str
    name: str = field(default="")

    def record(self) -> ImportedRecord:
        description = f"{self.history}{NAME_SEPARATOR}{self.name}" if self.name else self.history
        return ImportedRecord(
            date=self.date,
            amount=self.amount,
            description=description,
            external_id=self.document,
        )


def parse_statement_pages(pages: Sequence[str]) -> list[ImportedRecord]:
    """Lançamentos de um extrato, na ordem do documento.

    Cada página é o texto com layout preservado (`extract_layout_pages`): sem as
    posições horizontais não há como separar crédito de débito.
    """
    rows: list[_Row] = []
    totals: tuple[Decimal, Decimal] | None = None
    current: date | None = None
    for page in pages:
        lines = [line.rstrip() for line in page.splitlines()]
        ruler, start = _ruler(lines)
        for line in lines[start:]:
            transaction = TRANSACTION.match(line)
            if transaction is not None:
                row = _row(transaction, ruler, current)
                current = row.date
                rows.append(row)
                continue
            total = TOTAL.match(line)
            if total is not None:
                totals = _totals(total, ruler)
                continue
            name = _counterparty(line)
            if name and rows and not rows[-1].name:
                rows[-1].name = name
    _check_totals(rows, totals)
    return [row.record() for row in rows]


def _ruler(lines: Sequence[str]) -> tuple[_Ruler, int]:
    for index, line in enumerate(lines):
        if not all(caption in line for caption in (CREDIT_CAPTION, DEBIT_CAPTION, BALANCE_CAPTION)):
            continue
        credit = line.index(CREDIT_CAPTION) + len(CREDIT_CAPTION)
        debit = line.index(DEBIT_CAPTION) + len(DEBIT_CAPTION)
        balance = line.index(BALANCE_CAPTION) + len(BALANCE_CAPTION)
        return _Ruler((credit + debit) / 2, (debit + balance) / 2), index + 1
    raise FinanceError(
        "folha do extrato do Bradesco sem o cabeçalho "
        f"{CREDIT_CAPTION} / {DEBIT_CAPTION} / {BALANCE_CAPTION}: sem ele não dá pra "
        "saber se o valor é entrada ou saída. O layout mudou — não importe adivinhando."
    )


def _row(match: re.Match[str], ruler: _Ruler, current: date | None) -> _Row:
    credit, debit = _split(match, ruler)
    line = match.group(0).strip()
    if credit is not None and debit is not None:
        raise FinanceError(f"lançamento com crédito e débito na mesma linha: {line!r}")
    if credit is None and debit is None:
        raise FinanceError(f"lançamento sem crédito nem débito: {line!r}")
    return _Row(
        date=_date(match.group("date"), current, line),
        amount=credit if credit is not None else -(debit or ZERO),
        history=WHITESPACE.sub(" ", match.group("history")).strip(),
        document=match.group("document"),
    )


def _split(match: re.Match[str], ruler: _Ruler) -> tuple[Decimal | None, Decimal | None]:
    """Valor de crédito e de débito da linha; o saldo (coluna da direita) é descartado."""
    credit: Decimal | None = None
    debit: Decimal | None = None
    offset = match.start("values")
    for found in AMOUNT_IN_VALUES.finditer(match.group("values")):
        end = offset + found.end()
        if end <= ruler.credit_edge:
            credit = parse_amount(found.group())
        elif end <= ruler.debit_edge:
            debit = parse_amount(found.group())
    return credit, debit


def _date(text: str | None, current: date | None, line: str) -> date:
    """Data da linha, herdada da primeira transação do dia quando a coluna vem vazia."""
    if text is None:
        if current is None:
            raise FinanceError(
                f"primeiro lançamento do extrato do Bradesco sem data: {line!r}. "
                "Sem a data da primeira transação do dia não há o que herdar."
            )
        return current
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as exc:
        raise FinanceError(f"data inválida no extrato do Bradesco: {line!r}") from exc


def _counterparty(line: str) -> str:
    """Nome do favorecido (`DES:`) ou do remetente (`REM:`), sem o dia/mês da operação."""
    match = COUNTERPARTY.match(line.strip())
    return "" if match is None else match.group("name").strip()


def _totals(match: re.Match[str], ruler: _Ruler) -> tuple[Decimal, Decimal]:
    credit, debit = _split(match, ruler)
    return credit or ZERO, debit or ZERO


def _check_totals(rows: Sequence[_Row], totals: tuple[Decimal, Decimal] | None) -> None:
    if totals is None:
        return
    credit = sum((row.amount for row in rows if row.amount > ZERO), ZERO)
    debit = -sum((row.amount for row in rows if row.amount < ZERO), ZERO)
    if (credit, debit) == totals:
        return
    raise FinanceError(
        f"o extrato do Bradesco não fecha com a linha Total: li {format_amount(credit)} de "
        f"crédito e {format_amount(debit)} de débito, o PDF soma {format_amount(totals[0])} e "
        f"{format_amount(totals[1])}. Algum lançamento ficou de fora — não importe adivinhando."
    )
