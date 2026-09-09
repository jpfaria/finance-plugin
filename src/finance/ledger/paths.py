"""Month-file naming and listing under a data root."""

from pathlib import Path

LEDGER_DIR = "ledger"


def month_file(root: Path, year: int, month: int) -> Path:
    return root / LEDGER_DIR / f"{year:04d}-{month:02d}.csv"


def ledger_files(root: Path) -> list[Path]:
    folder = root / LEDGER_DIR
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("????-??.csv") if p.is_file())
