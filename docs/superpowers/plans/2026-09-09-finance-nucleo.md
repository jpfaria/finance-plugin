# finance v1 — Plano 1: núcleo (scaffold, modelo, ledger, `add`, cache, relatórios)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI `finance` que grava lançamentos manuais no ledger CSV versionado, reconstrói o cache SQLite e emite os relatórios `month`, `budget`, `balance`, `invoice`.

**Architecture:** Este repo é um plugin Claude Code (`finance-plugin`); os dados do usuário ficam no repo privado `finance` e chegam ao CLI por `FINANCE_DATA_DIR` (default `./data`). Pacote `src/finance/` em camadas finas: `model/` (dataclasses puras), `config/` (loaders YAML), `ledger/` (CSV canônico), `cache/` (SQLite regenerável), `reports/` (funções puras sobre o SQLite), `cli/` (só wiring Typer + render). Toda regra de negócio fica fora de `cli/` e é testada sem o CLI.

**Tech Stack:** Python 3.12, uv, typer, pyyaml, python-ulid, rich, sqlite3 (stdlib), pytest, ruff, mypy --strict.

**Spec:** `docs/superpowers/specs/2026-09-09-finance-v1-design.md`

## Global Constraints

- Código (identificadores, comentários de código) em inglês; docs, mensagens ao usuário, commits e skills em pt-BR.
- Um módulo = uma responsabilidade. `cli/` não contém regra de negócio.
- TDD red-first em toda task: teste escrito e visto FALHANDO antes da implementação (skill `dev` do `claude-plugin@xgodev`).
- Valores monetários sempre `Decimal` com 2 casas; negativo = saída, positivo = entrada.
- Nunca dados reais no repo: fixtures em `tests/` geradas em `tmp_path`.
- `data/` (no repo `finance`) é o canônico; `.cache/finance.db` é descartável e gitignorado.
- **Nada pessoal neste repo:** exemplos em `examples/data/` são fictícios; nenhum nome, valor ou extrato real.
- Antes de cada commit: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q` verdes.
- Conventional commits em pt-BR: `feat:`, `test:`, `chore:`, `docs:`.

---

## Estrutura de arquivos

```
pyproject.toml
uv.lock
CLAUDE.md
README.md
.claude/settings.json          # dev deste repo: claude-plugin@xgodev
.claude-plugin/plugin.json     # name: finance-plugin
.claude-plugin/marketplace.json # name: finance
.github/workflows/ci.yml
examples/data/accounts.yaml    # exemplo fictício
examples/data/categories.yaml
examples/data/budget.yaml
examples/data/rules.yaml       # vazio no plano 1
skills/                        # plano 2
src/finance/__init__.py       # __version__
src/finance/cli/__init__.py   # app Typer: registra subcomandos
src/finance/cli/add.py        # comando add
src/finance/cli/rebuild.py    # comando rebuild
src/finance/cli/report.py     # subcomandos report *
src/finance/cli/context.py    # resolve data_dir/cache_dir + carrega config
src/finance/render/output.py  # tabela rich ou JSON
src/finance/model/money.py    # parse/format Decimal
src/finance/model/dates.py    # add_months, parse_month
src/finance/model/account.py  # Account, AccountType
src/finance/model/entry.py    # Entry, Status
src/finance/model/errors.py   # FinanceError base
src/finance/config/accounts.py
src/finance/config/categories.py
src/finance/config/budget.py
src/finance/ledger/paths.py   # data_dir, cache_dir, month_file
src/finance/ledger/ids.py     # new_id (ULID)
src/finance/ledger/csv_io.py  # Entry <-> linha CSV, ler/escrever um mês
src/finance/ledger/store.py   # LedgerStore: append/load
src/finance/actions/add.py    # build_manual_entries (puro) + split_installments
src/finance/cache/schema.py   # DDL
src/finance/cache/rebuild.py  # rebuild(data_root, db_path)
src/finance/cache/connection.py # open_db com checagem de frescor
src/finance/reports/invoice_period.py
src/finance/reports/balance.py
src/finance/reports/invoice.py
src/finance/reports/month.py
tests/conftest.py             # fixture data_root com YAMLs de exemplo
tests/test_*.py               # um por módulo
```

---

### Task 1: Scaffold do projeto

**Files:**
- Create: `pyproject.toml`, `src/finance/__init__.py`, `src/finance/cli/__init__.py`, `tests/test_cli_version.py`, `CLAUDE.md`, `README.md`, `.claude/settings.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.github/workflows/ci.yml`

**Interfaces:**
- Produces: `finance.cli.app` (objeto Typer) e `finance.__version__`.

- [ ] **Step 1: Criar `pyproject.toml`**

```toml
[project]
name = "finance"
version = "0.1.0"
description = "Controle financeiro pessoal via Claude Code"
requires-python = ">=3.12"
dependencies = [
  "typer>=0.12",
  "pyyaml>=6",
  "python-ulid>=2",
  "rich>=13",
]

[project.scripts]
finance = "finance.cli:app"

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6", "mypy>=1.11", "types-PyYAML"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/finance"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "SIM", "RUF"]

[tool.mypy]
strict = true
python_version = "3.12"
files = ["src", "tests"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_cli_version.py`:
```python
from typer.testing import CliRunner

from finance import __version__
from finance.cli import app


def test_version_flag_prints_version() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv sync --group dev && uv run pytest tests/test_cli_version.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'finance'`

- [ ] **Step 4: Implementar o mínimo**

`src/finance/__init__.py`:
```python
"""Controle financeiro pessoal via Claude Code."""

__version__ = "0.1.0"
```

`src/finance/cli/__init__.py`:
```python
"""Typer app: only wiring, no business rules."""

from typing import Annotated

import typer

from finance import __version__

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Mostra a versão."),
    ] = False,
) -> None:
    """finance — controle financeiro pessoal."""
```

- [ ] **Step 5: Rodar e ver passar**

Run: `uv run pytest tests/test_cli_version.py -v`
Expected: PASS

- [ ] **Step 6: Lint/format/mypy**

Run: `uv run ruff check . && uv run ruff format . && uv run mypy`
Expected: sem erros.

- [ ] **Step 7: Arquivos de projeto**

`.claude/settings.json`:
```json
{
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true,
    "claude-plugin@xgodev": true
  }
}
```

`.claude-plugin/plugin.json`:
```json
{
  "name": "finance-plugin",
  "description": "Controle financeiro pessoal via Claude Code: skills + CLI Python sobre um ledger CSV versionado.",
  "version": "0.1.0",
  "author": { "name": "João Paulo" },
  "homepage": "https://github.com/jpfaria/finance-plugin"
}
```

`.claude-plugin/marketplace.json`:
```json
{
  "name": "finance",
  "owner": { "name": "João Paulo", "url": "https://github.com/jpfaria/finance-plugin" },
  "plugins": [
    {
      "name": "finance-plugin",
      "source": "./",
      "description": "Controle financeiro pessoal via Claude Code: skills + CLI Python sobre um ledger CSV versionado."
    }
  ]
}
```

`CLAUDE.md`:
```markdown
# finance-plugin — Claude Code

Plugin Claude Code de controle financeiro pessoal. Spec: `docs/superpowers/specs/2026-09-09-finance-v1-design.md`.

## Regras

- **Nada pessoal aqui.** Este repo é público e vira plugin: nenhum nome de conta, valor, extrato ou preferência de uma pessoa. Dados do usuário moram no repo privado dele (`data/`), lidos via `FINANCE_DATA_DIR`. Exemplos são fictícios, em `examples/data/`.
- **Idioma:** código em inglês; docs, mensagens ao usuário, skills, commits e issues em pt-BR.
- **Disciplina de código:** skill `dev` do `claude-plugin@xgodev` (TDD red-first, um módulo = uma responsabilidade). Sem exceção.
- **Regra de negócio só no CLI (`src/finance/`), nunca na skill.** Skill sabe qual comando rodar e como conversar.
- **`data/` do usuário é o canônico.** `.cache/` e `imports/` são descartáveis e gitignorados. Nunca commitar extrato, nem de exemplo.
- **Dinheiro é `Decimal`** com 2 casas. Negativo = saída, positivo = entrada.
- Antes de commitar: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q`.

## Layout

`src/finance/{model,config,ledger,actions,cache,reports,render,cli}` — ver `docs/superpowers/plans/`.
```

`README.md`:
```markdown
# finance-plugin

Plugin Claude Code de controle financeiro pessoal. Lançamentos e extratos viram CSV versionado no `data/` do seu repo privado; um SQLite descartável em `.cache/` serve os relatórios.

## Instalar

```bash
claude plugin marketplace add jpfaria/finance-plugin
claude plugin install finance-plugin@finance
```

## Desenvolver

```bash
uv sync --group dev
uv run finance --help
FINANCE_DATA_DIR=examples/data uv run finance report balance
```

Design: `docs/superpowers/specs/2026-09-09-finance-v1-design.md`.
```

`.github/workflows/ci.yml`:
```yaml
name: ci
on:
  push:
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --group dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy
      - run: uv run pytest -q
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src tests CLAUDE.md README.md .claude .claude-plugin .github
git commit -m "chore: scaffold do projeto (uv, typer, ruff, mypy, pytest, CI)"
```

---

### Task 2: Dinheiro (`model/money.py`) e erros base

**Files:**
- Create: `src/finance/model/__init__.py` (vazio), `src/finance/model/errors.py`, `src/finance/model/money.py`
- Test: `tests/test_money.py`

**Interfaces:**
- Produces: `FinanceError(Exception)`; `parse_amount(text: str) -> Decimal`; `format_amount(value: Decimal) -> str`; `CENTS = Decimal("0.01")`.

- [ ] **Step 1: Teste que falha**

`tests/test_money.py`:
```python
from decimal import Decimal

import pytest

from finance.model.errors import FinanceError
from finance.model.money import format_amount, parse_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("50", Decimal("50.00")),
        ("-12.5", Decimal("-12.50")),
        ("1.234,56", Decimal("1234.56")),
        ("R$ 99,90", Decimal("99.90")),
        ("0.005", Decimal("0.01")),
    ],
)
def test_parse_amount(text: str, expected: Decimal) -> None:
    assert parse_amount(text) == expected


def test_parse_amount_rejects_garbage() -> None:
    with pytest.raises(FinanceError, match="valor inválido"):
        parse_amount("abc")


def test_format_amount_two_places() -> None:
    assert format_amount(Decimal("-7")) == "-7.00"
    assert format_amount(Decimal("1234.5")) == "1234.50"
```

- [ ] **Step 2: Ver falhar**

Run: `uv run pytest tests/test_money.py -v`
Expected: FAIL — `ModuleNotFoundError: finance.model`

- [ ] **Step 3: Implementar**

`src/finance/model/errors.py`:
```python
"""Base exception for every user-facing failure."""


class FinanceError(Exception):
    """Raised with a pt-BR message meant to be shown to the user."""
```

`src/finance/model/money.py`:
```python
"""Decimal parsing and formatting for BRL amounts."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from finance.model.errors import FinanceError

CENTS = Decimal("0.01")


def parse_amount(text: str) -> Decimal:
    raw = text.strip().replace("R$", "").replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw).quantize(CENTS, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise FinanceError(f"valor inválido: {text!r}") from exc


def format_amount(value: Decimal) -> str:
    return f"{value.quantize(CENTS, rounding=ROUND_HALF_UP):.2f}"
```

- [ ] **Step 4: Ver passar** — `uv run pytest tests/test_money.py -v` → PASS
- [ ] **Step 5: Commit** — `git add src/finance/model tests/test_money.py && git commit -m "feat: parse e format de valores em Decimal"`

---

### Task 3: Datas (`model/dates.py`)

**Files:**
- Create: `src/finance/model/dates.py`
- Test: `tests/test_dates.py`

**Interfaces:**
- Produces: `add_months(d: date, n: int) -> date` (dia clampado ao fim do mês); `parse_month(text: str) -> tuple[int, int]` aceita `YYYY-MM`; `clamp_day(year: int, month: int, day: int) -> date`.

- [ ] **Step 1: Teste que falha**

`tests/test_dates.py`:
```python
from datetime import date

import pytest

from finance.model.dates import add_months, clamp_day, parse_month
from finance.model.errors import FinanceError


def test_add_months_clamps_to_month_end() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 1, 31), 2) == date(2026, 3, 31)
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)


def test_add_months_negative() -> None:
    assert add_months(date(2026, 3, 31), -1) == date(2026, 2, 28)


def test_clamp_day() -> None:
    assert clamp_day(2026, 2, 31) == date(2026, 2, 28)
    assert clamp_day(2026, 4, 10) == date(2026, 4, 10)


def test_parse_month() -> None:
    assert parse_month("2026-09") == (2026, 9)


@pytest.mark.parametrize("bad", ["2026", "09/2026", "2026-13"])
def test_parse_month_rejects(bad: str) -> None:
    with pytest.raises(FinanceError, match="mês inválido"):
        parse_month(bad)
```

- [ ] **Step 2: Ver falhar** — `uv run pytest tests/test_dates.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: Implementar**

`src/finance/model/dates.py`:
```python
"""Calendar helpers: month arithmetic and YYYY-MM parsing."""

import calendar
import re
from datetime import date

from finance.model.errors import FinanceError

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


def clamp_day(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def add_months(d: date, n: int) -> date:
    index = d.year * 12 + (d.month - 1) + n
    year, month0 = divmod(index, 12)
    return clamp_day(year, month0 + 1, d.day)


def parse_month(text: str) -> tuple[int, int]:
    match = _MONTH_RE.match(text.strip())
    if not match:
        raise FinanceError(f"mês inválido: {text!r} (use AAAA-MM)")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise FinanceError(f"mês inválido: {text!r} (use AAAA-MM)")
    return year, month
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git commit -am "feat: aritmética de meses e parse AAAA-MM"` (após `git add src/finance/model/dates.py tests/test_dates.py`)

---

### Task 4: Modelo `Account` e `Entry`

**Files:**
- Create: `src/finance/model/account.py`, `src/finance/model/entry.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Produces:
  - `AccountType(StrEnum)`: `CHECKING="checking"`, `CREDIT="credit"`.
  - `Account(id, name, bank, type, closing_day: int|None=None, due_day: int|None=None)` frozen dataclass; `is_credit` property.
  - `Status(StrEnum)`: `MANUAL="manual"`, `CONFIRMED="confirmed"`.
  - `Entry(id, date, account, amount, description, category="", tags=(), installment="", installment_group="", transfer_group="", status=Status.MANUAL, source="manual", import_hash="")` frozen dataclass; `is_transfer` property (`transfer_group != ""`).

- [ ] **Step 1: Teste que falha**

`tests/test_model.py`:
```python
from datetime import date
from decimal import Decimal

from finance.model.account import Account, AccountType
from finance.model.entry import Entry, Status


def test_account_is_credit() -> None:
    card = Account(id="nu-card", name="Nubank cartão", bank="nubank", type=AccountType.CREDIT, closing_day=3, due_day=10)
    conta = Account(id="nu", name="Nubank conta", bank="nubank", type=AccountType.CHECKING)
    assert card.is_credit
    assert not conta.is_credit


def test_entry_defaults_and_transfer_flag() -> None:
    e = Entry(id="01H", date=date(2026, 9, 1), account="nu", amount=Decimal("-50.00"), description="uber")
    assert e.status is Status.MANUAL
    assert e.source == "manual"
    assert e.category == ""
    assert e.tags == ()
    assert not e.is_transfer
    t = Entry(id="01J", date=date(2026, 9, 1), account="nu", amount=Decimal("-500.00"), description="fatura", transfer_group="G1")
    assert t.is_transfer
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.model.account`

- [ ] **Step 3: Implementar**

`src/finance/model/account.py`:
```python
"""Account: a checking account or a credit card."""

from dataclasses import dataclass
from enum import StrEnum


class AccountType(StrEnum):
    CHECKING = "checking"
    CREDIT = "credit"


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    bank: str
    type: AccountType
    closing_day: int | None = None
    due_day: int | None = None

    @property
    def is_credit(self) -> bool:
        return self.type is AccountType.CREDIT
```

`src/finance/model/entry.py`:
```python
"""Entry: one ledger line (a purchase, income, or one leg of a transfer)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Status(StrEnum):
    MANUAL = "manual"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class Entry:
    id: str
    date: date
    account: str
    amount: Decimal
    description: str
    category: str = ""
    tags: tuple[str, ...] = ()
    installment: str = ""
    installment_group: str = ""
    transfer_group: str = ""
    status: Status = Status.MANUAL
    source: str = "manual"
    import_hash: str = ""

    @property
    def is_transfer(self) -> bool:
        return self.transfer_group != ""
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git add src/finance/model tests/test_model.py && git commit -m "feat: modelo Account e Entry"`

---

### Task 5: Loaders de config (`accounts.yaml`, `categories.yaml`, `budget.yaml`)

**Files:**
- Create: `src/finance/config/__init__.py` (vazio), `src/finance/config/accounts.py`, `src/finance/config/categories.py`, `src/finance/config/budget.py`
- Test: `tests/conftest.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `load_accounts(path: Path) -> dict[str, Account]`
  - `load_categories(path: Path) -> frozenset[str]` (caminhos `grupo/item`)
  - `load_budget(path: Path, categories: frozenset[str]) -> dict[str, Decimal]`
- Formatos:

```yaml
# accounts.yaml
accounts:
  - id: nu
    name: Nubank conta
    bank: nubank
    type: checking
  - id: nu-card
    name: Nubank cartão
    bank: nubank
    type: credit
    closing_day: 3
    due_day: 10
```
```yaml
# categories.yaml
casa: [aluguel, condominio, luz]
transporte: [uber, combustivel]
renda: [salario]
```
```yaml
# budget.yaml
transporte/uber: 300
casa/luz: 250
```

- [ ] **Step 1: Fixture compartilhada**

`tests/conftest.py`:
```python
from pathlib import Path

import pytest

ACCOUNTS_YAML = """
accounts:
  - id: nu
    name: Nubank conta
    bank: nubank
    type: checking
  - id: nu-card
    name: Nubank cartão
    bank: nubank
    type: credit
    closing_day: 3
    due_day: 10
  - id: bra
    name: Bradesco conta
    bank: bradesco
    type: checking
"""

CATEGORIES_YAML = """
casa: [aluguel, condominio, luz]
transporte: [uber, combustivel]
renda: [salario]
"""

BUDGET_YAML = """
transporte/uber: 300
casa/luz: 250
"""


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    (root / "ledger").mkdir(parents=True)
    (root / "accounts.yaml").write_text(ACCOUNTS_YAML, encoding="utf-8")
    (root / "categories.yaml").write_text(CATEGORIES_YAML, encoding="utf-8")
    (root / "budget.yaml").write_text(BUDGET_YAML, encoding="utf-8")
    (root / "rules.yaml").write_text("rules: []\n", encoding="utf-8")
    return root


@pytest.fixture
def cache_root(tmp_path: Path) -> Path:
    root = tmp_path / "cache"
    root.mkdir()
    return root
```

- [ ] **Step 2: Teste que falha**

`tests/test_config.py`:
```python
from decimal import Decimal
from pathlib import Path

import pytest

from finance.config.accounts import load_accounts
from finance.config.budget import load_budget
from finance.config.categories import load_categories
from finance.model.account import AccountType
from finance.model.errors import FinanceError


def test_load_accounts(data_root: Path) -> None:
    accounts = load_accounts(data_root / "accounts.yaml")
    assert set(accounts) == {"nu", "nu-card", "bra"}
    assert accounts["nu-card"].type is AccountType.CREDIT
    assert accounts["nu-card"].closing_day == 3
    assert accounts["nu"].closing_day is None


def test_load_accounts_credit_requires_days(tmp_path: Path) -> None:
    p = tmp_path / "a.yaml"
    p.write_text("accounts:\n  - {id: c, name: C, bank: nubank, type: credit}\n", encoding="utf-8")
    with pytest.raises(FinanceError, match="closing_day"):
        load_accounts(p)


def test_load_accounts_rejects_duplicate_id(tmp_path: Path) -> None:
    p = tmp_path / "a.yaml"
    p.write_text(
        "accounts:\n"
        "  - {id: x, name: A, bank: nubank, type: checking}\n"
        "  - {id: x, name: B, bank: nubank, type: checking}\n",
        encoding="utf-8",
    )
    with pytest.raises(FinanceError, match="duplicad"):
        load_accounts(p)


def test_load_categories(data_root: Path) -> None:
    cats = load_categories(data_root / "categories.yaml")
    assert "casa/aluguel" in cats
    assert "renda/salario" in cats
    assert "casa" not in cats


def test_load_budget(data_root: Path) -> None:
    cats = load_categories(data_root / "categories.yaml")
    budget = load_budget(data_root / "budget.yaml", cats)
    assert budget == {"transporte/uber": Decimal("300.00"), "casa/luz": Decimal("250.00")}


def test_load_budget_rejects_unknown_category(tmp_path: Path) -> None:
    p = tmp_path / "b.yaml"
    p.write_text("lazer/cinema: 100\n", encoding="utf-8")
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        load_budget(p, frozenset({"casa/luz"}))
```

- [ ] **Step 3: Ver falhar** → `ModuleNotFoundError: finance.config`

- [ ] **Step 4: Implementar**

`src/finance/config/accounts.py`:
```python
"""Load accounts.yaml into Account objects."""

from pathlib import Path
from typing import Any

import yaml

from finance.model.account import Account, AccountType
from finance.model.errors import FinanceError


def load_accounts(path: Path) -> dict[str, Account]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = raw.get("accounts") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        raise FinanceError(f"{path}: esperado uma lista em 'accounts'")
    accounts: dict[str, Account] = {}
    for item in items:
        account = _parse(item, path)
        if account.id in accounts:
            raise FinanceError(f"{path}: id de conta duplicado: {account.id!r}")
        accounts[account.id] = account
    return accounts


def _parse(item: Any, path: Path) -> Account:
    if not isinstance(item, dict):
        raise FinanceError(f"{path}: conta inválida: {item!r}")
    try:
        kind = AccountType(str(item["type"]))
        account = Account(
            id=str(item["id"]),
            name=str(item["name"]),
            bank=str(item["bank"]),
            type=kind,
            closing_day=_optional_int(item.get("closing_day")),
            due_day=_optional_int(item.get("due_day")),
        )
    except (KeyError, ValueError) as exc:
        raise FinanceError(f"{path}: conta inválida: {item!r} ({exc})") from exc
    if account.is_credit and (account.closing_day is None or account.due_day is None):
        raise FinanceError(f"{path}: cartão {account.id!r} precisa de closing_day e due_day")
    return account


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    day = int(value)
    if not 1 <= day <= 31:
        raise ValueError(f"dia fora de 1..31: {day}")
    return day
```

`src/finance/config/categories.py`:
```python
"""Load categories.yaml: two-level tree flattened to 'group/item' paths."""

from pathlib import Path
from typing import Any

import yaml

from finance.model.errors import FinanceError


def load_categories(path: Path) -> frozenset[str]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise FinanceError(f"{path}: esperado um mapa grupo -> lista de itens")
    paths: set[str] = set()
    for group, items in raw.items():
        if not isinstance(items, list) or not items:
            raise FinanceError(f"{path}: grupo {group!r} precisa de uma lista de itens")
        for item in items:
            paths.add(f"{group}/{item}")
    return frozenset(paths)
```

`src/finance/config/budget.py`:
```python
"""Load budget.yaml: monthly cap per category path."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from finance.model.errors import FinanceError
from finance.model.money import parse_amount


def load_budget(path: Path, categories: frozenset[str]) -> dict[str, Decimal]:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise FinanceError(f"{path}: esperado um mapa categoria -> valor")
    budget: dict[str, Decimal] = {}
    for category, value in raw.items():
        if category not in categories:
            raise FinanceError(f"{path}: categoria desconhecida: {category!r}")
        budget[str(category)] = parse_amount(str(value))
    return budget
```

- [ ] **Step 5: Ver passar** → PASS
- [ ] **Step 6: Commit** — `git add src/finance/config tests/conftest.py tests/test_config.py && git commit -m "feat: loaders de accounts, categories e budget"`

---

### Task 6: Ledger — caminhos, ids e CSV de um mês

**Files:**
- Create: `src/finance/ledger/__init__.py` (vazio), `src/finance/ledger/paths.py`, `src/finance/ledger/ids.py`, `src/finance/ledger/csv_io.py`
- Test: `tests/test_csv_io.py`, `tests/test_paths.py`

**Interfaces:**
- Produces:
  - `data_dir() -> Path` (env `FINANCE_DATA_DIR`, default `data`); `cache_dir() -> Path` (env `FINANCE_CACHE_DIR`, default `.cache`); `month_file(root: Path, year: int, month: int) -> Path` = `root/ledger/YYYY-MM.csv`; `ledger_files(root) -> list[Path]` ordenada.
  - `new_id() -> str` (ULID).
  - `COLUMNS: tuple[str, ...]`; `entry_to_row(entry) -> dict[str, str]`; `row_to_entry(row: dict[str, str]) -> Entry`; `read_month_file(path) -> list[Entry]` (arquivo ausente = `[]`); `write_month_file(path, entries: Sequence[Entry]) -> None` (ordena por `date`, `id`; cria diretório).

- [ ] **Step 1: Testes que falham**

`tests/test_paths.py`:
```python
from pathlib import Path

import pytest

from finance.ledger.paths import cache_dir, data_dir, ledger_files, month_file


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FINANCE_DATA_DIR", raising=False)
    monkeypatch.delenv("FINANCE_CACHE_DIR", raising=False)
    assert data_dir() == Path("data")
    assert cache_dir() == Path(".cache")


def test_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path / "d"))
    assert data_dir() == tmp_path / "d"


def test_month_file_and_listing(tmp_path: Path) -> None:
    assert month_file(tmp_path, 2026, 9) == tmp_path / "ledger" / "2026-09.csv"
    (tmp_path / "ledger").mkdir()
    for name in ("2026-10.csv", "2026-09.csv", "notes.txt"):
        (tmp_path / "ledger" / name).write_text("", encoding="utf-8")
    assert [p.name for p in ledger_files(tmp_path)] == ["2026-09.csv", "2026-10.csv"]
```

`tests/test_csv_io.py`:
```python
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.ledger.csv_io import COLUMNS, entry_to_row, read_month_file, row_to_entry, write_month_file
from finance.ledger.ids import new_id
from finance.model.entry import Entry, Status


def _entry(**overrides: object) -> Entry:
    base: dict[str, object] = {
        "id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
        "date": date(2026, 9, 5),
        "account": "nu-card",
        "amount": Decimal("-120.00"),
        "description": "celular 1/10",
        "category": "casa/luz",
        "tags": ("pessoal", "eletronico"),
        "installment": "1/10",
        "installment_group": "G1",
        "status": Status.MANUAL,
    }
    base.update(overrides)
    return Entry(**base)  # type: ignore[arg-type]  # reason: test helper builds from a loose dict


def test_new_id_is_ulid_shaped() -> None:
    a, b = new_id(), new_id()
    assert len(a) == 26 and a != b


def test_row_roundtrip() -> None:
    e = _entry()
    row = entry_to_row(e)
    assert tuple(row) == COLUMNS
    assert row["amount"] == "-120.00"
    assert row["tags"] == "pessoal;eletronico"
    assert row["status"] == "manual"
    assert row_to_entry(row) == e


def test_write_then_read_sorted(tmp_path: Path) -> None:
    path = tmp_path / "ledger" / "2026-09.csv"
    later = _entry(id="01HZZZZZZZZZZZZZZZZZZZZZZB", date=date(2026, 9, 20))
    earlier = _entry(id="01HZZZZZZZZZZZZZZZZZZZZZZA", date=date(2026, 9, 1))
    write_month_file(path, [later, earlier])
    assert read_month_file(path) == [earlier, later]
    header = path.read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(COLUMNS)


def test_read_missing_file_is_empty(tmp_path: Path) -> None:
    assert read_month_file(tmp_path / "nope.csv") == []
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.ledger`

- [ ] **Step 3: Implementar**

`src/finance/ledger/paths.py`:
```python
"""Where data and cache live; month-file naming."""

import os
from pathlib import Path


def data_dir() -> Path:
    return Path(os.environ.get("FINANCE_DATA_DIR", "data"))


def cache_dir() -> Path:
    return Path(os.environ.get("FINANCE_CACHE_DIR", ".cache"))


def month_file(root: Path, year: int, month: int) -> Path:
    return root / "ledger" / f"{year:04d}-{month:02d}.csv"


def ledger_files(root: Path) -> list[Path]:
    folder = root / "ledger"
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("????-??.csv") if p.is_file())
```

`src/finance/ledger/ids.py`:
```python
"""Entry ids: ULIDs (sortable by creation time)."""

from ulid import ULID


def new_id() -> str:
    return str(ULID())
```

`src/finance/ledger/csv_io.py`:
```python
"""Entry <-> CSV row, and reading/writing one month file."""

import csv
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.model.entry import Entry, Status
from finance.model.money import format_amount

COLUMNS: tuple[str, ...] = (
    "id",
    "date",
    "account",
    "amount",
    "description",
    "category",
    "tags",
    "installment",
    "installment_group",
    "transfer_group",
    "status",
    "source",
    "import_hash",
)


def entry_to_row(entry: Entry) -> dict[str, str]:
    return {
        "id": entry.id,
        "date": entry.date.isoformat(),
        "account": entry.account,
        "amount": format_amount(entry.amount),
        "description": entry.description,
        "category": entry.category,
        "tags": ";".join(entry.tags),
        "installment": entry.installment,
        "installment_group": entry.installment_group,
        "transfer_group": entry.transfer_group,
        "status": entry.status.value,
        "source": entry.source,
        "import_hash": entry.import_hash,
    }


def row_to_entry(row: dict[str, str]) -> Entry:
    return Entry(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        account=row["account"],
        amount=Decimal(row["amount"]),
        description=row["description"],
        category=row.get("category", ""),
        tags=tuple(t for t in row.get("tags", "").split(";") if t),
        installment=row.get("installment", ""),
        installment_group=row.get("installment_group", ""),
        transfer_group=row.get("transfer_group", ""),
        status=Status(row.get("status") or Status.MANUAL.value),
        source=row.get("source") or "manual",
        import_hash=row.get("import_hash", ""),
    )


def read_month_file(path: Path) -> list[Entry]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [row_to_entry(row) for row in csv.DictReader(fh)]


def write_month_file(path: Path, entries: Sequence[Entry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries, key=lambda e: (e.date, e.id))
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for entry in ordered:
            writer.writerow(entry_to_row(entry))
```

- [ ] **Step 4: Ver passar** → PASS (`uv run pytest tests/test_paths.py tests/test_csv_io.py -v`)
- [ ] **Step 5: Commit** — `git add src/finance/ledger tests/test_paths.py tests/test_csv_io.py && git commit -m "feat: ledger CSV por mês, caminhos e ids ULID"`

---

### Task 7: `LedgerStore` (append/load)

**Files:**
- Create: `src/finance/ledger/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Produces: `LedgerStore(root: Path)` com `append(entries: Iterable[Entry]) -> None` (agrupa por mês do `date`, lê o arquivo, acrescenta, reescreve; id duplicado → `FinanceError`), `load_month(year, month) -> list[Entry]`, `load_all() -> list[Entry]` (todos os meses em ordem).

- [ ] **Step 1: Teste que falha**

`tests/test_store.py`:
```python
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.model.errors import FinanceError


def _e(id_: str, d: date, amount: str = "-10.00") -> Entry:
    return Entry(id=id_, date=d, account="nu", amount=Decimal(amount), description="x")


def test_append_splits_by_month_and_load_all_is_ordered(data_root: Path) -> None:
    store = LedgerStore(data_root)
    store.append([_e("B", date(2026, 10, 1)), _e("A", date(2026, 9, 15))])
    store.append([_e("C", date(2026, 9, 2))])
    assert (data_root / "ledger" / "2026-09.csv").exists()
    assert (data_root / "ledger" / "2026-10.csv").exists()
    assert [e.id for e in store.load_month(2026, 9)] == ["C", "A"]
    assert [e.id for e in store.load_all()] == ["C", "A", "B"]


def test_append_rejects_duplicate_id(data_root: Path) -> None:
    store = LedgerStore(data_root)
    store.append([_e("A", date(2026, 9, 1))])
    with pytest.raises(FinanceError, match="id duplicado"):
        store.append([_e("A", date(2026, 9, 3))])
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.ledger.store`

- [ ] **Step 3: Implementar**

`src/finance/ledger/store.py`:
```python
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

    def load_month(self, year: int, month: int) -> list[Entry]:
        return read_month_file(month_file(self.root, year, month))

    def load_all(self) -> list[Entry]:
        return [entry for path in ledger_files(self.root) for entry in read_month_file(path)]
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git add src/finance/ledger/store.py tests/test_store.py && git commit -m "feat: LedgerStore com append por mês e load"`

---

### Task 8: Ação `add` pura (parcelas incluídas)

**Files:**
- Create: `src/finance/actions/__init__.py` (vazio), `src/finance/actions/add.py`
- Test: `tests/test_action_add.py`

**Interfaces:**
- Consumes: `Entry`, `Account`, `add_months`, `CENTS`.
- Produces:
  - `split_installments(total: Decimal, count: int) -> list[Decimal]` — partes iguais truncadas a centavos, resto na última; soma exata.
  - `AddRequest(account: Account, amount: Decimal, date: date, description: str, category: str, tags: tuple[str, ...], installments: int)` frozen dataclass.
  - `build_manual_entries(req: AddRequest, categories: frozenset[str], ids: Iterator[str]) -> list[Entry]` — valida categoria (vazia ok), parcelas só em conta `credit`, `installments >= 1`; parcela `n/N` na descrição não é adicionada (fica no campo `installment`), `installment_group` = primeiro id consumido.

- [ ] **Step 1: Teste que falha**

`tests/test_action_add.py`:
```python
from datetime import date
from decimal import Decimal
from itertools import count

import pytest

from finance.actions.add import AddRequest, build_manual_entries, split_installments
from finance.model.account import Account, AccountType
from finance.model.entry import Status
from finance.model.errors import FinanceError

CARD = Account(id="nu-card", name="Nubank cartão", bank="nubank", type=AccountType.CREDIT, closing_day=3, due_day=10)
CHECKING = Account(id="nu", name="Nubank conta", bank="nubank", type=AccountType.CHECKING)
CATS = frozenset({"casa/luz", "transporte/uber"})


def _ids() -> "count[int]":
    return count()


def _id_iter():  # type: ignore[no-untyped-def]  # reason: tiny test helper
    return (f"ID{n}" for n in count())


def test_split_installments_exact_sum() -> None:
    parts = split_installments(Decimal("-100.00"), 3)
    assert parts == [Decimal("-33.33"), Decimal("-33.33"), Decimal("-33.34")]
    assert sum(parts) == Decimal("-100.00")
    assert split_installments(Decimal("-10.00"), 1) == [Decimal("-10.00")]


def test_split_installments_rejects_zero() -> None:
    with pytest.raises(FinanceError, match="parcelas"):
        split_installments(Decimal("-10.00"), 0)


def test_single_entry() -> None:
    req = AddRequest(CHECKING, Decimal("-50.00"), date(2026, 9, 5), "uber", "transporte/uber", ("viagem",), 1)
    [e] = build_manual_entries(req, CATS, _id_iter())
    assert e.id == "ID0"
    assert e.account == "nu"
    assert e.amount == Decimal("-50.00")
    assert e.status is Status.MANUAL
    assert e.source == "manual"
    assert e.installment == ""
    assert e.tags == ("viagem",)


def test_installments_spread_over_months_with_group() -> None:
    req = AddRequest(CARD, Decimal("-1000.00"), date(2026, 1, 31), "celular", "", (), 3)
    entries = build_manual_entries(req, CATS, _id_iter())
    assert [e.date for e in entries] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
    assert [e.installment for e in entries] == ["1/3", "2/3", "3/3"]
    assert {e.installment_group for e in entries} == {"ID0"}
    assert sum(e.amount for e in entries) == Decimal("-1000.00")


def test_installments_only_on_credit() -> None:
    req = AddRequest(CHECKING, Decimal("-90.00"), date(2026, 9, 5), "x", "", (), 3)
    with pytest.raises(FinanceError, match="cartão"):
        build_manual_entries(req, CATS, _id_iter())


def test_unknown_category_rejected() -> None:
    req = AddRequest(CHECKING, Decimal("-5.00"), date(2026, 9, 5), "x", "lazer/bar", (), 1)
    with pytest.raises(FinanceError, match="categoria desconhecida"):
        build_manual_entries(req, CATS, _id_iter())
```

(Remova o helper `_ids` não usado antes de commitar — ruff acusa.)

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.actions`

- [ ] **Step 3: Implementar**

`src/finance/actions/add.py`:
```python
"""Build manual ledger entries from a user request (installments included)."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, Decimal

from finance.model.account import Account
from finance.model.dates import add_months
from finance.model.entry import Entry, Status
from finance.model.errors import FinanceError
from finance.model.money import CENTS


@dataclass(frozen=True)
class AddRequest:
    account: Account
    amount: Decimal
    date: date
    description: str
    category: str
    tags: tuple[str, ...]
    installments: int


def split_installments(total: Decimal, count: int) -> list[Decimal]:
    if count < 1:
        raise FinanceError(f"número de parcelas inválido: {count}")
    base = (total / count).quantize(CENTS, rounding=ROUND_DOWN)
    parts = [base] * count
    parts[-1] = total - base * (count - 1)
    return parts


def build_manual_entries(
    req: AddRequest, categories: frozenset[str], ids: Iterator[str]
) -> list[Entry]:
    if req.category and req.category not in categories:
        raise FinanceError(f"categoria desconhecida: {req.category!r}")
    if req.installments > 1 and not req.account.is_credit:
        raise FinanceError("parcelas só existem em cartão de crédito")
    parts = split_installments(req.amount, req.installments)
    group = ""
    entries: list[Entry] = []
    for index, part in enumerate(parts):
        entry_id = next(ids)
        if req.installments > 1 and index == 0:
            group = entry_id
        entries.append(
            Entry(
                id=entry_id,
                date=add_months(req.date, index),
                account=req.account.id,
                amount=part,
                description=req.description,
                category=req.category,
                tags=req.tags,
                installment=f"{index + 1}/{req.installments}" if req.installments > 1 else "",
                installment_group=group,
                status=Status.MANUAL,
                source="manual",
            )
        )
    return entries
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git add src/finance/actions tests/test_action_add.py && git commit -m "feat: montagem de lançamentos manuais com parcelas"`

---

### Task 9: Contexto do CLI + comando `finance add`

**Files:**
- Create: `src/finance/cli/context.py`, `src/finance/cli/add.py`
- Modify: `src/finance/cli/__init__.py` (registrar comando)
- Test: `tests/test_cli_add.py`

**Interfaces:**
- Produces:
  - `Context(data_root: Path, cache_root: Path, accounts: dict[str, Account], categories: frozenset[str], budget: dict[str, Decimal])` frozen dataclass; `load_context() -> Context` lê env via `paths.data_dir()/cache_dir()`.
  - `resolve_account(ctx: Context, text: str) -> Account` — casa por `id` exato, senão por `name` case-insensitive contendo o texto; 0 ou >1 resultados → `FinanceError`.
  - `run(fn) -> None` em `cli/context.py`: executa e converte `FinanceError` em `typer.echo(msg, err=True)` + `raise typer.Exit(1)`.
  - Comando `add`: `finance add --account X --amount V --desc "..." [--date AAAA-MM-DD, default hoje] [--category C] [--installments N] [--tags a,b]`; imprime `N lançamento(s) gravado(s): <ids>`.

- [ ] **Step 1: Teste que falha**

`tests/test_cli_add.py`:
```python
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app
from finance.ledger.store import LedgerStore


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    return data_root


def test_add_single(env: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["add", "--account", "nu", "--amount", "-50", "--desc", "uber", "--date", "2026-09-05",
         "--category", "transporte/uber", "--tags", "viagem,trabalho"],
    )
    assert result.exit_code == 0, result.output
    assert "1 lançamento(s) gravado(s)" in result.output
    [e] = LedgerStore(env).load_month(2026, 9)
    assert e.description == "uber"
    assert e.tags == ("viagem", "trabalho")


def test_add_installments_by_account_name(env: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["add", "--account", "nubank cart", "--amount", "-1000", "--desc", "celular",
         "--date", "2026-09-05", "--installments", "10"],
    )
    assert result.exit_code == 0, result.output
    assert "10 lançamento(s) gravado(s)" in result.output
    assert len(LedgerStore(env).load_all()) == 10
    assert LedgerStore(env).load_month(2027, 6)[0].installment == "10/10"


def test_add_unknown_account_fails_cleanly(env: Path) -> None:
    result = CliRunner().invoke(app, ["add", "--account", "zzz", "--amount", "-1", "--desc", "x"])
    assert result.exit_code == 1
    assert "conta desconhecida" in result.output


def test_add_ambiguous_account_fails(env: Path) -> None:
    result = CliRunner().invoke(app, ["add", "--account", "nubank", "--amount", "-1", "--desc", "x"])
    assert result.exit_code == 1
    assert "ambígua" in result.output
```

- [ ] **Step 2: Ver falhar** → `No such command 'add'` (exit code 2)

- [ ] **Step 3: Implementar**

`src/finance/cli/context.py`:
```python
"""Load config once per command and map FinanceError to a clean exit."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import typer

from finance.config.accounts import load_accounts
from finance.config.budget import load_budget
from finance.config.categories import load_categories
from finance.ledger.paths import cache_dir, data_dir
from finance.model.account import Account
from finance.model.errors import FinanceError


@dataclass(frozen=True)
class Context:
    data_root: Path
    cache_root: Path
    accounts: dict[str, Account]
    categories: frozenset[str]
    budget: dict[str, Decimal]


def load_context() -> Context:
    root = data_dir()
    categories = load_categories(root / "categories.yaml")
    return Context(
        data_root=root,
        cache_root=cache_dir(),
        accounts=load_accounts(root / "accounts.yaml"),
        categories=categories,
        budget=load_budget(root / "budget.yaml", categories),
    )


def resolve_account(ctx: Context, text: str) -> Account:
    if text in ctx.accounts:
        return ctx.accounts[text]
    needle = text.strip().lower()
    matches = [a for a in ctx.accounts.values() if needle in a.name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FinanceError(f"conta desconhecida: {text!r}")
    names = ", ".join(a.id for a in matches)
    raise FinanceError(f"conta ambígua: {text!r} casa com {names}")


def run(fn: Callable[[], None]) -> None:
    try:
        fn()
    except FinanceError as exc:
        typer.echo(f"erro: {exc}", err=True)
        raise typer.Exit(1) from exc
```

`src/finance/cli/add.py`:
```python
"""`finance add`: record manual entries."""

from datetime import date
from typing import Annotated

import typer

from finance.actions.add import AddRequest, build_manual_entries
from finance.cli.context import load_context, resolve_account, run
from finance.ledger.ids import new_id
from finance.ledger.store import LedgerStore
from finance.model.money import parse_amount


def add(
    account: Annotated[str, typer.Option("--account", help="id ou parte do nome da conta")],
    amount: Annotated[str, typer.Option("--amount", help="negativo = saída, positivo = entrada")],
    desc: Annotated[str, typer.Option("--desc")],
    date_text: Annotated[str | None, typer.Option("--date", help="AAAA-MM-DD, default hoje")] = None,
    category: Annotated[str, typer.Option("--category")] = "",
    installments: Annotated[int, typer.Option("--installments", min=1)] = 1,
    tags: Annotated[str, typer.Option("--tags", help="separadas por vírgula")] = "",
) -> None:
    """Grava um lançamento manual (parcelado ou não)."""

    def _go() -> None:
        ctx = load_context()
        req = AddRequest(
            account=resolve_account(ctx, account),
            amount=parse_amount(amount),
            date=date.fromisoformat(date_text) if date_text else date.today(),
            description=desc,
            category=category,
            tags=tuple(t.strip() for t in tags.split(",") if t.strip()),
            installments=installments,
        )
        entries = build_manual_entries(req, ctx.categories, iter(new_id, None))
        LedgerStore(ctx.data_root).append(entries)
        ids = ", ".join(e.id for e in entries)
        typer.echo(f"{len(entries)} lançamento(s) gravado(s): {ids}")

    run(_go)
```

Em `src/finance/cli/__init__.py`, após a definição de `main`, acrescentar:
```python
from finance.cli.add import add  # noqa: E402  # reason: commands import `app` indirectly; register after it exists

app.command("add")(add)
```

Se o ruff reclamar da ordem de import mesmo com `noqa`, mova o registro para uma função `_register()` chamada no fim do módulo. Nota: `iter(new_id, None)` cria um iterador infinito de ULIDs (sentinela nunca atingida).

- [ ] **Step 4: Ver passar** → `uv run pytest tests/test_cli_add.py -v` PASS
- [ ] **Step 5: Lint/mypy** → limpos
- [ ] **Step 6: Commit** — `git add src/finance/cli tests/test_cli_add.py && git commit -m "feat: comando finance add"`

---

### Task 10: Cache SQLite — schema, rebuild e abertura com frescor

**Files:**
- Create: `src/finance/cache/__init__.py` (vazio), `src/finance/cache/schema.py`, `src/finance/cache/rebuild.py`, `src/finance/cache/connection.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- Produces:
  - `SCHEMA: str` (DDL) com tabelas `entries` (todas as colunas de `COLUMNS`, `amount` como `TEXT` decimal, `year_month TEXT` = `YYYY-MM`), `accounts(id, name, bank, type, closing_day, due_day)`, `budget(category, amount TEXT)`.
  - `rebuild(ctx_data_root: Path, db_path: Path, accounts: dict[str, Account], budget: dict[str, Decimal]) -> int` — apaga o db, cria, insere; retorna nº de entries.
  - `is_stale(data_root: Path, db_path: Path) -> bool` — db ausente ou mais velho que qualquer arquivo em `data/` (yaml + ledger).
  - `open_db(data_root, cache_root, accounts, budget) -> sqlite3.Connection` — rebuild se `is_stale`; `row_factory = sqlite3.Row`.

- [ ] **Step 1: Teste que falha**

`tests/test_cache.py`:
```python
import os
import sqlite3
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.cache.connection import is_stale, open_db
from finance.cache.rebuild import rebuild
from finance.config.accounts import load_accounts
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry


def _seed(data_root: Path) -> None:
    LedgerStore(data_root).append(
        [
            Entry(id="A", date=date(2026, 9, 1), account="nu", amount=Decimal("-10.00"), description="a"),
            Entry(id="B", date=date(2026, 10, 1), account="nu", amount=Decimal("20.00"), description="b"),
        ]
    )


def test_rebuild_loads_entries_accounts_budget(data_root: Path, cache_root: Path) -> None:
    _seed(data_root)
    accounts = load_accounts(data_root / "accounts.yaml")
    db = cache_root / "finance.db"
    n = rebuild(data_root, db, accounts, {"casa/luz": Decimal("250.00")})
    assert n == 2
    conn = sqlite3.connect(db)
    assert conn.execute("select count(*) from entries").fetchone()[0] == 2
    assert conn.execute("select year_month from entries where id='B'").fetchone()[0] == "2026-10"
    assert conn.execute("select count(*) from accounts").fetchone()[0] == 3
    assert conn.execute("select amount from budget where category='casa/luz'").fetchone()[0] == "250.00"


def test_open_db_rebuilds_when_stale(data_root: Path, cache_root: Path) -> None:
    _seed(data_root)
    accounts = load_accounts(data_root / "accounts.yaml")
    db = cache_root / "finance.db"
    assert is_stale(data_root, db)
    conn = open_db(data_root, cache_root, accounts, {})
    assert conn.execute("select count(*) from entries").fetchone()[0] == 2
    conn.close()
    assert not is_stale(data_root, db)
    time.sleep(0.01)
    LedgerStore(data_root).append(
        [Entry(id="C", date=date(2026, 9, 3), account="nu", amount=Decimal("-1.00"), description="c")]
    )
    future = time.time() + 5
    os.utime(data_root / "ledger" / "2026-09.csv", (future, future))
    assert is_stale(data_root, db)
    conn = open_db(data_root, cache_root, accounts, {})
    assert conn.execute("select count(*) from entries").fetchone()[0] == 3
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.cache`

- [ ] **Step 3: Implementar**

`src/finance/cache/schema.py`:
```python
"""SQLite DDL for the disposable query cache."""

SCHEMA = """
create table entries (
  id text primary key,
  date text not null,
  year_month text not null,
  account text not null,
  amount text not null,
  description text not null,
  category text not null,
  tags text not null,
  installment text not null,
  installment_group text not null,
  transfer_group text not null,
  status text not null,
  source text not null,
  import_hash text not null
);
create index entries_month on entries(year_month);
create index entries_account_date on entries(account, date);

create table accounts (
  id text primary key,
  name text not null,
  bank text not null,
  type text not null,
  closing_day integer,
  due_day integer
);

create table budget (
  category text primary key,
  amount text not null
);
"""
```

`src/finance/cache/rebuild.py`:
```python
"""Rebuild the SQLite cache from data/ (yaml + ledger CSVs)."""

import sqlite3
from decimal import Decimal
from pathlib import Path

from finance.cache.schema import SCHEMA
from finance.ledger.csv_io import COLUMNS, entry_to_row
from finance.ledger.store import LedgerStore
from finance.model.account import Account
from finance.model.money import format_amount

_ENTRY_COLUMNS = (*COLUMNS, "year_month")
_ENTRY_SQL = (
    f"insert into entries ({', '.join(_ENTRY_COLUMNS)}) "
    f"values ({', '.join('?' for _ in _ENTRY_COLUMNS)})"
)


def rebuild(
    data_root: Path, db_path: Path, accounts: dict[str, Account], budget: dict[str, Decimal]
) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    entries = LedgerStore(data_root).load_all()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            _ENTRY_SQL,
            [
                (*(entry_to_row(e)[c] for c in COLUMNS), e.date.strftime("%Y-%m"))
                for e in entries
            ],
        )
        conn.executemany(
            "insert into accounts values (?, ?, ?, ?, ?, ?)",
            [(a.id, a.name, a.bank, a.type.value, a.closing_day, a.due_day) for a in accounts.values()],
        )
        conn.executemany(
            "insert into budget values (?, ?)",
            [(category, format_amount(amount)) for category, amount in budget.items()],
        )
    return len(entries)
```

`src/finance/cache/connection.py`:
```python
"""Open the cache, rebuilding it whenever data/ is newer."""

import sqlite3
from decimal import Decimal
from pathlib import Path

from finance.cache.rebuild import rebuild
from finance.ledger.paths import ledger_files
from finance.model.account import Account

DB_NAME = "finance.db"
_CONFIG_FILES = ("accounts.yaml", "categories.yaml", "budget.yaml", "rules.yaml")


def is_stale(data_root: Path, db_path: Path) -> bool:
    if not db_path.is_file():
        return True
    built = db_path.stat().st_mtime
    sources = [data_root / name for name in _CONFIG_FILES] + ledger_files(data_root)
    return any(p.is_file() and p.stat().st_mtime > built for p in sources)


def open_db(
    data_root: Path, cache_root: Path, accounts: dict[str, Account], budget: dict[str, Decimal]
) -> sqlite3.Connection:
    db_path = cache_root / DB_NAME
    if is_stale(data_root, db_path):
        rebuild(data_root, db_path, accounts, budget)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git add src/finance/cache tests/test_cache.py && git commit -m "feat: cache SQLite regenerável a partir de data/"`

---

### Task 11: Comando `finance rebuild`

**Files:**
- Create: `src/finance/cli/rebuild.py`
- Modify: `src/finance/cli/__init__.py` (registrar)
- Test: `tests/test_cli_rebuild.py`

**Interfaces:**
- Produces: comando `rebuild` que chama `cache.rebuild.rebuild(ctx.data_root, ctx.cache_root / DB_NAME, ctx.accounts, ctx.budget)` e imprime `cache reconstruído: N lançamento(s) em <path>`.

- [ ] **Step 1: Teste que falha**

`tests/test_cli_rebuild.py`:
```python
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app


def test_rebuild_creates_db(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> None:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    result = CliRunner().invoke(app, ["rebuild"])
    assert result.exit_code == 0, result.output
    assert "cache reconstruído: 0 lançamento(s)" in result.output
    assert (cache_root / "finance.db").is_file()
```

- [ ] **Step 2: Ver falhar** → `No such command 'rebuild'`

- [ ] **Step 3: Implementar**

`src/finance/cli/rebuild.py`:
```python
"""`finance rebuild`: regenerate the SQLite cache from data/."""

import typer

from finance.cache.connection import DB_NAME
from finance.cache.rebuild import rebuild as rebuild_cache
from finance.cli.context import load_context, run


def rebuild() -> None:
    """Recria .cache/finance.db a partir de data/."""

    def _go() -> None:
        ctx = load_context()
        db_path = ctx.cache_root / DB_NAME
        n = rebuild_cache(ctx.data_root, db_path, ctx.accounts, ctx.budget)
        typer.echo(f"cache reconstruído: {n} lançamento(s) em {db_path}")

    run(_go)
```

Em `cli/__init__.py`, junto do registro de `add`:
```python
from finance.cli.rebuild import rebuild  # noqa: E402  # reason: registered after `app` exists

app.command("rebuild")(rebuild)
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git add src/finance/cli tests/test_cli_rebuild.py && git commit -m "feat: comando finance rebuild"`

---

### Task 12: Período da fatura (`reports/invoice_period.py`)

**Files:**
- Create: `src/finance/reports/__init__.py` (vazio), `src/finance/reports/invoice_period.py`
- Test: `tests/test_invoice_period.py`

**Interfaces:**
- Produces:
  - `invoice_period(year: int, month: int, closing_day: int) -> tuple[date, date]` = `(start, end)` **ambos inclusivos**: `end = clamp_day(year, month, closing_day)`, `start = clamp_day(prev, closing_day) + 1 dia`.
  - `invoice_month_for(d: date, closing_day: int) -> tuple[int, int]` — `d.day <= closing_day` → mês de `d`; senão mês seguinte.
  - `due_date(year, month, due_day) -> date` = `clamp_day(year, month, due_day)`.

- [ ] **Step 1: Teste que falha**

`tests/test_invoice_period.py`:
```python
from datetime import date

from finance.reports.invoice_period import due_date, invoice_month_for, invoice_period


def test_period_is_prev_close_plus_one_to_close() -> None:
    assert invoice_period(2026, 9, 3) == (date(2026, 8, 4), date(2026, 9, 3))


def test_period_clamps_short_months() -> None:
    assert invoice_period(2026, 3, 31) == (date(2026, 3, 1), date(2026, 3, 31))
    assert invoice_period(2026, 2, 31) == (date(2026, 2, 1), date(2026, 2, 28))


def test_month_for_purchase_date() -> None:
    assert invoice_month_for(date(2026, 9, 3), 3) == (2026, 9)
    assert invoice_month_for(date(2026, 9, 4), 3) == (2026, 10)
    assert invoice_month_for(date(2026, 12, 20), 3) == (2027, 1)


def test_due_date() -> None:
    assert due_date(2026, 9, 10) == date(2026, 9, 10)
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.reports`

- [ ] **Step 3: Implementar**

`src/finance/reports/invoice_period.py`:
```python
"""Which purchase dates fall into which credit-card invoice."""

from datetime import date, timedelta

from finance.model.dates import add_months, clamp_day


def invoice_period(year: int, month: int, closing_day: int) -> tuple[date, date]:
    end = clamp_day(year, month, closing_day)
    previous = add_months(date(year, month, 1), -1)
    start = clamp_day(previous.year, previous.month, closing_day) + timedelta(days=1)
    return start, end


def invoice_month_for(d: date, closing_day: int) -> tuple[int, int]:
    if d.day <= closing_day:
        return d.year, d.month
    following = add_months(date(d.year, d.month, 1), 1)
    return following.year, following.month


def due_date(year: int, month: int, due_day: int) -> date:
    return clamp_day(year, month, due_day)
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git add src/finance/reports tests/test_invoice_period.py && git commit -m "feat: cálculo do período da fatura"`

---

### Task 13: Relatórios `balance` e `invoice`

**Files:**
- Create: `src/finance/reports/balance.py`, `src/finance/reports/invoice.py`
- Test: `tests/test_report_balance.py`, `tests/test_report_invoice.py`

**Interfaces:**
- Consumes: `sqlite3.Connection` aberta por `open_db`; `Account`; `invoice_period`, `invoice_month_for`, `due_date`.
- Produces:
  - `AccountBalance(account_id: str, name: str, type: str, balance: Decimal, open_invoice: Decimal | None, open_invoice_month: str | None)`; `account_balances(conn, accounts: dict[str, Account], today: date) -> list[AccountBalance]` — `balance` = soma de todos os `amount` da conta; para `credit`, `open_invoice` = valor devido (`-soma`) da fatura cujo período contém `today`, `open_invoice_month` = `YYYY-MM`.
  - `InvoiceLine(id: str, date: date, description: str, amount: Decimal, category: str, installment: str, status: str)`; `Invoice(account_id: str, year: int, month: int, start: date, end: date, due: date, lines: list[InvoiceLine], purchases: Decimal, payments: Decimal, total_due: Decimal)`; `invoice(conn, account: Account, year, month) -> Invoice` — `purchases` = soma dos `amount < 0` sem `transfer_group` (como positivo), `payments` = soma dos `amount > 0` com `transfer_group`, `total_due = -soma(todos amount no período)`. Conta não-crédito → `FinanceError`.

- [ ] **Step 1: Testes que falham**

`tests/test_report_balance.py`:
```python
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.cache.connection import open_db
from finance.config.accounts import load_accounts
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.reports.balance import account_balances


def _e(id_: str, d: date, account: str, amount: str, transfer: str = "") -> Entry:
    return Entry(id=id_, date=d, account=account, amount=Decimal(amount), description=id_, transfer_group=transfer)


def test_balances_and_open_invoice(data_root: Path, cache_root: Path) -> None:
    LedgerStore(data_root).append(
        [
            _e("sal", date(2026, 9, 1), "nu", "3000.00"),
            _e("mkt", date(2026, 9, 2), "nu", "-200.00"),
            _e("c1", date(2026, 8, 20), "nu-card", "-100.00"),   # fatura 2026-09 (04/08..03/09)
            _e("c2", date(2026, 9, 5), "nu-card", "-50.00"),     # fatura 2026-10
            _e("pay-out", date(2026, 9, 10), "nu", "-100.00", "T1"),
            _e("pay-in", date(2026, 9, 10), "nu-card", "100.00", "T1"),
        ]
    )
    accounts = load_accounts(data_root / "accounts.yaml")
    conn = open_db(data_root, cache_root, accounts, {})
    result = {b.account_id: b for b in account_balances(conn, accounts, today=date(2026, 9, 20))}
    assert result["nu"].balance == Decimal("2700.00")
    assert result["nu"].open_invoice is None
    assert result["nu-card"].balance == Decimal("-50.00")
    assert result["nu-card"].open_invoice_month == "2026-10"
    assert result["nu-card"].open_invoice == Decimal("-50.00")
    assert result["bra"].balance == Decimal("0.00")
```

Nota: na fatura 2026-10 (04/09..03/10) estão `c2` (-50) e `pay-in` (+100): soma = +50, devido = -50 (crédito a favor). O teste pinna esse sinal de propósito.

`tests/test_report_invoice.py`:
```python
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finance.cache.connection import open_db
from finance.config.accounts import load_accounts
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry
from finance.model.errors import FinanceError
from finance.reports.invoice import invoice


def _e(id_: str, d: date, amount: str, transfer: str = "") -> Entry:
    return Entry(id=id_, date=d, account="nu-card", amount=Decimal(amount), description=id_, transfer_group=transfer)


def test_invoice_totals_and_window(data_root: Path, cache_root: Path) -> None:
    LedgerStore(data_root).append(
        [
            _e("before", date(2026, 8, 3), "-999.00"),   # fatura 2026-08
            _e("a", date(2026, 8, 4), "-100.00"),
            _e("b", date(2026, 9, 3), "-20.50"),
            _e("pay", date(2026, 8, 15), "60.00", "T1"),
            _e("after", date(2026, 9, 4), "-1.00"),     # fatura 2026-10
        ]
    )
    accounts = load_accounts(data_root / "accounts.yaml")
    conn = open_db(data_root, cache_root, accounts, {})
    inv = invoice(conn, accounts["nu-card"], 2026, 9)
    assert (inv.start, inv.end, inv.due) == (date(2026, 8, 4), date(2026, 9, 3), date(2026, 9, 10))
    assert [line.id for line in inv.lines] == ["a", "pay", "b"]
    assert inv.purchases == Decimal("120.50")
    assert inv.payments == Decimal("60.00")
    assert inv.total_due == Decimal("60.50")


def test_invoice_rejects_checking(data_root: Path, cache_root: Path) -> None:
    accounts = load_accounts(data_root / "accounts.yaml")
    conn = open_db(data_root, cache_root, accounts, {})
    with pytest.raises(FinanceError, match="não é cartão"):
        invoice(conn, accounts["nu"], 2026, 9)
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.reports.balance`

- [ ] **Step 3: Implementar**

`src/finance/reports/balance.py`:
```python
"""Per-account balance and, for cards, the invoice currently open."""

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.model.account import Account
from finance.reports.invoice_period import invoice_month_for, invoice_period


@dataclass(frozen=True)
class AccountBalance:
    account_id: str
    name: str
    type: str
    balance: Decimal
    open_invoice: Decimal | None
    open_invoice_month: str | None


def _sum(conn: sqlite3.Connection, sql: str, params: tuple[object, ...]) -> Decimal:
    rows = conn.execute(sql, params).fetchall()
    return sum((Decimal(r[0]) for r in rows), Decimal("0.00"))


def account_balances(
    conn: sqlite3.Connection, accounts: dict[str, Account], today: date
) -> list[AccountBalance]:
    result: list[AccountBalance] = []
    for account in accounts.values():
        balance = _sum(conn, "select amount from entries where account = ?", (account.id,))
        open_invoice: Decimal | None = None
        open_month: str | None = None
        if account.is_credit and account.closing_day is not None:
            year, month = invoice_month_for(today, account.closing_day)
            start, end = invoice_period(year, month, account.closing_day)
            in_period = _sum(
                conn,
                "select amount from entries where account = ? and date between ? and ?",
                (account.id, start.isoformat(), end.isoformat()),
            )
            open_invoice = -in_period
            open_month = f"{year:04d}-{month:02d}"
        result.append(
            AccountBalance(account.id, account.name, account.type.value, balance, open_invoice, open_month)
        )
    return result
```

`src/finance/reports/invoice.py`:
```python
"""One credit-card invoice: its lines and totals."""

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.model.account import Account
from finance.model.errors import FinanceError
from finance.reports.invoice_period import due_date, invoice_period


@dataclass(frozen=True)
class InvoiceLine:
    id: str
    date: date
    description: str
    amount: Decimal
    category: str
    installment: str
    status: str


@dataclass(frozen=True)
class Invoice:
    account_id: str
    year: int
    month: int
    start: date
    end: date
    due: date
    lines: list[InvoiceLine]
    purchases: Decimal
    payments: Decimal
    total_due: Decimal


def invoice(conn: sqlite3.Connection, account: Account, year: int, month: int) -> Invoice:
    if not account.is_credit or account.closing_day is None or account.due_day is None:
        raise FinanceError(f"conta {account.id!r} não é cartão de crédito")
    start, end = invoice_period(year, month, account.closing_day)
    rows = conn.execute(
        "select id, date, description, amount, category, installment, status, transfer_group "
        "from entries where account = ? and date between ? and ? order by date, id",
        (account.id, start.isoformat(), end.isoformat()),
    ).fetchall()
    lines = [
        InvoiceLine(
            id=r["id"],
            date=date.fromisoformat(r["date"]),
            description=r["description"],
            amount=Decimal(r["amount"]),
            category=r["category"],
            installment=r["installment"],
            status=r["status"],
        )
        for r in rows
    ]
    zero = Decimal("0.00")
    purchases = -sum((Decimal(r["amount"]) for r in rows if Decimal(r["amount"]) < 0 and not r["transfer_group"]), zero)
    payments = sum((Decimal(r["amount"]) for r in rows if Decimal(r["amount"]) > 0 and r["transfer_group"]), zero)
    total_due = -sum((Decimal(r["amount"]) for r in rows), zero)
    return Invoice(
        account_id=account.id,
        year=year,
        month=month,
        start=start,
        end=end,
        due=due_date(year, month, account.due_day),
        lines=lines,
        purchases=purchases,
        payments=payments,
        total_due=total_due,
    )
```

- [ ] **Step 4: Ver passar** → PASS (ambos os arquivos)
- [ ] **Step 5: Commit** — `git add src/finance/reports tests/test_report_balance.py tests/test_report_invoice.py && git commit -m "feat: relatórios balance e invoice"`

---

### Task 14: Relatório `month` (com orçamento)

**Files:**
- Create: `src/finance/reports/month.py`
- Test: `tests/test_report_month.py`

**Interfaces:**
- Produces:
  - `CategoryLine(category: str, spent: Decimal, budget: Decimal | None, pct: Decimal | None)` — `pct` = `spent/budget*100` com 1 casa, `None` sem orçamento.
  - `MonthSummary(year: int, month: int, income: Decimal, expenses: Decimal, net: Decimal, lines: list[CategoryLine], uncategorized: int, pending_manual: int)`.
  - `month_summary(conn, year, month, budget: dict[str, Decimal]) -> MonthSummary` — ignora `transfer_group != ''`; `income` = soma dos positivos; `expenses` = soma dos negativos como positivo; `lines` por `category` (vazia = `"(sem categoria)"`), inclui categorias com orçamento e gasto zero; ordenadas por `spent` desc; `uncategorized` = nº de entries com `category = ''`; `pending_manual` = nº com `status = 'manual'`.

- [ ] **Step 1: Teste que falha**

`tests/test_report_month.py`:
```python
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.cache.connection import open_db
from finance.config.accounts import load_accounts
from finance.ledger.store import LedgerStore
from finance.model.entry import Entry, Status
from finance.reports.month import month_summary


def _e(id_: str, d: date, amount: str, category: str = "", transfer: str = "", status: Status = Status.CONFIRMED) -> Entry:
    return Entry(id=id_, date=d, account="nu", amount=Decimal(amount), description=id_, category=category, transfer_group=transfer, status=status)


def test_month_summary(data_root: Path, cache_root: Path) -> None:
    LedgerStore(data_root).append(
        [
            _e("sal", date(2026, 9, 1), "3000.00", "renda/salario"),
            _e("u1", date(2026, 9, 2), "-40.00", "transporte/uber"),
            _e("u2", date(2026, 9, 3), "-20.00", "transporte/uber", status=Status.MANUAL),
            _e("luz", date(2026, 9, 4), "-300.00", "casa/luz"),
            _e("??", date(2026, 9, 5), "-15.00"),
            _e("pay", date(2026, 9, 6), "-500.00", transfer="T1"),
            _e("oct", date(2026, 10, 1), "-1.00", "casa/luz"),
        ]
    )
    accounts = load_accounts(data_root / "accounts.yaml")
    budget = {"transporte/uber": Decimal("300.00"), "casa/luz": Decimal("250.00"), "casa/aluguel": Decimal("1500.00")}
    conn = open_db(data_root, cache_root, accounts, budget)
    s = month_summary(conn, 2026, 9, budget)
    assert s.income == Decimal("3000.00")
    assert s.expenses == Decimal("375.00")
    assert s.net == Decimal("2625.00")
    assert s.uncategorized == 1
    assert s.pending_manual == 1
    by_cat = {line.category: line for line in s.lines}
    assert by_cat["casa/luz"].spent == Decimal("300.00")
    assert by_cat["casa/luz"].pct == Decimal("120.0")
    assert by_cat["transporte/uber"].spent == Decimal("60.00")
    assert by_cat["transporte/uber"].pct == Decimal("20.0")
    assert by_cat["casa/aluguel"].spent == Decimal("0.00")
    assert by_cat["(sem categoria)"].budget is None
    assert [line.category for line in s.lines][:2] == ["casa/luz", "transporte/uber"]
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.reports.month`

- [ ] **Step 3: Implementar**

`src/finance/reports/month.py`:
```python
"""Monthly cash-flow summary: income, expenses by category vs budget."""

import sqlite3
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

UNCATEGORIZED = "(sem categoria)"
_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class CategoryLine:
    category: str
    spent: Decimal
    budget: Decimal | None
    pct: Decimal | None


@dataclass(frozen=True)
class MonthSummary:
    year: int
    month: int
    income: Decimal
    expenses: Decimal
    net: Decimal
    lines: list[CategoryLine]
    uncategorized: int
    pending_manual: int


def month_summary(
    conn: sqlite3.Connection, year: int, month: int, budget: dict[str, Decimal]
) -> MonthSummary:
    ym = f"{year:04d}-{month:02d}"
    rows = conn.execute(
        "select amount, category, status from entries where year_month = ? and transfer_group = ''",
        (ym,),
    ).fetchall()
    income = _ZERO
    spent_by_category: dict[str, Decimal] = {c: _ZERO for c in budget}
    uncategorized = 0
    pending_manual = 0
    for row in rows:
        amount = Decimal(row["amount"])
        if row["status"] == "manual":
            pending_manual += 1
        if amount > 0:
            income += amount
            continue
        category = row["category"] or UNCATEGORIZED
        if not row["category"]:
            uncategorized += 1
        spent_by_category[category] = spent_by_category.get(category, _ZERO) - amount
    lines = [
        CategoryLine(category, spent, budget.get(category), _pct(spent, budget.get(category)))
        for category, spent in spent_by_category.items()
    ]
    lines.sort(key=lambda line: (-line.spent, line.category))
    expenses = sum((line.spent for line in lines), _ZERO)
    return MonthSummary(year, month, income, expenses, income - expenses, lines, uncategorized, pending_manual)


def _pct(spent: Decimal, cap: Decimal | None) -> Decimal | None:
    if cap is None or cap == 0:
        return None
    return (spent / cap * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
```

- [ ] **Step 4: Ver passar** → PASS
- [ ] **Step 5: Commit** — `git add src/finance/reports/month.py tests/test_report_month.py && git commit -m "feat: resumo mensal com orçamento"`

---

### Task 15: Render (tabela/JSON) + comandos `finance report *`

**Files:**
- Create: `src/finance/render/__init__.py` (vazio), `src/finance/render/output.py`, `src/finance/cli/report.py`
- Modify: `src/finance/cli/__init__.py` (registrar grupo `report`)
- Test: `tests/test_render.py`, `tests/test_cli_report.py`

**Interfaces:**
- Produces:
  - `to_jsonable(obj: object) -> object` — dataclass → dict recursivo; `Decimal` → str 2 casas; `date` → ISO; list/tuple → list.
  - `emit_json(obj) -> None` (`typer.echo(json.dumps(..., ensure_ascii=False, indent=2))`).
  - `emit_table(title: str, columns: Sequence[str], rows: Sequence[Sequence[object]]) -> None` via `rich.table.Table` num `rich.console.Console()`; `Decimal` formatado com `format_amount`, `date` ISO, `None` → `-`.
  - Grupo `report` com `month [--month AAAA-MM] [--json]`, `budget [--month] [--json]`, `balance [--json]`, `invoice --account X [--month] [--json]`. Default de `--month`: mês atual (`date.today()`).

- [ ] **Step 1: Testes que falham**

`tests/test_render.py`:
```python
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from typer.testing import CliRunner

from finance.render.output import to_jsonable


@dataclass(frozen=True)
class _Inner:
    when: date
    value: Decimal


@dataclass(frozen=True)
class _Outer:
    name: str
    items: list[_Inner]
    maybe: Decimal | None


def test_to_jsonable() -> None:
    obj = _Outer("x", [_Inner(date(2026, 9, 1), Decimal("1.5"))], None)
    data = to_jsonable(obj)
    assert data == {"name": "x", "items": [{"when": "2026-09-01", "value": "1.50"}], "maybe": None}
    json.dumps(data)


def test_runner_import_smoke() -> None:
    assert CliRunner is not None
```

`tests/test_cli_report.py`:
```python
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from finance.cli import app


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, data_root: Path, cache_root: Path) -> Path:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(data_root))
    monkeypatch.setenv("FINANCE_CACHE_DIR", str(cache_root))
    runner = CliRunner()
    for args in (
        ["add", "--account", "nu", "--amount", "3000", "--desc", "salario", "--date", "2026-09-01", "--category", "renda/salario"],
        ["add", "--account", "nu", "--amount", "-40", "--desc", "uber", "--date", "2026-09-02", "--category", "transporte/uber"],
        ["add", "--account", "nu-card", "--amount", "-300", "--desc", "tv", "--date", "2026-08-20", "--installments", "3", "--category", "casa/luz"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
    return data_root


def test_report_month_json(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "month", "--month", "2026-09", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["income"] == "3000.00"
    assert data["expenses"] == "140.00"
    cats = {line["category"]: line for line in data["lines"]}
    assert cats["transporte/uber"]["pct"] == "13.3"


def test_report_budget_table(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "budget", "--month", "2026-09"])
    assert result.exit_code == 0, result.output
    assert "transporte/uber" in result.output
    assert "300.00" in result.output


def test_report_balance_json(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "balance", "--json"])
    assert result.exit_code == 0, result.output
    data = {row["account_id"]: row for row in json.loads(result.output)}
    assert data["nu"]["balance"] == "2960.00"
    assert data["nu-card"]["balance"] == "-300.00"


def test_report_invoice_json(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "invoice", "--account", "nu-card", "--month", "2026-09", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["total_due"] == "100.00"
    assert data["lines"][0]["installment"] == "1/3"


def test_report_invoice_on_checking_fails(env: Path) -> None:
    result = CliRunner().invoke(app, ["report", "invoice", "--account", "nu"])
    assert result.exit_code == 1
    assert "não é cartão" in result.output
```

- [ ] **Step 2: Ver falhar** → `ModuleNotFoundError: finance.render` / `No such command 'report'`

- [ ] **Step 3: Implementar**

`src/finance/render/output.py`:
```python
"""Turn report dataclasses into JSON or a rich table."""

import dataclasses
import json
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import typer
from rich.console import Console
from rich.table import Table

from finance.model.money import format_amount


def to_jsonable(obj: object) -> object:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Decimal):
        return format_amount(obj) if obj == obj.quantize(Decimal("0.01")) else str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, list | tuple):
        return [to_jsonable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    return obj


def emit_json(obj: object) -> None:
    typer.echo(json.dumps(to_jsonable(obj), ensure_ascii=False, indent=2))


def _cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, Decimal):
        return format_amount(value) if value == value.quantize(Decimal("0.01")) else str(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def emit_table(title: str, columns: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*(_cell(v) for v in row))
    Console(width=120).print(table)
```

Nota sobre `pct` (`Decimal("13.3")`): `to_jsonable` mantém 1 casa porque `13.3 != 13.30`? Não — `Decimal("13.3") == Decimal("13.30")` é `True`. Por isso o teste espera `"13.3"`? **Não**: com a regra acima, `13.3` viraria `"13.30"`. Ajuste: em `to_jsonable` e `_cell`, use `format_amount` só quando `obj.as_tuple().exponent <= -2`, senão `str(obj)`. Implementação final do ramo `Decimal`:

```python
    if isinstance(obj, Decimal):
        exponent = obj.as_tuple().exponent
        return format_amount(obj) if isinstance(exponent, int) and exponent <= -2 else str(obj)
```
(mesma regra em `_cell`). Com isso `Decimal("13.3")` → `"13.3"`, `Decimal("1.5")` → `"1.5"`... e o teste `test_to_jsonable` espera `"1.50"`. Regra definitiva, sem ambiguidade: **`pct` é o único Decimal com 1 casa; tudo o mais é dinheiro.** Então `to_jsonable` e `_cell` formatam com `format_amount` sempre, e `CategoryLine.pct` passa a ser `str | None` já formatado (`"13.3"`) em `reports/month.py` — ajuste `_pct` para devolver `str(...)` do quantize e o teste da Task 14 para `assert by_cat["casa/luz"].pct == "120.0"`. Corrija a Task 14 antes desta.

`src/finance/cli/report.py`:
```python
"""`finance report *`: read-only views over the cache."""

from datetime import date
from typing import Annotated

import typer

from finance.cache.connection import open_db
from finance.cli.context import Context, load_context, resolve_account, run
from finance.model.dates import parse_month
from finance.render.output import emit_json, emit_table
from finance.reports.balance import account_balances
from finance.reports.invoice import invoice as build_invoice
from finance.reports.month import month_summary

report_app = typer.Typer(no_args_is_help=True, help="Relatórios.")

MonthOpt = Annotated[str | None, typer.Option("--month", help="AAAA-MM, default mês atual")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Saída em JSON")]


def _month(text: str | None) -> tuple[int, int]:
    if text is None:
        today = date.today()
        return today.year, today.month
    return parse_month(text)


def _summary(ctx: Context, month: str | None):  # type: ignore[no-untyped-def]  # reason: returns MonthSummary; annotated below
    year, m = _month(month)
    conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
    return month_summary(conn, year, m, ctx.budget)


@report_app.command("month")
def month(month: MonthOpt = None, as_json: JsonOpt = False) -> None:
    """Receitas, despesas por categoria vs orçamento e saldo do mês."""

    def _go() -> None:
        ctx = load_context()
        summary = _summary(ctx, month)
        if as_json:
            emit_json(summary)
            return
        emit_table(
            f"Resumo {summary.year:04d}-{summary.month:02d}",
            ["receitas", "despesas", "saldo", "sem categoria", "manuais pendentes"],
            [[summary.income, summary.expenses, summary.net, summary.uncategorized, summary.pending_manual]],
        )
        emit_table(
            "Por categoria",
            ["categoria", "gasto", "orçamento", "%"],
            [[line.category, line.spent, line.budget, line.pct] for line in summary.lines],
        )

    run(_go)


@report_app.command("budget")
def budget(month: MonthOpt = None, as_json: JsonOpt = False) -> None:
    """Categoria × orçamento × realizado."""

    def _go() -> None:
        ctx = load_context()
        summary = _summary(ctx, month)
        lines = [line for line in summary.lines if line.budget is not None]
        if as_json:
            emit_json(lines)
            return
        emit_table(
            f"Orçamento {summary.year:04d}-{summary.month:02d}",
            ["categoria", "gasto", "orçamento", "%"],
            [[line.category, line.spent, line.budget, line.pct] for line in lines],
        )

    run(_go)


@report_app.command("balance")
def balance(as_json: JsonOpt = False) -> None:
    """Saldo por conta e fatura aberta por cartão."""

    def _go() -> None:
        ctx = load_context()
        conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
        rows = account_balances(conn, ctx.accounts, date.today())
        if as_json:
            emit_json(rows)
            return
        emit_table(
            "Saldos",
            ["conta", "tipo", "saldo", "fatura aberta", "mês"],
            [[r.name, r.type, r.balance, r.open_invoice, r.open_invoice_month] for r in rows],
        )

    run(_go)


@report_app.command("invoice")
def invoice(
    account: Annotated[str, typer.Option("--account")],
    month: MonthOpt = None,
    as_json: JsonOpt = False,
) -> None:
    """Detalhe da fatura de um cartão."""

    def _go() -> None:
        ctx = load_context()
        acct = resolve_account(ctx, account)
        year, m = _month(month)
        conn = open_db(ctx.data_root, ctx.cache_root, ctx.accounts, ctx.budget)
        inv = build_invoice(conn, acct, year, m)
        if as_json:
            emit_json(inv)
            return
        emit_table(
            f"Fatura {acct.name} {year:04d}-{m:02d} ({inv.start} a {inv.end}, vence {inv.due})",
            ["data", "descrição", "valor", "categoria", "parcela", "status"],
            [[l.date, l.description, l.amount, l.category, l.installment, l.status] for l in inv.lines],
        )
        emit_table("Totais", ["compras", "pagamentos", "a pagar"], [[inv.purchases, inv.payments, inv.total_due]])

    run(_go)
```

Troque o `# type: ignore` de `_summary` por uma anotação real: `def _summary(ctx: Context, month: str | None) -> MonthSummary:` importando `MonthSummary` de `finance.reports.month` (mypy strict não aceita função sem anotação).

Em `cli/__init__.py`:
```python
from finance.cli.report import report_app  # noqa: E402  # reason: registered after `app` exists

app.add_typer(report_app, name="report")
```

- [ ] **Step 4: Ver passar** → `uv run pytest -v` tudo PASS
- [ ] **Step 5: Lint/mypy** → limpos (ajuste nomes de variável `l` → `line` se ruff E741 acusar)
- [ ] **Step 6: Commit** — `git add src/finance/render src/finance/cli tests/test_render.py tests/test_cli_report.py && git commit -m "feat: comandos finance report month/budget/balance/invoice"`

---

### Task 16: Dados de exemplo + docs

**Files:**
- Create: `examples/data/accounts.yaml`, `examples/data/categories.yaml`, `examples/data/budget.yaml`, `examples/data/rules.yaml`
- Modify: `README.md`, `docs/cli.md` (novo)

- [ ] **Step 1: Dados de exemplo (fictícios; o usuário copia pro `data/` do repo dele e edita)**

`examples/data/accounts.yaml`:
```yaml
accounts:
  - id: nu
    name: Nubank conta
    bank: nubank
    type: checking
  - id: nu-card
    name: Nubank cartão
    bank: nubank
    type: credit
    closing_day: 1
    due_day: 8
  - id: bra
    name: Bradesco conta
    bank: bradesco
    type: checking
  - id: bra-card
    name: Bradesco cartão
    bank: bradesco
    type: credit
    closing_day: 1
    due_day: 10
```

`examples/data/categories.yaml`:
```yaml
casa: [aluguel, condominio, luz, agua, internet, mercado, manutencao]
transporte: [uber, combustivel, estacionamento, transporte-publico]
alimentacao: [restaurante, delivery, padaria]
saude: [plano, farmacia, consulta]
lazer: [streaming, viagem, bar, cinema]
pessoal: [roupas, eletronicos, presentes, educacao]
financeiro: [tarifas, juros, seguros]
renda: [salario, freelance, rendimentos, reembolso]
```

`examples/data/budget.yaml`:
```yaml
{}
```

`examples/data/rules.yaml`:
```yaml
rules: []
```

- [ ] **Step 2: Smoke real**

Run: `FINANCE_DATA_DIR=examples/data FINANCE_CACHE_DIR=/tmp/finance-cache uv run finance rebuild && FINANCE_DATA_DIR=examples/data FINANCE_CACHE_DIR=/tmp/finance-cache uv run finance report balance`
Expected: tabela com as 4 contas zeradas.

- [ ] **Step 3: `docs/cli.md`** — copie a tabela de comandos da spec (só os que existem: `add`, `rebuild`, `report month|budget|balance|invoice`), um exemplo de cada, e a nota das env vars `FINANCE_DATA_DIR`/`FINANCE_CACHE_DIR`, e como montar o repo privado de dados (copiar `examples/data/` para `data/`, `.claude/settings.json` com `"finance-plugin@finance": true`). No `README.md`, adicione a seção `## Comandos` apontando pra `docs/cli.md`.

- [ ] **Step 4: Gate completo** — `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q` → verde.

- [ ] **Step 5: Commit + push**

```bash
git add examples docs README.md
git commit -m "docs: dados iniciais e referência do CLI"
git push
```

---

## Fora deste plano (Plano 2)

`finance import` (parsers Nubank/Bradesco CSV/OFX/PDF), `finance reconcile`, `finance categorize`, `rules.yaml` e as skills (`lancar`, `importar`, `categorizar`, `fechar-mes`, `saldo`). Escrever o Plano 2 quando este estiver mergeado.
