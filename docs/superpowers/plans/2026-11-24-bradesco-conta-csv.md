# Parser do extrato de conta do Bradesco (CSV) — plano

**Spec:** `docs/superpowers/specs/2026-11-24-bradesco-conta-csv-design.md`.
**Objetivo:** `finance import` aceita o CSV de extrato de conta do Bradesco.
**Entrega única:** todos os testes primeiro (RED), depois a implementação, um
commit no fim.

## Arquivos

- Criar `tests/fixtures/bradesco_checking.csv` — fixture **anonimizado**
  (agência/conta fictícias, valores fictícios) com preâmbulo, crédito, débito,
  valor com milhar, dois lançamentos que só o `Docto.` distingue e o rodapé
  inteiro.
- Criar `tests/test_import_bradesco.py`.
- Criar `src/finance/imports/bradesco_checking_csv.py` —
  `class BradescoCheckingCsv` com `name = "bradesco-checking-csv"`,
  `matches(path, head) -> bool`, `parse(path) -> list[ImportedRecord]`.
- Modificar `src/finance/imports/registry.py` — somar `BradescoCheckingCsv()` a
  `PARSERS`.
- Modificar `tests/test_import_registry.py` — fixture do Bradesco na
  parametrização.
- Modificar `docs/cli.md`, `docs/roadmap.md`, `README.md`,
  `skills/importar/SKILL.md` — formatos suportados, no mesmo commit (LAW 2).

## Testes (RED antes de qualquer linha de produção)

1. `matches` casa com o cabeçalho na linha 2 e **não** casa com os cabeçalhos do
   Nubank; `detect()` do registry devolve `bradesco-checking-csv` para a fixture
   e continua devolvendo os parsers do Nubank para as fixtures deles.
2. `parse` da fixture devolve exatamente os lançamentos do bloco (crédito
   positivo, débito negativo, `1.234,56` → `Decimal("1234.56")`, `external_id` =
   `Docto.`) — nenhuma linha do rodapé entra.
3. Os dois lançamentos que só o `Docto.` distingue têm `record_hash` diferente.
4. Caminhos de erro (`FinanceError`): crédito e débito preenchidos juntos,
   nenhum dos dois, data inválida, arquivo sem a linha de cabeçalho.

## Implementação

- `csv.reader(fh, delimiter=";")` com `encoding="utf-8-sig"`; achar a linha de
  cabeçalho, mapear nome de coluna → índice a partir dela, parar na primeira
  linha toda vazia.
- Valor por `parse_amount`; crédito positivo, débito negado.

## Pronto quando

`uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q`
verde, o extrato real importa limpo, merge em `main`, push, issue #2 fechada.
