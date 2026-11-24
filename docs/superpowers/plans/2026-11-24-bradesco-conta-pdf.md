# Parser do extrato de conta do Bradesco (PDF) — issue #5

## O que a amostra real mostra

Extrato do app (Bradesco Celular → Extrato → exportar), 9 folhas, período de
28/09 a 23/11/2026, 139 lançamentos — o mesmo período que o CSV já tinha
importado. Tem camada de texto: o `pypdf` extrai tudo.

Cada lançamento ocupa **duas linhas**:

```
28/09/2026  PIX RECEBIDO              1003007        69,26                 3.606,11
            REM: LIVELO S.A. 28/09
            PIX ENVIADO               1141396                     187,61   3.793,72
            DES: POSTO MARINA VEROLME 27/09
```

- `REM:` é remetente (entrada), `DES:` é destinatário (saída); o nome vem
  truncado em 21 caracteres, seguido do dia/mês da operação. É exatamente o que
  o CSV não tem: lá o histórico é só `PIX ENVIADO` / `PIX RECEBIDO`.
- A data só aparece na primeira transação do dia; as seguintes herdam.
- O cabeçalho (`Bradesco Celular`, `Nome:`, `Folha: N/9`, linha de colunas) se
  repete a cada folha, e **toda** folha tem a linha de colunas.
- A última folha fecha com `Total <créditos> <débitos> <saldo>`.
- `Docto.` tem 7 dígitos e é o que distingue dois lançamentos iguais no mesmo
  dia — vai pra `external_id`, igual ao CSV.
- Lançamento que não é PIX pode ter segunda linha (`CONTA DE LUZ` →
  `ENEL DISTRIB. RJ-00063333060`) ou não ter nenhuma (`GASTOS CARTAO DE
  CREDITO`, `LIB EMPRESTIM/FINANCIAM`).

### O sinal só existe na posição horizontal

`Crédito (R$)` e `Débito (R$)` são colunas diferentes com o mesmo formato de
número. No texto plano (`extract_text`) as colunas colapsam em espaços e
`187,61` fica indistinguível de `69,26` — não dá pra saber entrada de saída. O
saldo também não resolve: o PDF imprime saldo negativo **sem sinal** (a conta
ficou negativa em outubro e o extrato mostra `39,38` onde o saldo era −39,38).

Daí a decisão: ler o texto **com layout** (`extract_layout_pages`, novo em
`imports/pdf_text.py`) e classificar cada valor pela coluna onde ele termina,
usando as legendas do cabeçalho de cada folha como régua. As folhas não têm a
mesma largura de coluna (o fim de `Crédito (R$)` varia de 115 a 122 entre as 9
folhas), por isso a régua é lida por folha, não uma vez só.

### Validação da gramática

Com o sinal vindo da coluna, a cadeia de saldo do extrato real fecha **linha a
linha** nos 139 lançamentos (em módulo, já que o sinal do saldo não é impresso),
e a soma dos créditos e a dos débitos batem com a linha `Total`
(110.262,60 / 110.252,74). Nenhuma linha perdida, nenhuma linha de texto
capturada à toa.

## Entrega

1. `finance/imports/pdf_text.py` — `extract_layout_pages`, único lugar que
   conhece o `pypdf`.
2. `finance/imports/bradesco_checking_pdf.py` — `matches` (`.pdf` + `%PDF` +
   `Bradesco` + `Docto.` + as legendas das colunas, que a fatura do cartão da #3
   não tem) e a gramática pura `páginas → registros`. Descrição
   `PIX ENVIADO — <nome>`; sem `DES:`/`REM:`, o histórico vai cru.
3. Conferência do `Total`: se as somas não batem, `FinanceError` em vez de
   importar faltando lançamento.
4. Registro em `imports/registry.py`.
5. Fixture anonimizada `tests/fixtures/bradesco_checking.pdf` — duas folhas com
   o layout real (cabeçalho repetido, data herdada, as duas colunas, linha de
   total), nomes e valores fictícios.

## Reimportação: o PDF substitui o CSV

O mesmo período já estava no ledger, importado do CSV. O `import_hash` sai de
`conta|data|valor|descrição|docto` (`imports/record.py`), e a descrição é
justamente o que muda (`PIX ENVIADO` → `PIX ENVIADO — POSTO MARINA VEROLME`):
reimportar o PDF em cima do CSV **duplica os 139 lançamentos**. `finance
reconcile` não ajuda — ele casa manual com importado, não importado com
importado.

Decisão: **para a conta do Bradesco, o PDF é o formato canônico**; o CSV
continua suportado (arquivo antigo, outro banco não muda). Não existe
reconciliação automática entre os dois, e não vale escrever uma: o caminho é
apagar o que veio do CSV e reimportar o PDF. Está em `docs/cli.md`, na seção
"Trocar o CSV pelo PDF na conta do Bradesco".

O que se perde ao apagar: categoria posta à mão (`category_source=manual`) nos
lançamentos daquele período. Categoria de regra volta sozinha no `import`.
