from pathlib import Path

from finance.ledger.paths import ledger_files, month_file


def test_month_file_and_listing(tmp_path: Path) -> None:
    assert month_file(tmp_path, 2026, 9) == tmp_path / "ledger" / "2026-09.csv"
    (tmp_path / "ledger").mkdir()
    for name in ("2026-10.csv", "2026-09.csv", "notes.txt"):
        (tmp_path / "ledger" / name).write_text("", encoding="utf-8")
    assert [p.name for p in ledger_files(tmp_path)] == ["2026-09.csv", "2026-10.csv"]


def test_listing_without_ledger_dir_is_empty(tmp_path: Path) -> None:
    assert ledger_files(tmp_path) == []
