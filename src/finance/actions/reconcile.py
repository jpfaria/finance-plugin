"""Match manual entries against imported ones; merge keeps the manual identity."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta

from finance.model.entry import Entry, Status


@dataclass(frozen=True)
class Match:
    manual: Entry
    imported: Entry


@dataclass(frozen=True)
class ReconcileResult:
    matches: list[Match]
    unmatched_imported: list[Entry]
    stale_manual: list[Entry]


def _is_imported(entry: Entry) -> bool:
    return entry.status is Status.CONFIRMED and entry.import_hash != ""


def _candidates(
    manuals: Sequence[Entry], imported: Sequence[Entry], window: timedelta
) -> list[tuple[timedelta, Entry, Entry]]:
    pairs: list[tuple[timedelta, Entry, Entry]] = []
    for m in manuals:
        for i in imported:
            # Imported lines carry no installment field; parcels are told apart by the
            # date window (one month apart), not by the manual's "n/N" label.
            if m.account != i.account or m.amount != i.amount:
                continue
            gap = abs(m.date - i.date)
            if gap <= window:
                pairs.append((gap, m, i))
    return sorted(pairs, key=lambda p: (p[0], p[1].id, p[2].id))


def reconcile(
    entries: Sequence[Entry], window_days: int, stale_days: int, today: date
) -> ReconcileResult:
    manuals = [e for e in entries if e.status is Status.MANUAL]
    imported = [e for e in entries if _is_imported(e)]
    taken_manual: set[str] = set()
    taken_imported: set[str] = set()
    matches: list[Match] = []
    for _, m, i in _candidates(manuals, imported, timedelta(days=window_days)):
        if m.id in taken_manual or i.id in taken_imported:
            continue
        taken_manual.add(m.id)
        taken_imported.add(i.id)
        matches.append(Match(m, i))
    stale_limit = timedelta(days=stale_days)
    return ReconcileResult(
        matches=matches,
        unmatched_imported=[i for i in imported if i.id not in taken_imported],
        stale_manual=[
            m for m in manuals if m.id not in taken_manual and today - m.date > stale_limit
        ],
    )


def merge(manual: Entry, imported: Entry) -> Entry:
    return replace(
        manual, status=Status.CONFIRMED, import_hash=imported.import_hash, source=imported.source
    )
