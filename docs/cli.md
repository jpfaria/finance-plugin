# CLI `finance`

Todo comando lê os dados de `FINANCE_DATA_DIR` (default `./data`) e o cache de `FINANCE_CACHE_DIR` (default `./.cache`). Rode a partir do seu repo privado de dados, ou exporte as variáveis.

| Comando | Faz |
|---|---|
| `finance add --account X --amount V --desc "..." [--date AAAA-MM-DD] [--category C] [--installments N] [--tags a,b]` | Grava lançamento(s) `manual`. Com `--installments N` (só cartão), divide em N parcelas mensais. |
| `finance rebuild` | Recria `.cache/finance.db` a partir de `data/`. Os relatórios fazem isso sozinhos quando `data/` está mais novo. |
| `finance report month [--month AAAA-MM] [--json]` | Receitas, despesas por categoria vs orçamento, saldo do mês. |
| `finance report budget [--month AAAA-MM] [--json]` | Só categorias com orçamento: gasto, teto, %. |
| `finance report balance [--json]` | Saldo por conta e fatura aberta por cartão. |
| `finance report invoice --account X [--month AAAA-MM] [--json]` | Detalhe da fatura do cartão (período, vencimento, linhas, totais). |

`--account` aceita o `id` exato ou parte do nome (`"nubank cart"`); ambiguidade é erro.

## Exemplos

```bash
finance add --account nu --amount -50 --desc "uber" --category transporte/uber
finance add --account nu-card --amount -3000 --desc "celular" --installments 10
finance report month --month 2026-09
finance report invoice --account nu-card --month 2026-10 --json
```

## Montar o repo privado de dados

1. Crie um repo privado e copie `examples/data/` deste plugin para `data/`.
2. Edite `data/accounts.yaml` (contas e cartões, dia de fechamento/vencimento) e `data/categories.yaml`.
3. `.claude/settings.json` com `{"enabledPlugins": {"finance-plugin@finance": true}}`.
4. `.gitignore` com `imports/` e `.cache/`.
