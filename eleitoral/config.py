"""Caminhos, endereços oficiais e critérios usados no projeto."""

from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_BRUTOS = RAIZ / "dados" / "brutos"
DIR_PROCESSADOS = RAIZ / "dados" / "processados"

# Prestação de contas parcial da campanha de 2026 considerada até esta data.
DATA_CORTE_2026 = date(2026, 9, 28)

# Código de cargo no TSE: 6 = Deputado Federal.
CARGO_DEPUTADO_FEDERAL = 6

URL_CANDIDATOS = {
    2022: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip",
    2026: "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip",
}
URL_VOTOS_2022 = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/"
    "votacao_candidato_munzona_2022.zip"
)
URL_CONTAS = {
    2022: (
        "https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/"
        "prestacao_de_contas_eleitorais_candidatos_2022.zip"
    ),
    2026: (
        "https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas/"
        "prestacao_de_contas_eleitorais_candidatos_2026.zip"
    ),
}

URL_DEPUTADOS = "https://dadosabertos.camara.leg.br/api/v2/deputados"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Termos já normalizados (maiúsculas, sem acento). A classificação oficial do TSE
# usa "DS_ORIGEM_DESPESA": publicidade impressa, adesivos, carros de som,
# impulsionamento e páginas na internet.
TERMOS_PUBLICIDADE = (
    "PUBLICIDADE",
    "PROPAGANDA",
    "IMPULSIONAMENTO",
    "PAGINAS NA INTERNET",
)

COLUNAS_CANDIDATOS = [
    "ANO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "NM_TIPO_ELEICAO",
    "NR_TURNO",
    "SG_UF",
    "CD_CARGO",
    "DS_CARGO",
    "SQ_CANDIDATO",
    "NR_CANDIDATO",
    "NM_CANDIDATO",
    "NM_URNA_CANDIDATO",
    "NM_SOCIAL_CANDIDATO",
    "NR_CPF_CANDIDATO",
    "NR_TITULO_ELEITORAL_CANDIDATO",
    "DS_SITUACAO_CANDIDATURA",
    "NR_PARTIDO",
    "SG_PARTIDO",
    "NM_PARTIDO",
    "SG_FEDERACAO",
    "DS_SIT_TOT_TURNO",
    "DS_GENERO",
    "DT_NASCIMENTO",
    "DT_GERACAO",
]

COLUNAS_VOTOS = [
    "ANO_ELEICAO",
    "NR_TURNO",
    "NM_TIPO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "SG_UF",
    "CD_CARGO",
    "DS_CARGO",
    "SQ_CANDIDATO",
    "NR_CANDIDATO",
    "NM_CANDIDATO",
    "NM_URNA_CANDIDATO",
    "SG_PARTIDO",
    "NM_PARTIDO",
    "DS_SIT_TOT_TURNO",
    "QT_VOTOS_NOMINAIS",
]

COLUNAS_DESPESAS = [
    "DT_GERACAO",
    "ANO_ELEICAO",
    "NM_TIPO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "SG_UF",
    "CD_CARGO",
    "DS_CARGO",
    "SQ_CANDIDATO",
    "NR_CANDIDATO",
    "NM_CANDIDATO",
    "NM_URNA_CANDIDATO",
    "SG_PARTIDO",
    "DS_ORIGEM_DESPESA",
    "DS_TIPO_DESPESA",
    "DS_NATUREZA_DESPESA",
    "DS_DESPESA",
    "DT_DESPESA",
    "VR_DESPESA_CONTRATADA",
]

COLUNAS_TIPO_DESPESA = (
    "DS_ORIGEM_DESPESA",
    "DS_TIPO_DESPESA",
    "DS_NATUREZA_DESPESA",
)

RENOMEAR_CANDIDATO = {
    "SG_UF": "uf",
    "SG_PARTIDO": "partido",
    "NM_PARTIDO": "nome_partido",
    "NR_CANDIDATO": "numero",
    "NM_CANDIDATO": "nome",
    "NM_URNA_CANDIDATO": "nome_urna",
    "NM_SOCIAL_CANDIDATO": "nome_social",
    "NR_TITULO_ELEITORAL_CANDIDATO": "titulo",
    "NR_CPF_CANDIDATO": "cpf",
    "SQ_CANDIDATO": "sequencial",
    "DS_SITUACAO_CANDIDATURA": "situacao",
    "DS_SIT_TOT_TURNO": "resultado",
    "SG_FEDERACAO": "federacao",
    "DS_GENERO": "genero",
    "DT_NASCIMENTO": "nascimento",
    "ANO_ELEICAO": "ano",
}

COLUNAS_EXIBICAO_CANDIDATO = [
    "partido",
    "uf",
    "numero",
    "nome_urna",
    "nome",
    "situacao",
    "resultado",
    "federacao",
]

TAMANHO_PEDACO = 200_000
