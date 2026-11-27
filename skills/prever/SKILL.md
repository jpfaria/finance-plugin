---
name: prever
description: Use quando o usuário quiser previsão de gasto no controle financeiro — "quanto vou gastar no mês que vem", "previsão de fevereiro", "quanto eu gasto por mês em cada categoria", "qual meu gasto fixo", "o que se repete todo mês".
---

# Prever

O que cada categoria costuma custar por mês, a partir dos meses já fechados.

## Comandos

Rode a partir do diretório do projeto de dados do usuário:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance report forecast --month AAAA-MM
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance report forecast --month AAAA-MM --from AAAA-MM --to AAAA-MM
```

## Como conduzir

1. **Escolha a base antes de rodar.** Mês incompleto na base puxa toda a média pra baixo sem avisar. Confira a primeira data de cada conta (`finance report balance`, ou a primeira linha do CSV do mês em `data/ledger/`) e, se a conta principal só entrou no meio de um mês, corte esse mês com `--from`.
2. Rode o comando. A saída já vem em duas tabelas: **Todo mês** (apareceu em todos os meses da base) e **Eventual**.
3. Apresente primeiro **Todo mês**, maior primeiro — é o gasto que ele vai ter de novo. "Eventual" é estimativa fraca: diga isso.
4. Diga quais meses formaram a base e quantos são. Base de dois meses é uma média de dois números, não uma tendência.

## Nunca

- Somar, dividir ou projetar categoria por fora da CLI. Todo número da previsão sai do `report forecast`.
- Tratar a previsão como sazonal: ela repete a média da base. Décimo terceiro, IPVA, IPTU, matrícula e Natal **não** aparecem se não estiverem nos meses da base — avise quando o mês previsto for um desses.
- Esconder a linha `(sem categoria)`. Ela é gasto real; se estiver grande, chame a skill `categorizar` antes de falar de previsão.
