# finance v1 — Plano 2: importação, conciliação, categorização e skills

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `finance import`, `finance reconcile`, `finance categorize` e as cinco skills do plugin, em cima do núcleo do Plano 1.

**Architecture:** `imports/` = parsers por formato atrás de um `Parser` Protocol + registry por assinatura de cabeçalho; `actions/` = funções puras (import, reconcile, categorize) sobre listas de `Entry`; `config/rules.py` = `rules.yaml`; `cli/` só wiring. Skills em `skills/<nome>/SKILL.md` chamam o CLI via `uv run --project "${CLAUDE_PLUGIN_ROOT}" finance …`.

**Tech Stack:** Python 3.12, ofxparse (OFX), csv (stdlib), pytest, ruff, mypy --strict.

**Spec:** `docs/superpowers/specs/2026-09-09-finance-v1-design.md`

## Global Constraints

- Mesmas do Plano 1 (código em inglês, pt-BR fora do código, RED-first, gate antes de cada commit, nada pessoal no repo).
- **Formato só com fonte de verdade.** Parser só nasce de um formato documentado (OFX = spec pública; Nubank CSV conta `Data,Valor,Identificador,Descrição` e cartão `date,title,amount` = formatos públicos do app). Bradesco CSV/PDF **não têm amostra**: ficam FORA deste plano; formato não reconhecido = erro claro pedindo amostra anonimizada. Nunca inventar layout.
- Fixtures de extrato são sintéticas e mínimas, versionadas em `tests/fixtures/`.
- Sinal de valor: sempre negativo = saída. OFX `TRNAMT` já vem assinado (spec); Nubank cartão CSV `amount` positivo = compra → negar.

---

## Estrutura de arquivos

```
src/finance/imports/__init__.py
src/finance/imports/record.py        # ImportedRecord + record_hash
src/finance/imports/parser.py        # Parser Protocol
src/finance/imports/registry.py      # detect(path) -> Parser
src/finance/imports/ofx.py           # OFX (qualquer banco)
src/finance/imports/nubank_checking_csv.py
src/finance/imports/nubank_card_csv.py
src/finance/config/rules.py          # Rule, load_rules, append_rule, apply_rules
src/finance/actions/import_statement.py
src/finance/actions/reconcile.py
src/finance/actions/categorize.py
src/finance/ledger/store.py          # + replace(updated, removed_ids)
src/finance/cli/import_cmd.py
src/finance/cli/reconcile.py
src/finance/cli/categorize.py
skills/lancar/SKILL.md
skills/importar/SKILL.md
skills/categorizar/SKILL.md
skills/fechar-mes/SKILL.md
skills/saldo/SKILL.md
tests/fixtures/{sample.ofx,nubank_checking.csv,nubank_card.csv}
docs/cli.md (atualizar), README.md (atualizar)
```

---

### Task 1: `ImportedRecord`, hash e `Parser` Protocol

**Files:** `src/finance/imports/{__init__,record,parser}.py`, `tests/test_import_record.py`

**Interfaces:**
- `ImportedRecord(date: date, amount: Decimal, description: str, external_id: str = "")` frozen.
- `record_hash(account_id: str, record: ImportedRecord) -> str` = sha256 hex de `f"{account_id}|{date ISO}|{amount 2 casas}|{description.strip()}|{external_id}"`.
- `Parser(Protocol)`: `name: str`; `matches(self, path: Path, head: str) -> bool`; `parse(self, path: Path) -> list[ImportedRecord]`.

- [ ] Teste:
```python
def test_hash_is_stable_and_account_scoped() -> None:
    rec = ImportedRecord(date(2026, 9, 1), Decimal("-10.00"), " uber ", "abc")
    same = ImportedRecord(date(2026, 9, 1), Decimal("-10"), "uber", "abc")
    assert record_hash("nu", rec) == record_hash("nu", same)
    assert record_hash("nu", rec) != record_hash("bra", rec)
    assert len(record_hash("nu", rec)) == 64
```
- [ ] RED → implementar → GREEN → commit `feat: contrato de registro importado e hash de dedupe`.

### Task 2: Parser OFX

**Files:** `src/finance/imports/ofx.py`, `tests/fixtures/sample.ofx`, `tests/test_import_ofx.py`; `pyproject.toml` += `ofxparse>=0.21`; `[[tool.mypy.overrides]] module="ofxparse.*" ignore_missing_imports=true` (reason: lib sem stubs; o valor é convertido em `Decimal`/`date` na fronteira).

**Interfaces:** `OfxParser` com `name="ofx"`, `matches` = extensão `.ofx` ou `head` contém `<OFX>`/`OFXHEADER`; `parse` → um `ImportedRecord` por transação (`date=trn.date.date()`, `amount=Decimal(str(trn.amount)).quantize(CENTS)`, `description=trn.memo or trn.payee`, `external_id=trn.id`).

- [ ] Fixture `sample.ofx` (SGML OFX 1.02 mínimo, 2 transações: `-35.90` "UBER TRIP" id `T1`, `1200.00` "PIX RECEBIDO" id `T2`).
- [ ] Teste: parse devolve 2 registros com esses valores; `matches` aceita `.ofx`.
- [ ] RED → implementar → GREEN → commit `feat: parser OFX`.

### Task 3: Parsers Nubank CSV (conta e cartão)

**Files:** `src/finance/imports/nubank_checking_csv.py`, `src/finance/imports/nubank_card_csv.py`, fixtures, `tests/test_import_nubank.py`.

**Interfaces:**
- `NubankCheckingCsv`: `name="nubank-checking-csv"`, `matches` = cabeçalho `Data,Valor,Identificador,Descrição`; linha: `Data` = `DD/MM/YYYY`, `Valor` assinado com ponto decimal, `Identificador` → `external_id`.
- `NubankCardCsv`: `name="nubank-card-csv"`, `matches` = cabeçalho `date,title,amount`; `date` ISO, `amount` positivo = compra → `-amount`; `external_id=""`.

- [ ] Fixtures sintéticas (2 linhas cada) e testes de `matches` + `parse`.
- [ ] RED → implementar → GREEN → commit `feat: parsers CSV do Nubank (conta e cartão)`.

### Task 4: Registry `detect`

**Files:** `src/finance/imports/registry.py`, `tests/test_import_registry.py`.

**Interfaces:** `PARSERS: tuple[Parser, ...] = (OfxParser(), NubankCheckingCsv(), NubankCardCsv())`; `detect(path: Path) -> Parser` lê os primeiros 512 chars (`utf-8`, `errors="replace"`) e devolve o primeiro `matches`; nenhum → `FinanceError("formato não reconhecido: <nome>. Formatos: ofx, nubank-checking-csv, nubank-card-csv. Para outro banco, abra uma issue com um extrato anonimizado.")`.

- [ ] Teste: cada fixture detecta o parser certo; arquivo `.txt` qualquer → erro.
- [ ] RED → GREEN → commit `feat: detecção de formato de extrato`.

### Task 5: `rules.yaml`

**Files:** `src/finance/config/rules.py`, `tests/test_rules.py`.

**Interfaces:** `Rule(pattern: str, category: str)`; `load_rules(path, categories) -> list[Rule]` (formato `rules: [{pattern, category}]`, regex compilado case-insensitive, categoria desconhecida → erro); `apply_rules(rules, description) -> str` (primeira que casa; `""` se nenhuma); `append_rule(path, rule) -> None` (lê, acrescenta, grava `yaml.safe_dump(allow_unicode=True, sort_keys=False)`).

- [ ] Teste: ordem importa; case-insensitive; append persiste e recarrega.
- [ ] RED → GREEN → commit `feat: regras de categorização`.

### Task 6: Ação de import (pura)

**Files:** `src/finance/actions/import_statement.py`, `tests/test_action_import.py`.

**Interfaces:** `ImportResult(new: list[Entry], duplicates: int, uncategorized: int)`; `build_import_entries(records, account: Account, source: str, existing_hashes: set[str], rules: list[Rule], ids: Iterator[str]) -> ImportResult` — hash já existente → conta em `duplicates`; senão `Entry(status=CONFIRMED, source=source, import_hash=hash, category=apply_rules(...))`.

- [ ] Teste: 3 registros, 1 duplicado, 1 casa regra, 1 fica sem categoria.
- [ ] RED → GREEN → commit `feat: montagem de lançamentos importados com dedupe e regras`.

### Task 7: `LedgerStore.replace`

**Files:** `src/finance/ledger/store.py`, `tests/test_store.py`.

**Interfaces:** `replace(self, updated: Iterable[Entry], removed_ids: set[str]) -> None` — reescreve cada mês afetado: remove ids, substitui por id (mesmo mês). Entry atualizado com id desconhecido → `FinanceError`.

- [ ] Teste: atualiza categoria de A, remove B, C intacto.
- [ ] RED → GREEN → commit `feat: LedgerStore.replace`.

### Task 8: Ação de conciliação (pura)

**Files:** `src/finance/actions/reconcile.py`, `tests/test_action_reconcile.py`.

**Interfaces:** `Match(manual: Entry, imported: Entry)`; `ReconcileResult(matches: list[Match], unmatched_imported: list[Entry], stale_manual: list[Entry])`; `reconcile(entries, window_days: int, stale_days: int, today: date) -> ReconcileResult` — candidatos: manual (`status=manual`) × importado (`status=confirmed` e `import_hash != ""`), mesmo `account`, mesmo `amount`, mesmo `installment`, `|Δdate| <= window`; greedy pelo menor Δ; cada importado casa no máximo uma vez. `stale_manual` = manuais sem par com `today - date > stale_days`. `merge(match) -> Entry` = manual com `status=CONFIRMED`, `import_hash`, `source` do importado.

- [ ] Teste: casa parcela 1/10 por valor+janela; não casa 2/10; sobra importado; manual velho vira stale.
- [ ] RED → GREEN → commit `feat: conciliação manual × importado`.

### Task 9: Ação de categorização (pura)

**Files:** `src/finance/actions/categorize.py`, `tests/test_action_categorize.py`.

**Interfaces:** `pending(entries, year: int | None, month: int | None) -> list[Entry]` (sem categoria, não-transferência); `set_category(entries, entry_id, category, categories) -> Entry` (id inexistente / categoria desconhecida → erro).

- [ ] RED → GREEN → commit `feat: categorização de pendentes`.

### Task 10: CLI `import`, `reconcile`, `categorize`

**Files:** `src/finance/cli/{import_cmd,reconcile,categorize}.py`, `cli/__init__.py`, `tests/test_cli_import_flow.py`.

- `finance import <arquivo> --account X` → detect, parse, `build_import_entries` (hashes existentes = todos do ledger), `store.append`, imprime `importados: N, duplicados: D, sem categoria: U`.
- `finance reconcile [--window 3] [--stale-days 45] [--json]` → `reconcile`, aplica `store.replace(merged, removed={imported ids})`, imprime `conciliados: N`, lista sobras e stale.
- `finance categorize [--month AAAA-MM] [--json]` lista pendentes (`id, date, account, amount, description`); `finance categorize set <id> <categoria> [--rule "<regex>"]` aplica via `store.replace` e, com `--rule`, `append_rule`.
- Teste end-to-end com fixtures: `add` manual (−35.90 no `nu`, 2026-09-01) → `import sample.ofx --account nu` → `reconcile` casa 1 → `categorize` lista 1 pendente → `categorize set <id> renda/salario --rule "PIX RECEBIDO"` → `rules.yaml` tem a regra; `report month` sem pendentes.
- [ ] RED → GREEN → commit `feat: comandos import, reconcile e categorize`.

### Task 11: Skills

**Files:** `skills/{lancar,importar,categorizar,fechar-mes,saldo}/SKILL.md`. Gate: `superpowers:writing-skills` + `claude-plugin:skill-rules` ANTES de escrever.

Cada skill: frontmatter `name`, `description` (gatilhos em pt-BR), corpo curto: (1) o que perguntar quando faltar dado, (2) o comando exato (`uv run --project "${CLAUDE_PLUGIN_ROOT}" finance …` a partir do diretório do projeto de dados), (3) como apresentar o resultado, (4) o que NUNCA fazer (calcular por conta própria, inventar conta/categoria, editar CSV à mão).

- [ ] Commit `feat: skills lancar, importar, categorizar, fechar-mes e saldo`.

### Task 12: Docs

- [ ] `docs/cli.md` += import/reconcile/categorize; README += skills e "formatos suportados / como pedir um novo". Commit `docs: importação, conciliação e skills`.
