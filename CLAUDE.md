# finance-plugin — Claude Code

Plugin Claude Code de controle financeiro pessoal. Spec: `docs/superpowers/specs/2026-09-09-finance-v1-design.md`.

## Regras

- **Nada pessoal aqui.** Este repo é público e vira plugin: nenhum nome de conta, valor, extrato ou preferência de uma pessoa. Dados do usuário moram no repo privado dele (`data/`), lidos via `FINANCE_DATA_DIR`. Exemplos são fictícios, em `examples/data/`.
- **Idioma:** código em inglês; docs, mensagens ao usuário, skills, commits e issues em pt-BR.
- **Disciplina de código:** skill `dev` do `claude-plugin@xgodev` (TDD red-first, um módulo = uma responsabilidade). Sem exceção.
- **Regra de negócio só no CLI (`src/finance/`), nunca na skill.** Skill sabe qual comando rodar e como conversar.
- **`data/` do usuário é o canônico.** `.cache/` e `imports/` são descartáveis e gitignorados. Nunca commitar extrato, nem de exemplo.
- **Dinheiro é `Decimal`** com 2 casas. Negativo = saída, positivo = entrada.
- Antes de commitar: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q`.

## Layout

`src/finance/{model,config,ledger,actions,cache,reports,render,cli}` — ver `docs/superpowers/plans/`.
