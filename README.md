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

## Skills

| Skill | Dispara quando |
|---|---|
| `lancar` | "gastei 50 no uber", "comprei um celular em 10x" |
| `importar` | "baixei o extrato", "chegou a fatura" |
| `categorizar` | pendentes sem categoria |
| `fechar-mes` | "como foi o mês", "fecha setembro" |
| `saldo` | "quanto tenho", "quanto vem de fatura" |

## Comandos

Ver `docs/cli.md`. Formatos de extrato suportados: OFX (qualquer banco) e os CSV de conta e cartão do Nubank.

Roadmap: `docs/roadmap.md`. Design: `docs/superpowers/specs/2026-09-09-finance-v1-design.md`.
