"""Rateio: uma cobrança só que paga duas coisas diferentes.

A fatura traz um lançamento de 868 que é a soma de duas assinaturas; o relatório
por categoria precisa dos dois pedaços. O rateio troca o lançamento por partes
que somam exatamente o mesmo valor, cada uma com sua categoria.

A primeira parte mantém o id do original, pra nada que aponte pra ele (grupo de
parcela, conciliação) ficar órfão. Todas as partes guardam o `import_hash` do
original, que é a chave de deduplicação: reimportar o extrato continua achando a
cobrança como já importada em vez de gravá-la de novo inteira.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from finance.model.entry import CategorySource, Entry
from finance.model.errors import FinanceError
from finance.model.money import format_amount

MIN_PARTS = 2


@dataclass(frozen=True)
class Part:
    amount: Decimal
    category: str


def split(
    entries: Sequence[Entry],
    entry_id: str,
    parts: Sequence[Part],
    categories: frozenset[str],
    ids: Iterator[str],
) -> list[Entry]:
    """As partes que substituem o lançamento, na ordem recebida (a 1ª herda o id)."""
    original = _entry(entries, entry_id)
    _check(original, parts, categories)
    sign = -1 if original.amount < 0 else 1
    total = len(parts)
    return [
        replace(
            original,
            id=original.id if index == 0 else next(ids),
            amount=sign * part.amount,
            description=f"{original.description} - Rateio {index + 1}/{total}",
            category=part.category,
            category_source=CategorySource.MANUAL,
        )
        for index, part in enumerate(parts)
    ]


def _entry(entries: Sequence[Entry], entry_id: str) -> Entry:
    for entry in entries:
        if entry.id == entry_id:
            return entry
    raise FinanceError(f"lançamento não encontrado: {entry_id!r}")


def _check(original: Entry, parts: Sequence[Part], categories: frozenset[str]) -> None:
    if original.is_transfer:
        raise FinanceError(
            "esse lançamento é perna de transferência: não entra em relatório, "
            "não há o que ratear. Use `finance transfer clear` antes."
        )
    if len(parts) < MIN_PARTS:
        raise FinanceError(f"um rateio precisa de pelo menos {MIN_PARTS} partes")
    for part in parts:
        if part.amount <= 0:
            raise FinanceError(f"valor de parte inválido: {format_amount(part.amount)}")
        if part.category not in categories:
            raise FinanceError(f"categoria desconhecida: {part.category!r}")
    total = sum((p.amount for p in parts), Decimal("0"))
    expected = abs(original.amount)
    if total != expected:
        raise FinanceError(
            f"as partes somam {format_amount(total)} em vez de {format_amount(expected)}"
        )
