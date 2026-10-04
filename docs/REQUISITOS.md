# Requisitos

Painel de deputado federal no Amazonas. A página tem abas de 2022 e de 2026. Em 2022, a navegação por âncoras reúne eleitos, quociente, gastos, votos, partidos e o movimento entre as duas eleições. Em 2026, a mesma organização mostra candidaturas e despesas contratadas.

## Tabela de IDs

| ID | Resumo | Status | Prioridade |
| --- | --- | --- | --- |
| REQ-001 | Aba com os dados de 2026 | implementado | 1 |

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

- Votos de 2026 durante a apuração: ver [APURACAO_AO_VIVO.md](APURACAO_AO_VIVO.md).
