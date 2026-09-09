---
name: importar
description: Use quando o usuário apontar um extrato ou fatura baixada do banco — arquivo .ofx ou .csv do Nubank/banco, "baixei o extrato", "chegou a fatura", "importa esse arquivo" — para carregar no controle financeiro.
---

# Importar

Importa um extrato, concilia com o que já foi lançado à mão e resolve as pendências. Três comandos, nesta ordem.

## Fluxo

Rode a partir do diretório do projeto de dados do usuário:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance import <arquivo> --account <conta>
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance reconcile
uv run --project "${CLAUDE_PLUGIN_ROOT}" finance categorize
```

1. **import** — detecta o formato, ignora o que já foi importado antes (dedupe por hash) e aplica `rules.yaml`. Reimportar o mesmo arquivo é seguro: vira "duplicados".
2. **reconcile** — casa o que o usuário já tinha lançado à mão com a linha do extrato. Ele relata importados sem par e manuais antigos sem par; mostre essas sobras ao usuário, são o sinal de que algo está errado.
3. **categorize** — o que sobrou sem categoria. Siga a skill `categorizar`.

## Antes de importar

- **Confirme o arquivo e a conta em uma linha** antes de rodar: `import` grava direto, não tem `--dry-run`. "Importo `fatura-set.csv` na conta `nu-card`?"
- **Só importe arquivo que o usuário apontou como extrato dele.** Fixture de teste, arquivo de exemplo do repositório do plugin ou arquivo achado por conta própria em `~/Downloads`: não importe, pergunte.
- **Formatos suportados:** OFX (qualquer banco), CSV de conta do Nubank, CSV de cartão do Nubank. Outro formato → a CLI falha com "formato não reconhecido"; repasse a mensagem e ofereça abrir uma issue com um extrato anonimizado. Nunca tente parsear o arquivo você mesmo.

## Depois

Relate em até três linhas: quantos importados, quantos duplicados, quantos conciliados, e o que ficou pendente de categoria. Depois trate os pendentes.

## Nunca

- Converter, recortar ou "arrumar" o arquivo antes de importar.
- Escrever no ledger sem passar pela CLI.
- Importar um extrato que você mesmo escolheu.
