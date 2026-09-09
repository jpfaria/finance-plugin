---
name: fechar-mes
description: Use quando o usuário quiser o fechamento do mês no controle financeiro — "como foi o mês", "fecha setembro", "quanto gastei esse mês", "como tá o orçamento", "quanto vai vir de fatura".
---

# Fechar mês

Resumo do mês: entradas, saídas por categoria contra o orçamento, faturas dos cartões e o que ficou pendente.

## Comandos

Rode a partir do diretório do projeto de dados do usuário:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance report month --month AAAA-MM
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance report invoice --account <cartão> --month AAAA-MM
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance reconcile
```

Uma `report invoice` por conta `type: credit` em `data/accounts.yaml`. Use `--json` quando for reformatar a saída; sem `--json` a CLI já imprime tabela pronta.

## Como apresentar

1. Uma linha de saldo do mês: entradas, saídas, resultado.
2. As categorias que estouraram o orçamento (`%` acima de 100), maior primeiro. Só essas.
3. Uma linha por cartão: total a pagar e vencimento.
4. Pendências, se houver: `sem categoria` maior que zero → chame a skill `categorizar`; `manuais pendentes` maior que zero ou sobras no `reconcile` → diga que falta importar o extrato.

## Nunca

- Somar, projetar ou recalcular por fora. Todo número vem da CLI.
- Omitir as pendências porque o resumo "ficou bonito" — elas são o que torna o número confiável.
- Inventar comparação com meses anteriores sem rodar `report month` naqueles meses.
