from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app


def test_rebuild_creates_db(
    monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path
) -> None:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    result = CliRunner().invoke(app, ["rebuild"])
    assert result.exit_code == 0, result.output
    assert "cache reconstruído: 0 lançamento(s)" in result.output
    assert (cache_root / "finance.db").is_file()
