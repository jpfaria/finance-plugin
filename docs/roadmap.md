# Roadmap

O que existe hoje e o que vem depois. Escopo entregue está na spec (`docs/superpowers/specs/`).

## Entregue

- CLI: `add` (com parcelas), `import`, `reconcile`, `categorize`, `recategorize`, `rebuild`, `report month|budget|balance|invoice`.
- Origem da categoria (`category_source`): regra nova pega lançamento antigo sem reimportar, e `recategorize --force` nunca encosta em categoria posta à mão.
- Extratos: OFX (qualquer banco), CSV de conta e de cartão do Nubank, conta do Bradesco em PDF (com o nome do favorecido) ou CSV, PDF da fatura do cartão Bradesco.
- Grupos de conta livres (`group:` em `accounts.yaml`), `--group` nos relatórios, orçamento geral + por grupo.
- Skills: `lancar`, `importar`, `categorizar`, `fechar-mes`, `saldo`.

## Próximo

1. **Projetos com rateio** ([#6](https://github.com/jpfaria/finance-plugin/issues/6)).
   Separar obra, barco e imóvel de temporada do gasto pessoal: projeto como tag,
   rateio em `data/projects.yaml`, acerto por participante e
   `finance report project`. Dinheiro que volta de rateio é devolução, não
   receita. Desenho em `docs/projetos-rateio/README.md`; o nome do favorecido
   que a regra vai casar já vem do extrato em PDF
   ([#5](https://github.com/jpfaria/finance-plugin/issues/5)).
2. **Bot do Telegram.** Lançar e consultar por mensagem, sem abrir o Claude Code. O bot chama o mesmo CLI que as skills — nenhuma regra de negócio nova. A decidir: onde roda, como autentica (restringir ao chat id do dono) e como faz commit/push do `data/` depois de cada escrita.
3. **Relatórios bonitos com previsão.** Saída visual além da tabela, e projeção: parcelas futuras já lançadas, faturas a vencer, renda recorrente. Hoje o relatório só olha pra trás.
4. **Renda fixa vs variável.** As categorias já existem (`salario`, `freelance`, `aluguel-recebido`, `venda`); falta o relatório que separa o que é previsível do que não é.

## Depois

Investimentos e patrimônio, multi-moeda, interface própria, servidor MCP, importação automática pela API dos bancos.
