# Parser da fatura do cartão Bradesco (PDF) — issue #3

## O que a amostra real mostra

Três faturas reais (set/out/nov 2026, vencimento sempre dia 20, fechamento
dia 4–6) têm camada de texto: `pypdf` extrai tudo, nenhuma é imagem.

A tabela `Lançamentos` extrai como uma linha por lançamento:

```
DD/MM  <histórico> <cidade> [US$ cotação] <valor>[ -]
```

- O ` -` no fim é crédito (pagamento da fatura, estorno); sem ele, débito.
- A linha quebra em até 3 quando a cidade não cabe na coluna
  (`ANGRA DOS` / `REI`), e a tabela continua depois do rodapé nas páginas
  seguintes. Por isso o parser varre o documento inteiro em vez de
  delimitar a seção `Lançamentos`.
- Parcela vem colada ou separada no histórico (`...EDECO11/12`,
  `MP*LUVIN 10/12`), nunca como a palavra "Parcela".
- A linha não tem ano. Toda compra é anterior ao fechamento, então
  dia/mês depois do vencimento é do ano anterior (parcela antiga).

Validação da gramática contra as três faturas: a soma assinada dos
lançamentos deu exatamente `-"Total da fatura em real" + pagamento` nas
três — nenhuma linha perdida, nenhuma linha de texto capturada à toa.

## Entrega

1. `pypdf` como dependência do projeto (nada instalado fora dele).
2. `finance/imports/pdf_text.py` — único lugar que conhece o `pypdf`.
3. `finance/imports/bradesco_card_pdf.py` — `matches` (`.pdf` + `%PDF` +
   marcadores do Bradesco), `parse` e a gramática pura texto → registros.
   Sinal igual ao cartão Nubank: compra negativa, pagamento positivo.
   Valor por `parse_amount`. Parcela vai pra descrição como
   `- Parcela N/M`, igual ao Nubank.
4. Registro em `imports/registry.py` (não conflita: CSV casa por header,
   OFX por extensão/marcador).
5. `examples/data/accounts.yaml`: `bra-card` com fechamento 5 e
   vencimento 20, lidos nas próprias faturas.
6. Fixture anonimizada `tests/fixtures/bradesco_card.pdf` — PDF mínimo
   gerado com o layout real, sem nome, cartão ou valor reais.
7. `docs/cli.md` e `docs/roadmap.md` no mesmo commit.

## Fora de escopo

Extrato da conta Bradesco (CSV/OFX): sem amostra, segue bloqueado.
