---
name: saldo
description: Use quando o usuário perguntar quanto tem ou quanto deve — "quanto tenho na conta", "qual meu saldo", "quanto vem de fatura", "quanto devo no cartão", "posso gastar X".
---

# Saldo

Saldo de cada conta e fatura aberta de cada cartão.

## Comando

Rode a partir do diretório do projeto de dados do usuário:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance report balance
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance report cash [--month AAAA-MM]
```

`report cash` é o caixa do mês: saldo no 1º dia, o que entrou, o que saiu e o saldo final de cada conta. Use quando a pergunta for sobre o mês ("entrei no mês com quanto", "pra onde foi o dinheiro"), não só sobre agora.

## Como apresentar

Responda a pergunta que ele fez, em uma ou duas linhas. Perguntou o saldo da conta → o saldo da conta. Perguntou da fatura → o valor e o mês. Só liste tudo se ele pediu tudo.

O saldo sai do que está lançado. Se o extrato do mês ainda não foi importado, avise em uma linha: o número está incompleto.

**Olhe a coluna `fonte` do `report balance` antes de falar um número.** `banco` = a conta tem `opening_balance` em `accounts.yaml` e o saldo é o do banco. `só movimento` = é apenas a soma do que foi importado, e **não** é o saldo da conta: diga isso com todas as letras e ofereça gravar o saldo inicial (o saldo do extrato na véspera do primeiro lançamento importado).

## Nunca

- Dizer se ele "pode" gastar algo. Dê o saldo e a fatura aberta; a decisão é dele.
- Chamar de "saldo" o que a coluna `fonte` marca como `só movimento`.
- Estimar saldo futuro de cabeça — pra isso existe a skill `prever`.
- Somar valores na mão a partir dos CSV.
