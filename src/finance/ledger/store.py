"""LedgerStore: append entries to, and load entries from, the month CSV files."""

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from finance.ledger.csv_io import read_month_file, write_month_file
from finance.ledger.paths import ledger_files, month_file
from finance.model.entry import Entry
from finance.model.errors import FinanceError


class LedgerStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def append(self, entries: Iterable[Entry]) -> None:
        by_month: dict[tuple[int, int], list[Entry]] = defaultdict(list)
        for entry in entries:
            by_month[(entry.date.year, entry.date.month)].append(entry)
        existing_ids = {e.id for e in self.load_all()}
        for (year, month), new in by_month.items():
            for entry in new:
                if entry.id in existing_ids:
                    raise FinanceError(f"id duplicado no ledger: {entry.id}")
                existing_ids.add(entry.id)
            path = month_file(self.root, year, month)
            write_month_file(path, [*read_month_file(path), *new])

    def replace(self, updated: Iterable[Entry], removed_ids: set[str]) -> None:
        by_id = {e.id: e for e in updated}
        pending = set(by_id)
        for path in ledger_files(self.root):
            current = read_month_file(path)
            kept = [by_id.get(e.id, e) for e in current if e.id not in removed_ids]
            pending -= {e.id for e in current}
            if kept != current:
                write_month_file(path, kept)
        if pending:
            raise FinanceError(f"lançamento não encontrado: {', '.join(sorted(pending))}")

    def load_month(self, year: int, month: int) -> list[Entry]:
        return read_month_file(month_file(self.root, year, month))

    def load_all(self) -> list[Entry]:
        return [entry for path in ledger_files(self.root) for entry in read_month_file(path)]
