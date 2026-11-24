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
| `finance import <arquivo> --account X` | Importa um extrato (OFX, CSV de conta ou de cartão do Nubank, CSV de conta do Bradesco). Dedupe por hash: reimportar não duplica. Aplica `rules.yaml`. |
| `finance reconcile [--window 3] [--stale-days 45] [--json]` | Casa lançamentos manuais com os importados, relata importados sem par e manuais antigos. |
| `finance categorize [--month AAAA-MM] [--json]` | Lista lançamentos sem categoria. |
| `finance categorize set <id> <categoria> [--rule "<regex>"]` | Aplica a categoria **à mão** e, com `--rule`, grava a regra em `rules.yaml`. |
| `finance recategorize [--month AAAA-MM] [--group X] [--dry-run] [--force]` | Reaplica `rules.yaml` no que já está gravado. Sem flags, só mexe em quem está sem categoria. |

`--account` aceita o `id` exato ou parte do nome (`"nubank cart"`); ambiguidade é erro.

## Regra nova no histórico: `recategorize`

`rules.yaml` é aplicado no `import`, mas uma regra escrita (ou corrigida) depois não precisa de reimportação: `finance recategorize` reaplica as regras nos lançamentos que já estão em `data/ledger/`. Nunca é preciso apagar a base canônica pra mudar uma categoria.

Cada lançamento guarda **de onde veio a categoria**, na coluna `category_source` do CSV:

| `category_source` | Quem gravou | `recategorize` mexe? |
|---|---|---|
| vazio | ninguém, lançamento sem categoria | sim, sempre |
| `rule` | `import` ou `recategorize` | só com `--force` |
| `manual` | `categorize set` ou `add --category` | **nunca**, nem com `--force` |

Lançamento gravado antes dessa coluna existir conta como `rule` quando tem categoria — a migração é automática, na primeira leitura.

```bash
finance recategorize --dry-run              # o que mudaria, sem gravar
finance recategorize                        # pega só quem está sem categoria
finance recategorize --force --month 2026-09  # reavalia também categoria de regra
```

Regra que não casa mais **não apaga** a categoria que ela pôs antes: `--force` com `rules.yaml` vazio não zera a base. Transferência fica fora do escopo, igual ao `finance categorize`. A saída lista cada mudança (`id  data  descrição: antes -> depois`) e fecha com quantos mudaram e quantos seguem sem categoria.

## Grupos de conta

Cada conta pode declarar `group: <nome livre>` em `accounts.yaml` — "pessoal", "pj", "familia", quantos você quiser. A lista de grupos sai das próprias contas; não existe segundo arquivo pra desincronizar.

`report month`, `report budget`, `report balance` e `recategorize` aceitam `--group X`: contam só as contas daquele grupo. Sem a flag, agregam tudo. Grupo que nenhuma conta declara é erro.

## Orçamento

`budget.yaml` tem duas seções. `geral` vale pra tudo; `grupos` sobrescreve por grupo, categoria a categoria:

```yaml
geral:
  transporte/uber: 300
grupos:
  pj:
    transporte/uber: 500
```

Num relatório com `--group pj`, `transporte/uber` usa 500; qualquer categoria sem limite próprio no grupo cai no `geral`.

## Exemplos

```bash
finance add --account nu --amount -50 --desc "uber" --category transporte/uber
finance add --account nu-card --amount -3000 --desc "celular" --installments 10
finance report month --month 2026-09
finance report invoice --account nu-card --month 2026-10 --json
```

## Formatos de extrato suportados

| Banco | Produto | Formatos |
|---|---|---|
| qualquer | conta ou cartão | OFX |
| Nubank | conta | CSV (`Data,Valor,Identificador,Descrição`) |
| Nubank | cartão | CSV (`date,title,amount`) |
| Bradesco | conta | CSV `;` (cabeçalho `Data;Histórico;Docto.;Crédito (R$);Débito (R$);Saldo (R$)` na 2ª linha) |

Outro banco ou formato: `finance import` falha com "formato não reconhecido". Abra uma issue com um extrato anonimizado para o parser ser escrito — nunca edite o arquivo para "caber" num formato existente.

## Montar o repo privado de dados

1. Crie um repo privado e copie `examples/data/` deste plugin para `data/`.
2. Edite `data/accounts.yaml` (contas e cartões, dia de fechamento/vencimento) e `data/categories.yaml`.
3. `.claude/settings.json` com `{"enabledPlugins": {"finance-plugin@finance": true}}`.
4. `.gitignore` com `imports/` e `.cache/`.
