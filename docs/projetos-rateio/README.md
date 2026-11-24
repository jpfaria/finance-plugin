# Projetos com rateio — desenho

Issue: [#6](https://github.com/jpfaria/finance-plugin/issues/6). Depende da
[#5](https://github.com/jpfaria/finance-plugin/issues/5) para o preenchimento
automático (sem o nome do favorecido no extrato, nenhuma regra identifica quem
pagou o PIX).

## Intenção

Separar, dentro das mesmas contas, o que é gasto pessoal do que é gasto de um
**projeto**: uma frente de despesa com vida própria, que ou é rateada com outras
pessoas (uma obra, um barco) ou tem receita e despesa próprias (um imóvel de
temporada). Hoje tudo isso cai junto no `report month` e o relatório mensal
mente nas duas direções: a despesa aparece inteira mesmo quando dois terços
voltam, e o dinheiro que volta aparece como receita.

## Metas

- Um lançamento entra num projeto por regra (`rules.yaml`) ou à mão, e isso fica
  gravado em `data/ledger/` — nada derivado só do cache.
- O rateio é declarado em um arquivo do repo privado, não no código.
- `finance report project <id>` responde "quem ainda me deve quanto".
- Dinheiro que volta de rateio **nunca** entra em "receitas" do `report month`,
  pelo mesmo motivo que pagamento de fatura não entra em "despesas".
- O `report month` não esconde o dinheiro que tirou de vista: imprime quanto
  ficou fora e por qual projeto.

## Não-metas

- Ler as reservas do `jpfaria/lardocemar` (decisão 5 abaixo).
- Nova skill. Este issue entrega CLI; a conversa pode vir depois.
- Rateio com data de vencimento, juros, cobrança ou histórico de acertos
  parciais com saldo congelado. O saldo é sempre calculado do ledger.
- Projeto dentro de projeto, ou lançamento em dois projetos (é erro).

## Decisões

### 1. Como um lançamento entra num projeto: tag, pelos dois caminhos

Projeto **é uma tag** de `Entry.tags`. Nenhuma coluna nova: `tags` já existe,
já faz round-trip no CSV e já sai no cache. O que faltava era (a) quem escreve e
(b) quem sabe que aquela tag é um projeto.

Quem sabe é o `data/projects.yaml`: a tag é projeto quando um projeto declara
aquele `id`. Tag que ninguém declara continua sendo tag livre, sem efeito nenhum
em relatório — não existe "projeto implícito".

Quem escreve, nos dois caminhos:

- **Regra.** `rules.yaml` passa a aceitar `tags:` junto de `category:`, e as
  duas chaves ficam opcionais (hoje `category` é obrigatória). Uma regra pode
  marcar só a tag, só a categoria, ou as duas. `apply_rules` passa a devolver
  categoria + tags em vez de uma string.
- **À mão.** `finance tag` marca (e desmarca) o que já está gravado, igual ao
  `categorize set` faz com categoria, com o mesmo `--rule` para já deixar a
  regra escrita.

Tag vinda de regra é **sempre aditiva**: `recategorize` (que é o comando de
"reaplica `rules.yaml` no que já está gravado") passa a aplicar também as tags,
e nunca remove uma. Por isso **não existe** `tag_source` espelhando o
`category_source`: sem remoção não há o que proteger. O preço disso é conhecido
e aceito: tag que uma regra errada pôs, removida à mão, volta na próxima
reaplicação — o certo é corrigir a regra, não o lançamento.

Um lançamento com **duas** tags de projeto é erro, levantado ao carregar o
projeto, nomeando o id do lançamento. É uma situação que só aparece editando o
CSV à mão, e falhar alto é melhor que contar o mesmo real em dois projetos.

### 2. Onde o rateio é declarado: `data/projects.yaml`, no repo privado

Participante de rateio é pessoa física com nome; isso vive no repo privado, como
`accounts.yaml`. Aqui só entra o exemplo fictício, em `examples/data/`.

```yaml
projects:
  - id: obra
    name: Obra
    owner: dono
    rateio:
      exemplo-a: 50     # percentuais; precisam somar 100
      dono: 25
      exemplo-b: 25

  - id: barco
    name: Barco
    owner: dono
    rateio:
      participantes: [dono, exemplo-a, exemplo-b]   # divisão igual

  - id: angra
    name: Angra
    # sem rateio: receita e despesa são do dono
```

- `rateio` ausente → projeto **sem rateio** (caso Angra). É o que decide o
  comportamento no `report month` (decisão 4); não existe campo `kind`.
- `owner` é quem paga pela conta acompanhada; default `dono`. Tem de aparecer no
  rateio quando o rateio existe — quem paga também tem cota.
- As duas formas de divisão são a mesma coisa internamente: `participantes: [...]`
  virá um mapa de percentuais iguais. Percentual que não soma 100 é erro.
- Centavo de arredondamento sobra para o `owner`, igual ao
  `split_installments` já faz com a última parcela.

### 3. Como o acerto aparece: devido − devolvido, sempre calculado do ledger

Dentro de um projeto com rateio, o sinal do lançamento diz o papel:

| sinal | o que é | entra no acerto como |
|---|---|---|
| negativo | gasto do projeto (pagamento ao prestador, combustível) | aumenta o total a ratear |
| positivo | **devolução** de um participante | abate o que aquele participante devia |

A devolução precisa dizer **de quem** veio, e isso não se adivinha da descrição:
o lançamento carrega uma segunda tag `de:<participante>` (`de:exemplo-a`).
Com a #5 na mão, uma regra faz isso sozinha — pattern no nome do pagador, `tags:
[obra, "de:exemplo-a"]`. Antes dela, é `finance tag ... --from exemplo-a`.

Com isso:

```
gasto        = Σ |lançamentos negativos do projeto|
devido[p]    = cota[p] × gasto                (centavo residual no owner)
devolvido[p] = Σ lançamentos positivos com de:p
saldo[p]     = devido[p] − devolvido[p]       (> 0: ainda deve)
```

Devolução **sem** `de:` não é descartada em silêncio: entra como
`(sem participante)` na saída, com contagem própria, para ser corrigida. Pelo
mesmo motivo, nenhum acerto é gravado em arquivo: o saldo é sempre recalculado
do ledger, então corrigir uma tag conserta o acerto na hora.

A cota do próprio `owner` é o número que interessa para o bolso dele: é o custo
real que a obra teve, enquanto os outros 75% são caixa de passagem.

### 4. `report month`: projeto com rateio sai, projeto sem rateio fica

O ponto crítico da issue. Hoje o `month_summary` já tem exatamente este
mecanismo para fatura de cartão: filtra `transfer_group = ''` e as duas pernas da
transferência desaparecem de receita e despesa. Rateio não pode usar
`transfer_group` — a outra perna está na conta de outra pessoa, não existe para
nós.

Decisão: **lançamento de projeto com rateio fica fora do `report month` por
default**, pelos dois lados. Nem o pagamento inteiro ao prestador como despesa
pessoal, nem a devolução como receita. Com um total visível no resumo
(`projetos (fora)`, por projeto), para que a exclusão nunca seja silenciosa.

Por que fora inteiro, e não "só a minha cota dentro das categorias": a cota é
número derivado (percentual × total), e enfiá-la numa linha de categoria faria o
relatório deixar de bater com o ledger — não dá mais para somar as linhas e
achar o que saiu da conta. A cota tem lugar próprio, o `report project`, onde ela
é explicada. O mesmo caminho da fatura de cartão: o movimento sai do fluxo e o
que sobra é olhado no relatório daquele objeto.

Projeto **sem** rateio (Angra) continua **dentro** do `report month`: ali a
receita de reserva é receita de verdade e a despesa é despesa de verdade; não há
nada de terceiro passando pela conta. O que ele ganha é a visão agrupada no
`report project`.

Flags: `--with-projects` traz tudo bruto para dentro (conferência contra o
extrato) e `--project <id>` olha o mês de um projeto só.

### 5. Angra: lançamento normal da conta, sem acoplar o `lardocemar`

A evidência do outro repo: cada reserva em `data/bookings/AAAA/*.yaml` tem
`canal`, `status`, `checkin`, `checkout`, `noites`, `hospedes`, `hospede.nome` e
`financeiro` com `bruto`, `comissao`, `limpeza`, `liquido`, `moeda`.

O que **não** tem: data de pagamento, conta que recebeu e forma de recebimento.
Uma reserva é um compromisso, não um movimento de caixa — ela é lançada meses
antes, pode ser cancelada depois (`status`) e o dinheiro cai numa data e numa
conta que só o extrato sabe. Importar reserva como lançamento criaria receita que
nunca entrou, e obrigaria este repo a conciliar reserva × depósito e a seguir o
schema de outro projeto.

Decisão: a receita de Angra entra como lançamento normal da conta onde o dinheiro
caiu — pelo `finance import` do extrato, ou `finance add` — com a tag `angra` e
categoria `renda/aluguel-recebido`. As despesas (empregada, luz, manutenção) já
entram pelo extrato; ganham a tag `angra` por regra.

Conciliar `bruto/comissao/liquido` da reserva contra o que caiu na conta é
relatório útil, mas é outro issue e, se vier, mora no `lardocemar`, que é quem
conhece reserva.

## Comandos

| Comando | Faz |
|---|---|
| `finance project list [--json]` | Projetos declarados, com cotas e se têm rateio. |
| `finance tag <id> <tag> [--from <participante>] [--rule "<regex>"]` | Marca um lançamento gravado. `--from` grava também `de:<participante>`. `--rule` escreve a regra em `rules.yaml`. |
| `finance tag clear <id> <tag>` | Remove a tag daquele lançamento. |
| `finance report project <id> [--month AAAA-MM] [--json]` | Com rateio: gasto, devolvido, e por participante cota/devido/devolvido/saldo. Sem rateio: receita, despesa, resultado e linhas por categoria. |
| `finance report month [--with-projects] [--project <id>]` | Como hoje, mais a linha `projetos (fora)` e as duas flags. |
| `finance recategorize` | Passa a aplicar também as `tags:` das regras, aditivamente. |

Erro de id de projeto desconhecido lista os declarados, no formato que
`resolve_group` já usa para grupo de conta.

## Modelo e arquivos

| Onde | O quê |
|---|---|
| `src/finance/model/project.py` | `Project` (`id`, `name`, `owner`, `shares: dict[str, Decimal]`), `has_rateio`, `share_of(total)` com o centavo residual no owner. |
| `src/finance/config/projects.py` | `load_projects(path)` → `dict[str, Project]`; valida soma 100, owner na cota, id duplicado. Arquivo ausente = nenhum projeto (feature opcional). |
| `src/finance/config/rules.py` | `Rule` ganha `tags: tuple[str, ...]`; `category` opcional; `apply_rules` devolve `RuleMatch(category, tags)`. |
| `src/finance/actions/tag.py` | aplicar/remover tag num `Entry`, validando que não vira segundo projeto. |
| `src/finance/reports/project.py` | `project_settlement` (acerto) e `project_result` (receita/despesa/resultado). |
| `src/finance/reports/month.py` | exclusão dos projetos com rateio + total excluído por projeto. |
| `src/finance/cache/schema.py` | tabela `entry_tags(entry_id, tag)` indexada por tag — `tags` como texto `a;b` não dá para consultar direito. O cache é descartável, o `rebuild` preenche. |
| `src/finance/cache/connection.py` | `projects.yaml` entra em `CONFIG_FILES` (senão o cache não envelhece quando a cota muda). |
| `examples/data/projects.yaml` | exemplo fictício: `obra` (percentual), `barco` (divisão igual), `angra` (sem rateio). |

## Plano de implementação (RED primeiro em cada fase)

1. **Projeto e cotas.** `load_projects` + `share_of`: soma ≠ 100, owner fora da
   cota, id duplicado, divisão igual, centavo residual no owner.
2. **Tag por regra.** `rules.yaml` com `tags:`, `category` opcional,
   `apply_rules` devolvendo as duas coisas; `import` e `recategorize` gravando
   tag; tag aditiva nunca removida; regra só-tag não mexe em categoria.
3. **Tag à mão.** `finance tag`, `tag clear`, `--from`, `--rule`; segunda tag de
   projeto é erro.
4. **Acerto.** `project_settlement`: gasto, devido, devolvido, saldo por
   participante; devolução sem `de:` contada à parte; projeto sem rateio recusa o
   acerto e usa `project_result`.
5. **`report month`.** Projeto com rateio fora por default, total excluído
   visível, `--with-projects` e `--project`; projeto sem rateio permanece dentro.
6. **Saída.** `report project` tabela e `--json`, `project list`, `docs/cli.md`.

## O que está travado pela #5

Fases 1 a 6 não dependem da #5: o modelo, as tags, o acerto e os relatórios
funcionam com tag posta à mão. O que só funciona depois é a regra que reconhece
**quem** pagou — hoje o extrato de conta em CSV não traz o nome do favorecido,
então `de:<participante>` sai do `finance tag --from`, uma devolução por vez.
Com a #5, uma regra por participante resolve na importação.
