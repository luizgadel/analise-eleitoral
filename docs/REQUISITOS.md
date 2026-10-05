# Requisitos

Painel de deputado federal, de deputado estadual e de senador no Amazonas. A pessoa escolhe o cargo. Em cada um, a página tem abas de 2022 e de 2026. Em 2022, a navegação por âncoras reúne eleitos, quociente, gastos, votos, partidos e o movimento entre as duas eleições. Em 2026, a mesma organização mostra candidaturas, despesas contratadas e os votos ao vivo da apuração. Na lista de votos e gastos, o fundo marca quem levaria cadeira neste instante.

## Tabela de IDs

| ID | Resumo | Status | Prioridade |
| --- | --- | --- | --- |
| REQ-001 | Aba com os dados de 2026 | implementado | 1 |
| REQ-002 | Votos ao vivo de 2026 | implementado | 2 |
| REQ-003 | Destaque de quem está sendo eleito | implementado | 3 |
| REQ-004 | Deputados estaduais no mesmo desenho | implementado | 4 |
| REQ-005 | Aba de senadores no mesmo desenho | implementado | 5 |

## REQ-003 — Destaque de quem está sendo eleito

**Status:** implementado
**Prioridade:** 3
**Depende de:** nenhuma

### Objetivo

Na seção "Votos de 2026 e gastos da campanha", calcular quais candidatos estão sendo eleitos neste instante da apuração e marcar essas linhas com outra cor de fundo.

### Experiência desejada

- Na lista de votos e gastos de 2026, as candidaturas que levariam uma cadeira com os votos apurados agora ficam com cor de fundo diferente.
- A conta usa o quociente eleitoral publicado pelo TSE, o quociente partidário da legenda e as sobras, e acompanha cada atualização da apuração.
- A cor indica essa conta do momento. Não substitui a marca oficial de eleito do TSE.

### Fora do escopo deste requisito

- Mudar a seção "Eleitos em 2026", que continua só com quem o TSE marcou.
- Recalcular o quociente eleitoral publicado pelo TSE.
- Aplicar o mesmo destaque na aba de 2022.

### Critérios de aceite

- [x] Na seção "Votos de 2026 e gastos da campanha", a lista calcula quem levaria uma das cadeiras com os votos deste instante.
- [x] Essas linhas têm cor de fundo diferente das demais.
- [x] O destaque acompanha a atualização da apuração.
- [x] A marca oficial de eleito do TSE não é substituída por essa conta.

## REQ-002 — Votos ao vivo de 2026

**Status:** implementado
**Prioridade:** 2
**Depende de:** nenhuma

### Objetivo

Exibir na aba de 2026 os votos ao vivo da apuração, consumidos como em `docs/APURACAO_AO_VIVO.md` e organizados da mesma forma que os dados de 2022.

### Experiência desejada

- Na aba de 2026, a pessoa vê os votos de deputado federal no Amazonas enquanto o TSE totaliza.
- A organização segue a de 2022: resumo, quociente das federações e partidos, e lista de candidaturas com busca e ordenação por votos.
- Eleito só aparece quando o TSE marca. A tela mostra o percentual de seções e o carimbo de data e hora da totalização, sem converter fuso.
- A atualização periódica sobrepõe a apuração em memória. O JSON estático não é reescrito a cada consulta, e os votos de 2022 permanecem intactos.
- Quando a totalização fecha, o polling para e o snapshot fica gravado no JSON do painel.

### Fora do escopo deste requisito

- O CSV histórico de votação por município e zona de 2026.
- Prestação de contas, DivulgaCand, município, zona e boletim de urna.
- O segundo turno (`6260`). Deputado federal se define no primeiro.
- Recalcular o quociente ou inferir eleito a partir do percentual.

### Critérios de aceite

- [x] A aba de 2026 busca o JSON unificado do deputado federal no Amazonas (`6259`, cargo `0006`) e sobrepõe a apuração em memória, sem reescrever `amazonas.json` a cada atualização.
- [x] Os votos ao vivo seguem a organização de 2022: resumo, quociente das federações e partidos com o `qe` do TSE e o `tvtn`, e lista de candidaturas com busca e ordenação por votos.
- [x] Cada candidatura mostra o voto nominal válido, o percentual, o partido e o número de 2026. O cruzamento usa o número de 2026 e, quando existir, o sequencial.
- [x] A aba mostra as seções totalizadas e o carimbo `dt` e `ht`, sem converter fuso.
- [x] Enquanto a totalização estiver aberta, a tela atualiza entre 45 e 60 segundos. Resposta inalterada mantém a tela.
- [x] Situação vazia não vira eleito. Eleito só aparece quando o TSE indica.
- [x] O campo de votos de 2022 não é substituído pelo voto de 2026.
- [x] Quando a totalização fecha, o polling para e um snapshot com `votos2026`, situação e quociente fica gravado no JSON do painel.

## REQ-001 — Aba com os dados de 2026

**Status:** implementado
**Prioridade:** 1
**Depende de:** nenhuma

### Objetivo

Adicionar uma aba na página para exibir os dados de 2026, organizados da mesma forma que os dados de 2022.

### Experiência desejada

- A página passa a ter uma aba de 2026, além da visão atual.
- Nessa aba, candidaturas e despesas de 2026 aparecem nos mesmos tipos de bloco usados para 2022: resumo, maiores gastos, faixas de gasto, lista com busca e ordenação, gastos por partido e candidaturas por partido.
- Quem disputa os dois anos aparece na aba de 2026 com o partido e o número de 2026.
- A visão de 2022 continua no lugar, com a organização que já tem.

### Fora do escopo deste requisito

- Eleitos, votos, quociente e custo por voto de 2026, porque o painel não tem esses resultados.
- O recorte de gasto até uma semana antes da votação, que só existe para 2022.
- Reorganizar as seções que comparam os dois anos (trocas de partido, quem saiu e quem entrou).

### Critérios de aceite

- [x] A página oferece uma aba de 2026 além da visão atual.
- [x] A aba de 2026 repete a organização de 2022 nos blocos que têm dado equivalente: resumo, 50 maiores gastos, faixas de gasto, lista com busca e ordenação, gastos por partido e candidaturas por partido.
- [x] A aba de 2026 lista as candidaturas de 2026 com partido, número e despesa contratada.
- [x] Quem disputou os dois anos aparece na aba de 2026 com o partido e o número de 2026.
- [x] A visão de 2022 permanece como está.

## REQ-004 — Deputados estaduais no mesmo desenho

**Status:** implementado
**Prioridade:** 4
**Depende de:** nenhuma

### Objetivo

Fazer para deputado estadual no Amazonas o mesmo painel que já existe para deputado federal.

### Experiência desejada

- A pessoa escolhe deputado estadual e vê a mesma organização do deputado federal.
- Em 2022: eleitos, quociente, gastos, votos, partidos e o movimento entre as duas eleições.
- Em 2026: candidaturas, despesas contratadas, votos ao vivo e o fundo de quem levaria cadeira neste instante.
- O painel de deputado federal continua no lugar.

### Fora do escopo deste requisito

- Outros cargos e outros estados.
- A Câmara dos Deputados como fonte dos estaduais. Eles não são deputados federais.

### Critérios de aceite

- [x] O painel oferece deputado estadual no Amazonas, no mesmo desenho do deputado federal.
- [x] A visão de 2022 traz eleitos, quociente, gastos, votos, partidos e quem saiu ou entrou em 2026.
- [x] A visão de 2026 traz candidaturas, despesas contratadas, votos ao vivo da apuração e o destaque de quem levaria cadeira.
- [x] A apuração ao vivo usa o arquivo do cargo de deputado estadual.
- [x] O painel de deputado federal permanece como está.

## REQ-005 — Aba de senadores no mesmo desenho

**Status:** implementado
**Prioridade:** 5
**Depende de:** nenhuma

### Objetivo

Fazer uma aba de senador no Amazonas no mesmo desenho das abas de deputado federal e deputado estadual.

### Experiência desejada

- A pessoa escolhe senador e vê a mesma organização dos deputados.
- Em 2022: eleitos, quociente, gastos, votos, partidos e o movimento entre as duas eleições.
- Em 2026: candidaturas, despesas contratadas, votos ao vivo e o fundo de quem levaria cadeira neste instante.
- As abas de deputado federal e de deputado estadual continuam no lugar.

### Fora do escopo deste requisito

- Outros cargos e outros estados.
- A Câmara dos Deputados como fonte dos senadores.

### Critérios de aceite

- [x] O painel oferece senador no Amazonas, no mesmo desenho dos deputados.
- [x] A visão de 2022 traz eleitos, quociente, gastos, votos, partidos e quem saiu ou entrou em 2026.
- [x] A visão de 2026 traz candidaturas, despesas contratadas, votos ao vivo da apuração e o destaque de quem levaria cadeira.
- [x] A apuração ao vivo usa o arquivo do cargo de senador.
- [x] Os painéis de deputado federal e de deputado estadual permanecem como estão.

## Próximos requisitos (ainda não detalhados)
