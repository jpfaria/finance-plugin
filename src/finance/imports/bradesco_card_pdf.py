"""Fatura do cartão Bradesco em PDF (o banco não exporta outro formato).

A fatura tem camada de texto e a tabela `Lançamentos` extrai como uma
linha por lançamento:

    DD/MM <histórico> <cidade> [US$ cotação] <valor>[ -]

- ` -` no fim é crédito (pagamento da fatura, estorno); sem ele, débito.
  O sinal final é o mesmo do cartão Nubank: compra negativa, pagamento
  positivo.
- A linha quebra em até `MAX_WRAPPED_LINES` quando a cidade não cabe na
  coluna, e a tabela continua depois do rodapé nas páginas seguintes —
  por isso o documento é varrido inteiro, sem delimitar seção.
- Parcela aparece colada ou separada no histórico (`...EDECO11/12`,
  `MP*LUVIN 10/12`), nunca como a palavra "Parcela"; vai pra descrição
  como `- Parcela N/M`, igual ao CSV do Nubank.
- A linha não tem ano. Toda compra é anterior ao fechamento, então
  dia/mês posterior ao vencimento é do ano anterior (parcela de uma
  compra antiga).
- Parcela fica com a data da COMPRA, não da cobrança. Como o que sai do
  bolso é a cobrança, a parcela é gravada no 1º do mês do vencimento —
  ver `_charge_date`.
"""

import re
from datetime import date
from pathlib import Path

from finance.imports.pdf_text import extract_text
from finance.imports.record import ImportedRecord
from finance.model.errors import FinanceError
from finance.model.money import parse_amount

PDF_EXTENSION = ".pdf"
PDF_MAGIC = "%PDF"
MARKERS = ("Bradesco", "Histórico de Lançamentos")

AMOUNT = r"\d{1,3}(?:\.\d{3})*,\d{2}"
TRANSACTION = re.compile(rf"^(\d{{2}})/(\d{{2}})\s+(\S.*?)\s+({AMOUNT})(\s-)?$")
TRANSACTION_START = re.compile(r"^\d{2}/\d{2}\s+\S")
DUE_DATE = re.compile(r"Vencimento\s+(\d{2})/(\d{2})/(\d{4})")
INSTALLMENT = re.compile(r"\s*(\d{2})/(\d{2})(?=\s|$)")
TRAILING_NUMBER = re.compile(r"\s+[\d.,]+$")
WHITESPACE = re.compile(r"\s+")
MAX_WRAPPED_LINES = 3


class BradescoCardPdf:
    name = "bradesco-card-pdf"

    def matches(self, path: Path, head: str) -> bool:
        if path.suffix.lower() != PDF_EXTENSION or not head.startswith(PDF_MAGIC):
            return False
        text = extract_text(path)
        return all(marker in text for marker in MARKERS)

    def parse(self, path: Path) -> list[ImportedRecord]:
        return parse_statement_text(extract_text(path))


def parse_statement_text(text: str) -> list[ImportedRecord]:
    """Lançamentos da fatura, na ordem do documento."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    due = _due_date(lines)
    records: list[ImportedRecord] = []
    index = 0
    while index < len(lines):
        if TRANSACTION_START.match(lines[index]):
            record, index = _read_transaction(lines, index, due)
            records.append(record)
        else:
            index += 1
    return records


def _due_date(lines: list[str]) -> date:
    match = DUE_DATE.search("\n".join(lines))
    if match is None:
        raise FinanceError(
            "fatura do Bradesco sem data de vencimento: sem ela não dá pra "
            "saber o ano dos lançamentos"
        )
    day, month, year = (int(group) for group in match.groups())
    return _date(year, month, day, context="vencimento")


def _read_transaction(lines: list[str], index: int, due: date) -> tuple[ImportedRecord, int]:
    joined = lines[index]
    last = index
    match = TRANSACTION.match(joined)
    while match is None and last + 1 < len(lines) and last - index < MAX_WRAPPED_LINES:
        if TRANSACTION_START.match(lines[last + 1]):
            break
        last += 1
        joined = f"{joined} {lines[last]}"
        match = TRANSACTION.match(joined)
    if match is None:
        raise FinanceError(
            f"lançamento sem valor na fatura do Bradesco: {lines[index]!r}. "
            "O layout mudou — não importe adivinhando."
        )
    day, month, middle, amount, credit = match.groups()
    value = parse_amount(amount)
    text, installment = _without_installment(middle)
    record = ImportedRecord(
        date=_charge_date(int(day), int(month), due, installment=bool(installment)),
        amount=value if credit else -value,
        description=_description(text, installment),
    )
    return record, last + 1


def _charge_date(day: int, month: int, due: date, *, installment: bool) -> date:
    """Quando o dinheiro sai: a data da linha, ou o 1º do mês do vencimento se é parcela.

    A fatura data cada parcela no dia da COMPRA original — uma parcela 8/12 de março
    aparece na fatura de novembro com 15/03. Guardar essa data joga a despesa num mês
    que já passou: nem o `report month` de novembro nem a fatura de novembro (a janela
    vai do fechamento anterior até o fechamento) enxergam ela.

    O 1º do mês do vencimento cai dentro da janela de qualquer cartão — ela começa no
    mês anterior e termina no dia do fechamento, que é no mínimo 1 —, então a parcela
    fica na fatura certa e no mês em que o dinheiro sai. O dia da compra se perde: o
    que interessa é a cobrança, e `- Parcela N/M` na descrição guarda o resto.
    """
    if installment:
        return date(due.year, due.month, 1)
    year = due.year if (month, day) <= (due.month, due.day) else due.year - 1
    return _date(year, month, day, context="lançamento")


def _date(year: int, month: int, day: int, context: str) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise FinanceError(
            f"data inválida no {context} da fatura: {day:02d}/{month:02d}/{year}"
        ) from exc


def _description(text: str, suffix: str) -> str:
    while (trailing := TRAILING_NUMBER.search(text)) is not None:
        text = text[: trailing.start()]
    return WHITESPACE.sub(" ", text).strip() + suffix


def _without_installment(middle: str) -> tuple[str, str]:
    match = INSTALLMENT.search(middle)
    if match is None:
        return middle, ""
    number, total = (int(group) for group in match.groups())
    if number > total:
        return middle, ""
    rest = f"{middle[: match.start()]} {middle[match.end() :]}"
    return rest, f" - Parcela {number}/{total}"
