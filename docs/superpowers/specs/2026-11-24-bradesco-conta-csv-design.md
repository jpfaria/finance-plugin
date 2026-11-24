# Parser do extrato de conta do Bradesco (CSV) — desenho

Issue: [#2](https://github.com/jpfaria/finance-plugin/issues/2).

## Intenção

Importar o CSV de extrato de **conta** do Bradesco com `finance import`, como já
se faz com OFX e com os CSV do Nubank. O roadmap listava o Bradesco como
bloqueado por falta de amostra; a amostra real existe na máquina do dono e nunca
entra neste repo.

## Metas

- Crédito vira valor positivo, débito vira negativo.
- Preâmbulo e rodapé nunca viram lançamento.
- Reimportar o mesmo extrato não duplica, e dois lançamentos reais que só o
  `Docto.` distingue continuam sendo dois.

## Não-metas

- PDF do Bradesco (segue bloqueado: nenhuma amostra).
- Extrato de cartão do Bradesco.
- Usar a coluna `Saldo (R$)` para conferência de saldo.

## O que a amostra real mostra (evidência, não suposição)

- Codificação **UTF-8 com BOM** (`efbbbf` nos três primeiros bytes), não
  latin-1. Separador `;`.
- Linha 1 é preâmbulo (`Extrato de: Ag: ... | Conta: ...;;;;;`); o cabeçalho
  `Data;Histórico;Docto.;Crédito (R$);Débito (R$);Saldo (R$)` está na linha 2.
- Data `DD/MM/AAAA`; valores em notação brasileira (`1.234,56`).
- Crédito e débito em colunas separadas; a que não se aplica vem com **um
  espaço**, não vazia.
- O bloco de lançamentos termina na primeira linha toda vazia (`;;;;;`). Depois
  dela: a frase da data-base, o bloco "Lançamentos periódicos" com outro
  cabeçalho e a linha de total.
- `Docto.` **não é único**: repete na mesma data, inclusive com valores
  diferentes (139 linhas, 9 doctos repetidos). Mas em 3 pares de lançamentos ele
  é a única coisa que os distingue (mesma data, mesmo histórico, mesmo valor).

## Abordagens

1. **`csv.reader` com delimitador `;`, achando o cabeçalho e parando na primeira
   linha vazia** — escolhida. Lê o layout como ele é, sem depender de posição
   fixa de linha, e o fim do bloco é um fato do arquivo.
2. `csv.DictReader` como os parsers do Nubank — descartada: o arquivo tem duas
   linhas de cabeçalho (`Data;...` aparece de novo no rodapé) e um preâmbulo
   antes do cabeçalho; `DictReader` leria o preâmbulo como nomes de coluna.
3. Filtrar linha por linha pelo formato da data e ignorar o resto — descartada:
   ignorar em silêncio qualquer linha que não casa esconde um layout novo
   (LAW 4). Parar no fim declarado do bloco e **falhar alto** dentro dele é o
   oposto disso.

## Decisões

- `external_id = Docto.` — não é único no extrato, mas é o que distingue dois
  lançamentos de mesma data, histórico e valor. O dedupe por ocorrência (issue
  #1) já deixa as duas linhas entrarem; com o `Docto.` a identidade de cada uma
  não depende da posição dela no arquivo.
- `matches` procura a linha de cabeçalho entre as primeiras linhas do arquivo
  (os parsers do Nubank comparam a linha 1, que aqui é o preâmbulo). Nenhum
  conflito: os cabeçalhos do Nubank são separados por vírgula.
- Dentro do bloco de lançamentos, linha inesperada é erro alto (`FinanceError`):
  crédito e débito preenchidos ao mesmo tempo, nenhum dos dois, data inválida.
- Valor sempre por `finance.model.money.parse_amount`, a única parte que conhece
  a notação brasileira.
