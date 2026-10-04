# Apuração ao vivo de 2026

Base para mostrar, na aba de 2026, os votos de deputado federal no Amazonas enquanto o TSE totaliza. O painel hoje só tem votação fechada de 2022, lida do CSV de dados abertos. Esse CSV de 2026 não existe durante a apuração.

## Fonte

Usar o JSON oficial de resultado unificado (arquivo EA20), o mesmo que o portal Resultados lê.

Arquivo do cargo, um por estado:

```
https://resultados.tse.jus.br/oficial/ele2026/6259/dados/am/am-c0006-e006259-u.json
```

| Parte do endereço | Valor | Significado |
| --- | --- | --- |
| ambiente | `oficial` | Divulgação real, em `https://resultados.tse.jus.br` |
| ciclo | `ele2026` | Ciclo das eleições gerais de 2026 |
| eleição | `6259` | Eleição ordinária estadual, 1º turno |
| abrangência | `am` | Amazonas |
| cargo | `0006` | Deputado federal, com quatro dígitos no nome do arquivo |
| sufixo | `-u.json` | Resultado unificado (EA20) |

O 2º turno da mesma eleição estadual, se houver, usa o código `6260` no lugar de `6259`. Deputado federal se define no 1º turno; `6260` não entra nesta aba.

Códigos conferidos em `https://resultados.tse.jus.br/oficial/comum/config/ele-c.json`, pleito `3220`, data `04/10/2026`:

- `6257` — eleição federal (presidente)
- `6259` — eleição estadual (governador, senador, deputado federal, deputado estadual, deputado distrital). O segundo turno previsto é `6260`.
- `6261` — conselheiro distrital

Documentação do TSE: [Informações técnicas sobre a divulgação de resultados 2026](https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados).

## O que o arquivo traz

Consulta feita em 04/10/2026, com o arquivo ainda parcial: `and` = `p`, 85,02% das seções (`s.pst`), quociente `qe` = 224485, 8 vagas (`nv`). O arquivo tinha cerca de 42 KB.

Caminho dos candidatos:

```
carg[0].agr[].par[].cand[]
```

`carg[0]` é o deputado federal (`cd` = `6`). Cada `agr` é um partido ou uma federação. Cada `par` é um partido. O candidato está em `cand`.

### Candidato

| Campo | Uso |
| --- | --- |
| `sqcand` | Sequencial oficial. É o `SQ_CANDIDATO` de 2026. Chave estável para cruzar com o painel. |
| `n` | Número do candidato em 2026. |
| `nmu` | Nome de urna. |
| `vap` | Votos nominais apurados, em texto. Inclui voto com destinação anulada. |
| `pvapn` | Percentual com casas decimais, texto com ponto. `pvap` é o percentual já arredondado, com vírgula. |
| `dvt` | Destinação do voto (`Válido`, `Anulado`, `Anulado sub judice`, `Válido (legenda)`). |
| `st` | Situação escrita pelo TSE. Vem vazia enquanto a apuração não atribui eleito. |
| `e` | `s` ou `n`. Indica eleito quando o TSE já atribuiu. |

### Partido e federação

| Campo | Uso |
| --- | --- |
| `par.sg` | Sigla. |
| `par.n` | Número do partido. |
| `par.nfed` | Número da federação em `carg[0].fed[].n`. Vazio quando o partido concorre sozinho. |
| `par.tvtn` | Votos nominais válidos do partido. É esta a soma que entra no quociente. |
| `par.tvan` | Soma de todos os `vap` do partido, inclusive destinação anulada. |
| `par.tvtl` | Votos de legenda. |
| `par.tval` | Votos de legenda válidos. Coincide com `tvtl` quando a legenda está válida. |
| `agr.vag` | Vagas já atribuídas ao grupo (partido isolado ou federação). |
| `carg[0].fed` | Federações: `n`, `sg`, `com` e `npar` (números dos partidos membros). |
| `carg[0].qe` | Quociente eleitoral calculado pelo TSE naquele instante. Muda enquanto `and` for `p`. |
| `carg[0].nv` | Vagas. No Amazonas, 8. |

`tvtn` não é a soma crua de `vap`. No PDT e no Solidariedade, nesta consulta, a soma de `vap` era maior que `tvtn` porque parte dos votos nominais tinha outra destinação. Para faixa, ordenação e quociente, usar `tvtn` do partido e, no candidato, o `vap` somente quando `dvt` indicar voto válido. Mostrar o `vap` bruto deixa o candidato comparável à tela do TSE; a soma do grupo deve seguir `tvtn`, senão o quociente não fecha.

Totais do cargo em `v`: `vnom` (nominais), `vl` (legenda), `vv` (válidos, nominais mais legenda), `vb` (brancos), `tvn` (nulos), `tv` (total). Nesta consulta, `vnom` + `vl` = `vv`.

Andamento:

| Campo | Uso |
| --- | --- |
| `and` | `p` enquanto a totalização da UF está aberta. `f` quando fecha. |
| `s.pst` | Percentual de seções totalizadas, com vírgula. `s.st` e `s.ts` são seções totalizadas e seções totais. |
| `dg`, `hg` | Data e hora de geração do arquivo. |
| `dt`, `ht` | Data e hora da totalização. Exibir este carimbo na aba, sem converter fuso. |

## Encaixe no painel

O JSON estático (`painel/public/dados/amazonas.json`, gerado por `scripts/exportar_painel_am.py`) não deve ser reescrito a cada atualização. Gastos, fotos e a lista de candidaturas continuam nele. A aba busca o EA20 e sobrepõe a apuração em memória.

O campo `votos` desse JSON é a votação de 2022. Quem disputou os dois anos está no registro de 2022, e o `votos` dele não pode ser substituído pelo `vap`. Guardar a apuração em campo próprio, `votos2026`.

O registro exportado não traz o sequencial. A ponte disponível hoje:

- quem disputou os dois anos: `numero2026`
- quem só disputa 2026: `numero`

Os dois correspondem a `cand.n`. O número é único para deputado federal no Amazonas. Na exportação seguinte, gravar também `sequencial2026` e passar a cruzar por `sqcand`. Substituição de candidatura troca o número e mantém o sentido do sequencial.

Fotos de 2026 já usam o sequencial no caminho `/fotos/2026/{sequencial}.jpg`.

Enquanto `and` for `p`:

- mostrar votos, percentual, seções totalizadas e o carimbo `dt` `ht`
- usar o `qe` publicado pelo TSE, sem recalcular
- tratar `st` vazio como apuração em andamento; não inferir eleito a partir do percentual nem do quociente
- quociente do grupo pelo `tvtn`, somando os partidos com o mesmo `nfed` e deixando sozinho quem tem `nfed` vazio

Quando `and` passar a `f`, gravar um snapshot no JSON do painel (`votos2026`, situação e quociente) e parar o polling.

## Como buscar

Uma requisição por atualização, só desse arquivo do Amazonas.

A CDN devolve `ETag`, `Last-Modified` e `Cache-Control` de algumas dezenas de segundos. Repetir o pedido com `If-None-Match`. Resposta `304` significa que a tela pode ficar como está. O `304` também conta no limite de acesso.

Intervalo de 45 a 60 segundos. Abaixo disso o pedido só relê o cache.

O limite oficial é de 100 requisições por segundo por IP. Acima disso o TSE pode bloquear o IP por cerca de 10 minutos, e o prazo recomeça se o acesso continuar. Vários `404` também podem bloquear. Montar a URL com os códigos deste documento; não varrer arquivos para descobrir o que existe.

Na consulta, a resposta GET com `Origin: http://localhost:5173` trouxe `Access-Control-Allow-Origin` de volta com essa origem. O painel pode ler o JSON direto do navegador, sem proxy.

## Fora desta base

- CSV `votacao_candidato_munzona` de 2026. É o arquivo histórico de dados abertos, no mesmo papel do que `eleitoral/tse.py` já baixa para 2022. Serve para congelar o resultado depois, não para a noite da apuração.
- Prestação de contas e DivulgaCand. São despesa, não voto.
- Município, zona e boletim de urna. A aba usa o consolidado da UF.
