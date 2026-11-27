# CLI `finance`

Todo comando lê os dados de `FINANCE_DATA_DIR` (default `./data`) e o cache de `FINANCE_CACHE_DIR` (default `./.cache`). Rode a partir do seu repo privado de dados, ou exporte as variáveis.

| Comando | Faz |
|---|---|
| `finance add --account X --amount V --desc "..." [--date AAAA-MM-DD] [--category C] [--installments N] [--tags a,b]` | Grava lançamento(s) `manual`. Com `--installments N` (só cartão), divide em N parcelas mensais. |
| `finance rebuild` | Recria `.cache/finance.db` a partir de `data/`. Os relatórios fazem isso sozinhos quando `data/` está mais novo. |
| `finance report month [--month AAAA-MM] [--json]` | Receitas, despesas por categoria vs orçamento, saldo do mês. |
| `finance report budget [--month AAAA-MM] [--json]` | Só categorias com orçamento: gasto, teto, %. |
| `finance report balance [--json]` | Saldo por conta e fatura aberta por cartão. |
| `finance report forecast [--month AAAA-MM] [--base N] [--from AAAA-MM --to AAAA-MM] [--json]` | Previsão por categoria: o que cada uma custou em cada mês da base e a média por mês. |
| `finance report pdf --out arquivo.pdf [--month AAAA-MM] [--base N] [--from AAAA-MM --to AAAA-MM]` | A previsão em PDF, com gráficos. Imprime pelo Chrome/Chromium/Edge da máquina e deixa o `.html` ao lado. |
| `finance report cash [--month AAAA-MM] [--json]` | Caixa do mês por conta: saldo inicial, o que entrou, o que saiu e o saldo final. |
| `finance report invoice --account X [--month AAAA-MM] [--json]` | Detalhe da fatura do cartão (período, vencimento, linhas, totais). |
| `finance import <arquivo> --account X` | Importa um extrato (OFX, CSV de conta ou de cartão do Nubank, CSV e PDF de conta do Bradesco, PDF da fatura do cartão Bradesco). Dedupe por hash: reimportar o mesmo arquivo não duplica. Aplica `rules.yaml`. |
| `finance reconcile [--window 3] [--stale-days 45] [--json]` | Casa lançamentos manuais com os importados, relata importados sem par e manuais antigos. |
| `finance categorize [--month AAAA-MM] [--json]` | Lista lançamentos sem categoria. |
| `finance categorize set <id> <categoria> [--rule "<regex>"]` | Aplica a categoria **à mão** e, com `--rule`, grava a regra em `rules.yaml`. |
| `finance recategorize [--month AAAA-MM] [--group X] [--dry-run] [--force]` | Reaplica `rules.yaml` no que já está gravado. Sem flags, só mexe em quem está sem categoria. |
| `finance transfer [--days 5] [--json]` | Lista pares que parecem transferência (valores opostos, contas diferentes) e ainda não estão marcados. |
| `finance transfer set <id> <id>... [--force]` | Marca as pernas como uma transferência: o `report month` passa a ignorar as duas. |
| `finance transfer clear <id>...` | Tira a marca. |
| `finance split <id> --part valor:categoria --part valor:categoria` | Rateia uma cobrança em partes com categorias diferentes. |

`--account` aceita o `id` exato ou parte do nome (`"nubank cart"`); ambiguidade é erro.

## Dinheiro que só muda de lugar: `transfer`

Pagar a fatura do cartão não é despesa nova — a despesa são as compras, que já estão lançadas uma por uma na conta do cartão. Se o pagamento ficar como despesa na conta corrente, o mês conta o cartão duas vezes. O mesmo vale pra PIX entre duas contas do próprio dono.

As duas pernas continuam no ledger (cada extrato traz a sua), mas com o mesmo `transfer_group`:

- `report month` ignora as duas, então nem a saída vira despesa nem a entrada vira receita;
- `report invoice` lê o crédito marcado como **pagamento** da fatura, não como estorno;
- `categorize` e `recategorize` não pedem categoria pra elas.

```bash
finance transfer                            # pares candidatos, com os dois ids
finance transfer set <id-saida> <id-entrada>
finance transfer clear <id> <id>            # desfaz
```

A soma das pernas tem que dar zero: é o que prova que o dinheiro só mudou de lugar. Perna sozinha — a outra está num extrato que não foi importado — só com `--force`, porque aí a decisão é sua e não dá pra conferir.

**Cuidado com o cartão que não é conta no `accounts.yaml`.** Se as compras daquele cartão não estão no ledger, o pagamento da fatura é o *único* registro daquele gasto: marcar como transferência apaga a despesa do relatório. Só marque quando as duas pontas estiverem no ledger.

## Uma cobrança, duas coisas: `split`

Uma linha de 868 na fatura que é a soma de duas assinaturas não tem como ter duas categorias. `finance split` troca o lançamento por partes que somam exatamente o mesmo valor:

```bash
finance split <id> --part 576:barco/starlink --part 292:casa/internet
```

- Os valores são positivos e precisam somar o valor original (o sinal é herdado: saída continua saída).
- A primeira parte **mantém o id** do lançamento original, pra nada que aponte pra ele ficar órfão.
- Todas as partes guardam o `import_hash` do original, que é a chave de deduplicação: reimportar o extrato não grava a cobrança de novo.
- A categoria de cada parte entra como `manual`, então `recategorize --force` não desfaz o rateio.
- A descrição ganha `- Rateio N/M`.

Perna de transferência não se rateia (não entra em relatório): use `finance transfer clear` antes.

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

`report month`, `report budget`, `report balance`, `report cash`, `report forecast` e `recategorize` aceitam `--group X`: contam só as contas daquele grupo. Sem a flag, agregam tudo. Grupo que nenhuma conta declara é erro.

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

## Trocar o CSV pelo PDF na conta do Bradesco

No CSV da conta, todo PIX vira `PIX ENVIADO` ou `PIX RECEBIDO` sem nome, e boleto vira `PAGTO ELETRON COBRANCA` — nenhuma regra de categoria consegue casar. O PDF do extrato (no app: Extrato → exportar) traz a outra ponta na linha de baixo do lançamento, e a descrição importada fica `PIX ENVIADO — POSTO EXEMPLO`, `PAGTO ELETRON COBRANCA — CONDOMINIO EXEMPLO`, `CONTA DE LUZ — ENEL DISTRIB. RJ-00012345`. **Para a conta do Bradesco, prefira o PDF.**

O preço de trocar: o dedupe é por hash de `conta|data|valor|descrição|docto`, e a descrição é exatamente o que muda. Reimportar o PDF de um período que já entrou pelo CSV **duplica cada lançamento** — e `finance reconcile` não pega isso, porque ele casa manual com importado, não importado com importado. Não existe migração automática: apague o que veio do CSV e importe o PDF.

```bash
grep -rl ",extrato.csv," data/ledger/        # meses com lançamento daquele CSV
sed -i '' '/,extrato\.csv,/d' data/ledger/2026-10.csv
finance import extrato.pdf --account bra
finance rebuild
```

Antes de apagar, veja se algum desses lançamentos tem categoria posta à mão (`category_source=manual` no CSV do mês): essa escolha se perde e precisa ser refeita com `finance categorize set`. Categoria que veio de regra volta sozinha no `import`.

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
| Bradesco | conta | PDF do app (**preferido**: traz o nome de quem enviou/recebeu o PIX) |
| Bradesco | conta | CSV `;` do internet banking (cabeçalho `Data;Histórico;Docto.;Crédito (R$);Débito (R$);Saldo (R$)` na 2ª linha) |
| Bradesco | cartão | PDF da fatura (o banco não exporta outro formato) |

O extrato de conta do Bradesco em PDF é lido com as colunas preservadas: é a posição de `Crédito (R$)` e `Débito (R$)` que diz se o valor é entrada ou saída, e a régua é lida no cabeçalho de cada folha. A data vem da primeira transação do dia (as seguintes herdam) e as somas são conferidas com a linha `Total` — se não fecham, o import falha em vez de entrar faltando lançamento.

A fatura do Bradesco em PDF é lida inteira, inclusive os lançamentos que continuam depois do rodapé: data, descrição, valor, parcela (`- Parcela N/M` na descrição) e sinal igual ao do cartão Nubank — compra negativa, pagamento da fatura e estorno positivos. O ano, que não aparece na linha, vem do vencimento impresso na própria fatura. Parcela é gravada no 1º dia do mês do vencimento, não no dia da compra original: a cobrança é agora, e a data antiga jogaria a despesa num mês que já fechou.

Outro banco ou formato: `finance import` falha com "formato não reconhecido". Abra uma issue com um extrato anonimizado para o parser ser escrito — nunca edite o arquivo para "caber" num formato existente.

## Montar o repo privado de dados

1. Crie um repo privado e copie `examples/data/` deste plugin para `data/`.
2. Edite `data/accounts.yaml` (contas e cartões, dia de fechamento/vencimento) e `data/categories.yaml`.
3. `.claude/settings.json` com `{"enabledPlugins": {"finance-plugin@finance": true}}`.
4. `.gitignore` com `imports/` e `.cache/`.

## Previsão: `report forecast`

Quanto cada categoria costuma custar por mês, pra estimar um mês que ainda não aconteceu.

- A base são meses **fechados**: por padrão os `--base N` meses imediatamente antes do mês previsto (N = 3). `--from AAAA-MM --to AAAA-MM` escolhe a janela na mão — use quando um mês da base está incompleto (conta importada no meio do mês, por exemplo), porque mês incompleto puxa a média pra baixo em silêncio.
- A média divide por **todos** os meses da base, mesmo onde a categoria não apareceu: um gasto único em três meses entra como um terço. A coluna `meses` (2/3) e a separação em duas tabelas — **Todo mês** e **Eventual** — mostram o que é recorrente e o que foi pontual.
- Competência, igual ao `report month`: compra no cartão conta no mês da compra, e perna de transferência não conta.
- A linha `(sem categoria)` entra na previsão. Categorizar muda a previsão, não o total.
- Não há sazonalidade: a previsão é a média da base repetida. Dezembro, IPVA, IPTU e matrícula não aparecem se não estiverem nos meses da base.

## PDF: `report pdf`

Mesma previsão do `report forecast`, em página A4 com gráficos de barra, tabela e as ressalvas impressas no rodapé.

- Quem imprime é o navegador já instalado (Chrome, Chromium ou Edge, nessa ordem), em modo headless. **Nenhuma dependência nova** e nada é baixado: a página é autocontida, com os gráficos em SVG inline e o CSS embutido. `FINANCE_BROWSER` aponta outro executável.
- O `.html` fica salvo ao lado do `.pdf`: dá pra abrir, conferir e reimprimir sem rodar a CLI.
- O PDF tem os valores do usuário. Ele é saída descartável — gere em `.cache/` do repo de dados, nunca dentro deste repo.

## Saldo de verdade: `opening_balance` e `report cash`

O ledger só tem o que foi importado, então somar lançamento dá movimento, não saldo. Pra o saldo bater com o banco, a conta declara em `accounts.yaml`:

```yaml
  - id: bra
    name: Bradesco conta
    bank: bradesco
    type: checking
    opening_balance: -3675.37
    opening_date: 2026-09-28
```

- `opening_balance` é o saldo **na véspera** do primeiro lançamento importado (`opening_date`), com sinal: negativo é conta no vermelho. Os dois andam juntos; um sem o outro é erro.
- Onde achar: no extrato. Atenção à coluna de saldo do Bradesco — ela imprime o **módulo**, sem sinal. Confira a aritmética linha a linha antes de copiar um número de lá: se um débito faz o saldo impresso **subir**, a conta está negativa.
- `report balance` passa a mostrar o saldo do banco e a coluna `fonte` diz `banco` ou `só movimento`.
- `report cash` é a visão de caixa: entra tudo que mexeu na conta, **inclusive perna de transferência** (pagar a fatura é dinheiro saindo), e cartão não aparece. É o complemento do `report month`, que é competência e conta a compra no mês da compra.
