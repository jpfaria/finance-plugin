"""`finance transfer`: o pagamento da fatura sai da despesa do mês e vira transferência."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app
from finance.ledger.store import LedgerStore


def _run(*args: str, code: int = 0) -> str:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == code, result.output
    return result.output


def _add(account: str, amount: str, desc: str, when: str, category: str = "") -> None:
    args = ["add", "--account", account, "--amount", amount, "--desc", desc, "--date", when]
    if category:
        args += ["--category", category]
    _run(*args)


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    _add("bra", "5000", "salario", "2026-11-01", "renda/salario")
    _add("nu-card", "-700", "compra no cartao", "2026-11-04", "casa/luz")
    _add("bra", "-700", "pagamento da fatura", "2026-11-09")
    _add("nu-card", "700", "Pagamento recebido", "2026-11-07")
    return data_root


def _ids(output: str) -> list[str]:
    ids: list[str] = json.loads(output)[0]["ids"]
    return ids


def _groups(data_root: Path) -> dict[str, str]:
    return {e.description: e.transfer_group for e in LedgerStore(data_root).load_all()}


def test_candidates_find_the_two_legs_of_the_invoice_payment(env: Path) -> None:
    rows = json.loads(_run("transfer", "--json"))
    assert len(rows) == 1
    assert rows[0]["amount"] == "700.00"
    assert rows[0]["days_apart"] == 2
    assert rows[0]["out"]["description"] == "pagamento da fatura"
    assert rows[0]["in"]["description"] == "Pagamento recebido"


def test_marking_the_pair_takes_it_out_of_the_month_report(env: Path) -> None:
    before = json.loads(_run("report", "month", "--month", "2026-11", "--json"))
    assert (before["income"], before["expenses"]) == ("5700.00", "1400.00")

    ids = _ids(_run("transfer", "--json"))
    out = _run("transfer", "set", *ids)
    assert "2 perna(s)" in out

    after = json.loads(_run("report", "month", "--month", "2026-11", "--json"))
    assert (after["income"], after["expenses"]) == ("5000.00", "700.00")
    groups = _groups(env)
    assert groups["pagamento da fatura"] == groups["Pagamento recebido"] != ""
    assert _run("transfer", "--json").strip() == "[]"


def test_clear_puts_the_pair_back(env: Path) -> None:
    ids = _ids(_run("transfer", "--json"))
    _run("transfer", "set", *ids)
    assert "2 lançamento(s)" in _run("transfer", "clear", *ids)
    after = json.loads(_run("report", "month", "--month", "2026-11", "--json"))
    assert (after["income"], after["expenses"]) == ("5700.00", "1400.00")


def test_a_lone_leg_needs_force(env: Path) -> None:
    ids = _ids(_run("transfer", "--json"))
    assert "não parece transferência" in _run("transfer", "set", ids[0], code=1)
    _run("transfer", "set", ids[0], "--force")
    assert _groups(env)["pagamento da fatura"] == ids[0]


def test_an_entry_marked_twice_is_an_error(env: Path) -> None:
    ids = _ids(_run("transfer", "--json"))
    _run("transfer", "set", *ids)
    assert "já marcado" in _run("transfer", "set", *ids, code=1)


def test_a_transfer_leg_is_not_asked_for_a_category(env: Path) -> None:
    pending = json.loads(_run("categorize", "--json"))
    assert "pagamento da fatura" in [row["description"] for row in pending]
    _run("transfer", "set", *_ids(_run("transfer", "--json")))
    pending = json.loads(_run("categorize", "--json"))
    assert [row["description"] for row in pending] == []
