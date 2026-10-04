# Requisitos

Painel de deputado federal no Amazonas. A página tem abas de 2022 e de 2026. Em 2022, a navegação por âncoras reúne eleitos, quociente, gastos, votos, partidos e o movimento entre as duas eleições. Em 2026, a mesma organização mostra candidaturas, despesas contratadas e os votos ao vivo da apuração.

## Tabela de IDs

| ID | Resumo | Status | Prioridade |
| --- | --- | --- | --- |
| REQ-001 | Aba com os dados de 2026 | implementado | 1 |
| REQ-002 | Votos ao vivo de 2026 | implementado | 2 |

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

## Próximos requisitos (ainda não detalhados)
