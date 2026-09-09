from pathlib import Path

from finance.config.accounts import load_accounts


def test_group_is_optional_and_read(tmp_path: Path) -> None:
    p = tmp_path / "accounts.yaml"
    p.write_text(
        "accounts:\n"
        "  - {id: a, name: A, bank: nubank, type: checking, group: pessoal}\n"
        "  - {id: b, name: B, bank: nubank, type: checking}\n",
        encoding="utf-8",
    )
    accounts = load_accounts(p)
    assert accounts["a"].group == "pessoal"
    assert accounts["b"].group == ""


def test_accounts_in_group_filters(tmp_path: Path) -> None:
    from finance.config.accounts import accounts_in_group

    p = tmp_path / "accounts.yaml"
    p.write_text(
        "accounts:\n"
        "  - {id: a, name: A, bank: nubank, type: checking, group: pessoal}\n"
        "  - {id: b, name: B, bank: bradesco, type: checking, group: pj}\n"
        "  - {id: c, name: C, bank: bradesco, type: checking}\n",
        encoding="utf-8",
    )
    accounts = load_accounts(p)
    assert set(accounts_in_group(accounts, None)) == {"a", "b", "c"}
    assert set(accounts_in_group(accounts, "pj")) == {"b"}
    assert set(accounts_in_group(accounts, "pessoal")) == {"a"}
