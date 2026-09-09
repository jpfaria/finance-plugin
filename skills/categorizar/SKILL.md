---
name: categorizar
description: Use quando houver lançamentos sem categoria no controle financeiro — depois de importar um extrato, quando o usuário perguntar "o que falta categorizar", ou quando um relatório mostrar "sem categoria" maior que zero.
---

# Categorizar

Resolve os lançamentos sem categoria, um a um, com o usuário aprovando.

## Comandos

Rode a partir do diretório do projeto de dados do usuário:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance categorize [--month AAAA-MM] [--json]
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance categorize set <id> <grupo/item> [--rule "<regex>"]
```

## Como conduzir

1. Liste os pendentes. Leia `data/categories.yaml` para saber quais categorias existem.
2. Para cada pendente, **proponha uma categoria e espere o ok**. Uma linha por item: descrição, valor, categoria sugerida. Vários itens parecidos podem ir numa proposta só.
3. Aplique com `categorize set`.
4. **`--rule` só quando o padrão vai se repetir** (nome de estabelecimento que aparece todo mês). A regex casa a descrição, sem diferenciar maiúscula. Compra única não vira regra — `rules.yaml` cheio de regra morta categoriza errado depois.

## Nunca

- Aplicar categoria sem o usuário confirmar.
- Usar um caminho que não está em `categories.yaml`. Falta categoria? Proponha adicionar ao arquivo e espere o ok.
- Editar `rules.yaml` ou o CSV na mão — use `categorize set --rule`.
