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

## Comandos

Ver `docs/cli.md`.

Design: `docs/superpowers/specs/2026-09-09-finance-v1-design.md`.
