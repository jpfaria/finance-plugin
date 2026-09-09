# Roadmap

O que existe hoje e o que vem depois. Escopo entregue está na spec (`docs/superpowers/specs/`).

## Entregue

- CLI: `add` (com parcelas), `import`, `reconcile`, `categorize`, `rebuild`, `report month|budget|balance|invoice`.
- Extratos: OFX (qualquer banco), CSV de conta e de cartão do Nubank.
- Grupos de conta livres (`group:` em `accounts.yaml`), `--group` nos relatórios, orçamento geral + por grupo.
- Skills: `lancar`, `importar`, `categorizar`, `fechar-mes`, `saldo`.

## Próximo

1. **Bot do Telegram.** Lançar e consultar por mensagem, sem abrir o Claude Code. O bot chama o mesmo CLI que as skills — nenhuma regra de negócio nova. A decidir: onde roda, como autentica (restringir ao chat id do dono) e como faz commit/push do `data/` depois de cada escrita.
2. **Relatórios bonitos com previsão.** Saída visual além da tabela, e projeção: parcelas futuras já lançadas, faturas a vencer, renda recorrente. Hoje o relatório só olha pra trás.
3. **Renda fixa vs variável.** As categorias já existem (`salario`, `freelance`, `aluguel-recebido`, `venda`); falta o relatório que separa o que é previsível do que não é.
4. **Extratos do Bradesco** (CSV e PDF). Bloqueado: falta uma amostra anonimizada para escrever o parser.

## Depois

Investimentos e patrimônio, multi-moeda, interface própria, servidor MCP, importação automática pela API dos bancos.
