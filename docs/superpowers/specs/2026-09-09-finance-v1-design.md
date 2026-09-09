# finance v1 — design

Controle financeiro pessoal operado só via Claude Code: skills finas chamam um CLI Python testado; os dados vivem em arquivos texto versionados num repo privado separado.

## Dois repositórios

| Repo | Visibilidade | Contém |
|---|---|---|
| `jpfaria/finance-plugin` (este) | público | Plugin Claude Code: `.claude-plugin/`, `skills/`, o pacote Python `src/finance/`, testes, `examples/data/`. **Nada pessoal**: nenhum nome de conta, valor ou extrato real. |
| `jpfaria/finance` | privado | Só os dados do usuário: `data/` (yaml + `ledger/*.csv`), `.claude/settings.json` habilitando o plugin, `CLAUDE.md` curto. Zero código. |

O plugin nunca assume um usuário específico: bancos suportados são parsers genéricos, contas e categorias vêm sempre do `data/` de quem instala. O CLI acha os dados por `FINANCE_DATA_DIR` (default `./data`, ou seja, o repo `finance` aberto como projeto).

## Decisões fechadas

| Tema | Decisão |
|---|---|
| Uso | Só Claude Code (skills). Sem app/UI. |
| Entrada | Lançamentos falados/digitados **e** extratos exportados (Nubank, Bradesco). |
| Persistência | Canônico = texto versionado (`data/`). SQLite gitignorado, regenerável, só pra consulta. |
| Linguagem | Python (uv, ruff, mypy --strict, pytest). Código em inglês; docs/skills/commits/issues em pt-BR. |
| Escopo v1 | Fluxo de caixa + contas/cartões com saldo e fatura. Sem investimentos. |
| Moeda | BRL. |
| Skills | Finas: sabem qual comando rodar e como conversar; lógica no Python. |
| Distribuição | Plugin Claude Code (`finance-plugin@finance`), instalado via marketplace do próprio repo. |
| Disciplina | `claude-plugin@xgodev` como dependência do projeto (skill `dev`); folha Python pedida em xgodev/claude-plugin#24. |

## Dados (repo `finance`)

```
data/
  accounts.yaml        # contas e cartões
  categories.yaml      # árvore de categorias
  rules.yaml           # descrição → categoria
  budget.yaml          # orçamento mensal por categoria
  ledger/YYYY-MM.csv   # lançamentos do mês
imports/               # extratos crus (gitignored)
.cache/finance.db      # SQLite (gitignored), rebuild a partir de data/
```

### accounts.yaml
Cada conta: `id`, `name`, `bank` (`nubank` | `bradesco`), `type` (`checking` | `credit`), e para `credit`: `closing_day`, `due_day`.

### categories.yaml
Árvore de dois níveis (`casa/aluguel`, `transporte/uber`). Categoria é referenciada pelo caminho completo.

### rules.yaml
Lista ordenada de `{pattern, category}`; `pattern` é regex case-insensitive sobre a descrição. Primeira que casa vence. Criadas pela skill `categorizar` quando o usuário aprova uma sugestão.

### budget.yaml
`{category: valor_mensal}`. Categoria sem entrada = sem teto.

### ledger/YYYY-MM.csv
Um arquivo por mês (mês do `date`). Colunas:

| Coluna | Conteúdo |
|---|---|
| `id` | ULID |
| `date` | ISO `YYYY-MM-DD` (data da compra/movimento) |
| `account` | `accounts.yaml#id` |
| `amount` | decimal com 2 casas; negativo = saída, positivo = entrada |
| `description` | texto livre |
| `category` | caminho em `categories.yaml`, ou vazio = pendente |
| `tags` | separadas por `;`, opcional |
| `installment` | `n/N` quando parcelado, senão vazio |
| `installment_group` | ULID comum às N parcelas, senão vazio |
| `transfer_group` | ULID que liga as duas pontas de uma transferência, senão vazio |
| `status` | `manual` (dito pelo usuário, ainda não veio no extrato) ou `confirmed` (veio do extrato ou foi conciliado) |
| `source` | `manual` ou nome do arquivo importado |
| `import_hash` | sha256 do registro cru do extrato; vazio em `manual` |

Regras:
- Compra no cartão = lançamento na conta `credit` no dia da compra. Parcela = N lançamentos, um por mês, mesma `installment_group`.
- Pagamento de fatura = transferência `checking → credit` (dois lançamentos com o mesmo `transfer_group`). Transferência não é despesa nem receita.
- Saldo da conta e fatura do cartão são **derivados** do ledger, nunca digitados.
- `import_hash` é a chave de dedupe: reimportar o mesmo extrato não duplica.

## Fatura do cartão
Fatura do mês M de um cartão = soma dos lançamentos daquela conta com `date` entre o fechamento de M-1 (exclusivo) e o fechamento de M (inclusivo), menos pagamentos recebidos no período. `closing_day`/`due_day` vêm de `accounts.yaml`.

## Layout do plugin (repo `finance-plugin`)

```
.claude-plugin/plugin.json        # name: finance-plugin
.claude-plugin/marketplace.json   # name: finance, plugins: [finance-plugin]
skills/<nome>/SKILL.md            # lancar, importar, categorizar, fechar-mes, saldo
src/finance/                      # pacote Python do CLI
tests/
examples/data/                    # accounts/categories/budget/rules de exemplo, sem dados reais
pyproject.toml, uv.lock
```

As skills chamam o CLI por `uv run --project "${CLAUDE_PLUGIN_ROOT}" finance <cmd>`, sempre a partir do diretório do projeto `finance` (onde está `data/`). Instalação: `claude plugin marketplace add jpfaria/finance-plugin` + `claude plugin install finance-plugin@finance`.

## CLI (`finance`)

Pacote `src/finance/`, entry point `finance` via `[project.scripts]`. Saída humana em tabela; `--json` em todo comando de leitura.

| Comando | Faz |
|---|---|
| `finance add --account X --amount V --date D --desc "..." [--category C] [--installments N]` | Cria lançamento(s) `manual`. Com `--installments N`, divide o valor em N parcelas mensais (resto na última) a partir de `--date`. |
| `finance import <arquivo> --account X` | Detecta o formato (ver abaixo), normaliza, dedupe por `import_hash`, aplica `rules.yaml`, grava `confirmed`. Relata: novos, duplicados, sem categoria. |
| `finance reconcile [--window 3]` | Casa `manual` × importados por `account` + `amount` + `date` ±janela + `installment`. Casou: mantém `category`/`description` do manual, herda `import_hash`/`source`, vira `confirmed`; o importado duplicado é removido. Relata sobras dos dois lados e `manual` com mais de `--stale-days` (default 45). |
| `finance categorize [--month M]` | Lista pendentes (`category` vazio). `finance categorize set <id> <category> [--rule "<regex>"]` aplica e opcionalmente grava regra. |
| `finance report month [--month M]` | Receitas, despesas por categoria vs orçamento, saldo do mês. |
| `finance report budget [--month M]` | Só categoria × orçamento × realizado × % . |
| `finance report balance` | Saldo atual por conta `checking`; fatura aberta por `credit`. |
| `finance report invoice --account X [--month M]` | Detalhe da fatura do cartão. |
| `finance rebuild` | Apaga e recria `.cache/finance.db` a partir de `data/`. Todo comando de leitura chama rebuild se o cache estiver mais velho que `data/`. |

### Formatos de import (v1)
| Banco | Produto | Formatos |
|---|---|---|
| Nubank | conta | CSV, OFX |
| Nubank | cartão | CSV, OFX |
| Bradesco | conta | CSV, OFX, PDF |
| Bradesco | cartão | CSV, OFX, PDF |

Detecção pela extensão + assinatura do cabeçalho; um parser por (banco, produto, formato), cada um num módulo próprio devolvendo a mesma lista de registros normalizados. Formato não reconhecido = erro claro, nada gravado.

## Skills (`.claude/skills/`)

| Skill | Quando | Chama |
|---|---|---|
| `lancar` | "gastei 50 no uber", "comprei celular em 10x no XPTO" | `finance add` (resolve conta por nome/apelido, pede o que faltar) |
| `importar` | usuário aponta um extrato | `finance import` → `finance reconcile` → oferece `categorizar` pros pendentes |
| `categorizar` | pendentes sem categoria | `finance categorize`; sugere categoria, usuário aprova, cria regra quando o padrão for reutilizável |
| `fechar-mes` | fim do mês | `report month` + `report invoice` por cartão + sobras do `reconcile` |
| `saldo` | "quanto tenho", "quanto vem de fatura" | `report balance` |

Skill não calcula nada: toda regra de negócio está no CLI e nos testes dele.

## Qualidade

- `uv` + `pyproject.toml` + `uv.lock`; `ruff` (lint+format), `mypy --strict`, `pytest`.
- TDD red-first (skill `dev` do `claude-plugin@xgodev`). Um módulo = uma responsabilidade.
- Fixtures de extrato anonimizadas e versionadas em `tests/fixtures/`; nunca extrato real no repo.
- CI (GitHub Actions): ruff + mypy + pytest a cada push/PR.
- `.gitignore`: `imports/`, `.cache/`, `.venv/`.
- `finance-plugin/.claude/settings.json` habilita `claude-plugin@xgodev` (disciplina de dev). `finance/.claude/settings.json` habilita `finance-plugin@finance`.
- `CLAUDE.md` curto em cada repo: idioma, layout, "regra de negócio só no CLI", "nada pessoal no plugin".

## Fora do v1 — backlog do v2

Registrado durante o desenvolvimento, sem issue aberta:

- **Relatórios bonitos com previsão.** Saída visual (HTML/artifact ou terminal rico) além da tabela atual, com projeção de fluxo de caixa: parcelas futuras já lançadas, faturas a vencer, renda recorrente. Hoje `report` só olha o passado.
- **Renda variável como cidadã de primeira classe.** Salário, aluguel recebido, freelance/PJ, venda de bens e reembolso já existem como categorias em `renda:`; falta relatório que separe renda fixa de variável.
- **Bot do Telegram.** Lançar e consultar por mensagem, sem abrir o Claude Code: "gastei 50 no uber" chega pelo Telegram e vira `finance add`. Precisa decidir onde o bot roda (máquina do usuário, VPS, container), como ele autentica (só o chat id dele), e como o repo de dados é commitado — o bot escreve em `data/` e precisa fazer commit/push sozinho. O CLI já serve como camada única: o bot chama os mesmos comandos que as skills.
- **Grupos de conta: FEITO** (`group:` livre em `accounts.yaml`, `--group` nos relatórios, `budget.yaml` com `geral` + `grupos`). PF e PJ são só dois valores possíveis.
- Investimentos/patrimônio, multi-moeda, app/UI, MCP server, import automático (API dos bancos).
- Formatos de extrato do Bradesco (CSV/PDF): faltam amostras anonimizadas para escrever o parser.
