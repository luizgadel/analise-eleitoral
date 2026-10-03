# Análise eleitoral

Notebooks para ler os dados abertos do TSE e da Câmara dos Deputados e olhar a disputa de deputado federal em 2022 e 2026.

O primeiro notebook mostra:

- candidaturas aptas a deputado federal em 2022, por partido
- deputados federais em exercício agora, por partido
- candidaturas aptas a deputado federal em 2026, por partido
- quem saiu da disputa, quem entrou e quem trocou de partido
- votos nominais de 2022 por candidato
- despesas contratadas de publicidade em 2022
- despesas contratadas de publicidade em 2026 até 28/09/2026

## Como rodar

Na pasta do projeto:

```bash
pip install -r requirements.txt
jupyter notebook notebooks/01_deputados_federais.ipynb
```

Execute as células de cima para baixo. A primeira execução baixa os arquivos oficiais para `dados/brutos/` e guarda as tabelas já filtradas em `dados/processados/`. Nas próximas vezes, o notebook reaproveita esses arquivos.

Os ZIPs de candidatos são pequenos. Os de votação por município e zona e os de prestação de contas são grandes: a primeira execução dessas células pode levar vários minutos e ocupar alguns GB em disco.

## Fontes

- Candidatos, votos e prestação de contas: [Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/)
- Deputados em exercício: [Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/)

A publicidade usa a classificação oficial da despesa contratada (`DS_ORIGEM_DESPESA`): entram tipos com publicidade, propaganda, impulsionamento de conteúdo e criação de páginas na internet. A célula de gastos lista os tipos encontrados e marca quais entraram na soma.

Candidaturas com situação diferente de apta ficam de fora. O recorte de 2026 usa a data da despesa, não a data em que o TSE gerou o arquivo.
