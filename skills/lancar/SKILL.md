---
name: lancar
description: Use quando o usuário contar um gasto, uma compra, um recebimento ou uma transferência em linguagem natural — "gastei 50 no uber", "comprei um celular em 10x no nubank", "caiu o salário", "paguei a fatura do cartão" — e isso precisar virar lançamento no controle financeiro.
---

# Lançar

Transforma o que o usuário falou em `finance add`. A CLI é a única fonte de verdade: você não calcula parcela, não soma saldo, não edita CSV.

## Comando

Rode a partir do diretório do projeto de dados do usuário (o que tem `data/`):

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance add \
  --account <id-ou-parte-do-nome> --amount <valor> --desc "<descrição>" \
  [--date AAAA-MM-DD] [--category <grupo/item>] [--installments N] [--tags a,b]
```

## Regras do valor e da parcela

| Situação | O que passar |
|---|---|
| Gasto, compra, pagamento | `--amount` NEGATIVO (`-50`) |
| Salário, recebimento, reembolso, venda | `--amount` POSITIVO (`3000`) |
| Parcelado | `--amount` = valor TOTAL da compra, `--installments N`. A CLI divide. Nunca passe o valor da parcela. |
| Parcelado | Só existe em conta `type: credit`. Em conta corrente a CLI recusa — e ela está certa. |
| Sem data dita | Omita `--date` (default hoje). "Ontem" / "dia 3" → calcule e passe explícito. |

## Antes de rodar

1. **Conta:** `--account` aceita o id ou parte do nome. Se o que o usuário disse casar com mais de uma conta (ex.: "nubank" com conta e cartão), a CLI falha com "conta ambígua" — pergunte qual, em uma linha, e repita o comando. Não escolha por ele.
2. **Categoria:** use só um caminho que exista em `data/categories.yaml` (leia o arquivo). Óbvio pelo texto ("uber" → `transporte/uber`) → use. Ambíguo → deixe sem `--category`; o pendente aparece depois em `categorize`. Nunca invente categoria nem edite `categories.yaml` sem o usuário pedir.
3. **Pagamento de fatura é transferência, não despesa:** são DOIS lançamentos, saída na conta corrente e entrada no cartão. Isso ainda não tem comando próprio — diga isso ao usuário e não registre como despesa.

## Depois

Repita em uma linha o que foi gravado (valor, conta, data, parcelas) e o id. Nada além disso.

## Nunca

- Ler o código-fonte da CLI para descobrir o que uma flag faz — está tudo aqui e em `finance add --help`.
- Editar `data/ledger/*.csv` na mão.
- Calcular o valor da parcela você mesmo.
- Registrar sem saber a conta.
