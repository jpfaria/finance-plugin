# finance recategorize — reaplicar rules.yaml no que já está gravado

**Issue:** https://github.com/jpfaria/finance-plugin/issues/4

**Goal:** `finance recategorize [--month AAAA-MM] [--group X] [--dry-run] [--force]` reaplica `rules.yaml` nos lançamentos já gravados em `data/ledger/`, sem nunca sobrescrever categoria posta à mão.

**Decisão de design central.** O `Entry` ganha `category_source` (`""` / `rule` / `manual`) e o CSV ganha a coluna `category_source`. Alternativas descartadas:

- *Arquivo paralelo de ids manuais* — segundo lugar pra desincronizar, e a origem da categoria é fato do lançamento: mora no lançamento (Data Ownership).
- *Reusar `source`* — `source` diz de onde veio o **lançamento** (`manual`, `extrato.ofx`); a origem da **categoria** é outro fato. Dois fatos num campo é o acoplamento que a regra proíbe.

**Migração:** linha gravada antes da coluna existir conta como `rule` quando tem categoria, `""` quando não tem. Nenhum passo manual, nenhuma reimportação.

**Quem grava o quê:**

| Caminho | `category_source` |
|---|---|
| `finance import`, regra casou | `rule` |
| `finance import`, nenhuma regra casou | `""` |
| `finance add --category C` | `manual` |
| `finance add` sem categoria | `""` |
| `finance categorize set` | `manual` |
| `finance recategorize` | `rule` |
| `reconcile merge` | preserva o do manual |

**Regras do comando:**

- Sem flags: só avalia quem está sem categoria.
- `--force`: avalia também quem tem categoria `rule`. **Nunca** toca em `manual`.
- Nenhuma regra casa → **mantém** a categoria atual. `--force` com `rules.yaml` vazio não pode zerar a base.
- Transferência fica fora do escopo, igual ao `finance categorize` de hoje.
- `--dry-run` imprime e não grava.
- Relatório: quantos mudaram, quantos seguem sem categoria no escopo.

## Estrutura de arquivos

```
src/finance/model/entry.py              # + CategorySource, Entry.category_source
src/finance/ledger/csv_io.py            # + coluna category_source (com migração)
src/finance/cache/schema.py             # + coluna category_source
src/finance/actions/add.py              # categoria digitada = manual
src/finance/actions/categorize.py       # set_category = manual
src/finance/actions/import_statement.py # regra casou = rule
src/finance/actions/recategorize.py     # reapply_rules (função pura)
src/finance/cli/recategorize.py         # wiring
src/finance/cli/__init__.py             # registra o comando
docs/cli.md                             # tabela + seção de origem da categoria
skills/categorizar/SKILL.md             # oferece o comando depois de gravar regra
```

## Tasks

- [ ] Todos os testes (`tests/test_action_recategorize.py`, `tests/test_cli_recategorize.py`, extensões em `test_csv_io.py`, `test_action_add.py`, `test_action_categorize.py`, `test_action_import.py`, `test_cache.py`), uma rodada RED.
- [ ] `CategorySource` + `Entry.category_source` + coluna no CSV com migração + coluna no cache.
- [ ] Origem gravada por `add`, `categorize set` e `import`.
- [ ] `reapply_rules` e `finance recategorize`.
- [ ] `docs/cli.md` e `skills/categorizar/SKILL.md` no mesmo commit.
- [ ] Gate verde, merge em `main`, push, issue #4 fechada.
