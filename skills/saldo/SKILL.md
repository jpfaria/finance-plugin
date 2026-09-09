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
```

## Como apresentar

Responda a pergunta que ele fez, em uma ou duas linhas. Perguntou o saldo da conta → o saldo da conta. Perguntou da fatura → o valor e o mês. Só liste tudo se ele pediu tudo.

O saldo sai do que está lançado. Se o extrato do mês ainda não foi importado, avise em uma linha: o número está incompleto.

## Nunca

- Dizer se ele "pode" gastar algo. Dê o saldo e a fatura aberta; a decisão é dele.
- Estimar saldo futuro — previsão ainda não existe nesta versão.
- Somar valores na mão a partir dos CSV.
