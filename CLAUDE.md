# finance-plugin — Claude Code

Plugin Claude Code de controle financeiro pessoal. Spec: `docs/superpowers/specs/2026-09-09-finance-v1-design.md`.

## Regras

- **Nada pessoal aqui.** Este repo é público e vira plugin: nenhum nome de conta, valor, extrato ou preferência de uma pessoa. Dados do usuário moram no repo privado dele (`data/`), lidos via `FINANCE_DATA_DIR`. Exemplos são fictícios, em `examples/data/`.
- **Idioma:** código em inglês; docs, mensagens ao usuário, skills, commits e issues em pt-BR.
- **Sem gates de desenvolvimento.** Repo pessoal: os hooks de dev-rules do `claude-plugin@xgodev` estão desligados por `.dev-rules/.off` (não versionado — recriar com `touch .dev-rules/.off` em clone novo). Nenhuma sessão reativa e nenhuma pergunta sobre isso: nada de RED-first obrigatório, modo FEATURE, brainstorm/plano formal ou guarda de commit/branch. A skill `dev` vale como referência de bom senso (um módulo = uma responsabilidade, teste junto com o código), nunca como trava.
- **Regra de negócio só no CLI (`src/finance/`), nunca na skill.** Skill sabe qual comando rodar e como conversar.
- **`data/` do usuário é o canônico.** `.cache/` e `imports/` são descartáveis e gitignorados. Nunca commitar extrato, nem de exemplo.
- **Dinheiro é `Decimal`** com 2 casas. Negativo = saída, positivo = entrada.
- **`.gitignore` ancorado na raiz** (`/imports/`, `/.cache/`). `imports/` sem a barra casa com diretório de qualquer nível e ignorava o pacote `src/finance/imports/`. Não "simplificar".
- **Parser de extrato só com amostra real anonimizada.** Layout inventado quebra dado real em silêncio. O CSV da conta e o PDF da fatura do cartão do Bradesco saíram de extratos reais; as fixtures do repo são cópias anonimizadas com o mesmo layout (ver `docs/roadmap.md`).
- **Número que eu afirmo sai de um comando, não da cabeça.** Toda soma, total, agrupamento ou comparação dita ao usuário vem do CLI (`finance report …`) ou de uma consulta ao CSV — nunca de somar linhas do relatório de cabeça, e nunca de comentário extra do tipo "X somou tanto" ou "sem contar Y". Agrupamento que o relatório não imprime: rode outra consulta antes de falar. Não rodou, não fala. **Why:** (2026-11-27) juntei categorias do relatório por conta própria e afirmei que faltava um item que nem caía naquele mês — "vc nao pode deduzir sem ter certeza.. pq vc vai errar as contas todas".
- Antes de commitar: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q`.

## Layout

`src/finance/{model,config,ledger,actions,cache,reports,render,cli}` — ver `docs/superpowers/plans/`.
