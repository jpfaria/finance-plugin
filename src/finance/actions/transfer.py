"""Mark ledger entries as the legs of one transfer, so the reports stop counting them.

Dinheiro que só muda de lugar não é receita nem despesa: o pagamento da fatura do
cartão, um PIX entre contas do próprio dono. As duas pernas ficam no ledger (cada
extrato traz a sua), mas com o mesmo `transfer_group` o `report month` as ignora e
o `report invoice` sabe que aquele crédito é o pagamento da fatura.

O grupo é o menor id entre as pernas — a mesma convenção do `installment_group`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal

from finance.model.entry import Entry
from finance.model.errors import FinanceError

ZERO = Decimal("0")
DEFAULT_WINDOW_DAYS = 5


@dataclass(frozen=True)
class Candidate:
    """Duas pernas que parecem ser uma transferência: valores opostos, contas diferentes."""

    out_leg: Entry
    in_leg: Entry

    @property
    def days_apart(self) -> int:
        return abs((self.in_leg.date - self.out_leg.date).days)


def candidates(
    entries: Sequence[Entry], *, window_days: int = DEFAULT_WINDOW_DAYS
) -> list[Candidate]:
    """Pares de pernas ainda não marcadas: valores opostos, contas diferentes, perto no tempo.

    Cada lançamento entra em um par só — o mais próximo no tempo vence, e o resto
    daquela perna é descartado. Nada é gravado aqui: quem decide é o usuário, com
    `transfer set`, porque dois lançamentos opostos podem ser coincidência.
    """
    window = timedelta(days=window_days)
    free = [e for e in entries if not e.is_transfer]
    pairs = sorted(
        (
            Candidate(out_leg=out, in_leg=into)
            for out in free
            if out.amount < ZERO
            for into in free
            if into.amount == -out.amount
            and into.account != out.account
            and abs(into.date - out.date) <= window
        ),
        key=lambda c: (c.days_apart, c.out_leg.date, c.out_leg.id, c.in_leg.id),
    )
    taken: set[str] = set()
    chosen: list[Candidate] = []
    for pair in pairs:
        if pair.out_leg.id in taken or pair.in_leg.id in taken:
            continue
        taken.update({pair.out_leg.id, pair.in_leg.id})
        chosen.append(pair)
    return sorted(chosen, key=lambda c: (c.out_leg.date, c.out_leg.id))


def link(entries: Sequence[Entry], entry_ids: Sequence[str], *, force: bool = False) -> list[Entry]:
    """As pernas de `entry_ids` com o mesmo `transfer_group`, prontas pra gravar.

    Sem `force` a soma das pernas tem que ser zero: é o que prova que o dinheiro
    só mudou de lugar. Uma perna sozinha (a outra está num extrato que não foi
    importado) nunca soma zero, então exige `force` — marcar é decisão do usuário,
    não adivinhação. Um lançamento já marcado é erro: `transfer clear` primeiro,
    senão a perna que sobrou no grupo antigo fica órfã.
    """
    legs = _legs(entries, entry_ids)
    already = [e.id for e in legs if e.is_transfer]
    if already:
        raise FinanceError(
            f"já marcado(s) como transferência: {', '.join(already)}. "
            "Use `finance transfer clear` antes."
        )
    total = sum((e.amount for e in legs), ZERO)
    if total != ZERO and not force:
        raise FinanceError(
            f"as pernas somam {total} em vez de zero: não parece transferência. "
            "Se a outra perna não está no ledger, repita com --force."
        )
    group = min(e.id for e in legs)
    return [replace(e, transfer_group=group) for e in legs]


def clear(entries: Sequence[Entry], entry_ids: Sequence[str]) -> list[Entry]:
    """As pernas de `entry_ids` sem marca de transferência, prontas pra gravar."""
    legs = _legs(entries, entry_ids)
    loose = [e.id for e in legs if not e.is_transfer]
    if loose:
        raise FinanceError(f"não está marcado como transferência: {', '.join(loose)}")
    return [replace(e, transfer_group="") for e in legs]


def _legs(entries: Sequence[Entry], entry_ids: Sequence[str]) -> list[Entry]:
    if not entry_ids:
        raise FinanceError("informe pelo menos um lançamento")
    if len(set(entry_ids)) != len(entry_ids):
        raise FinanceError("id repetido na lista")
    by_id = {e.id: e for e in entries}
    missing = [i for i in entry_ids if i not in by_id]
    if missing:
        raise FinanceError(f"lançamento não encontrado: {', '.join(missing)}")
    return [by_id[i] for i in entry_ids]
