"""Resumos e comparação entre as disputas de 2022 e 2026."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from eleitoral.regras import (
    cpf_comparavel,
    eh_eleito,
    formatar_reais,
    limpar_codigo,
    normalizar_data,
    normalizar_texto,
)


def resumo_por_partido(
    quadro: pd.DataFrame,
    valor: str | None = None,
    coluna_partido: str = "partido",
    nome_contagem: str = "candidatos",
) -> pd.DataFrame:
    if quadro.empty:
        colunas = [coluna_partido, nome_contagem]
        if valor:
            colunas.append(valor)
        return pd.DataFrame(columns=colunas)
    if valor is None:
        resumo = (
            quadro.groupby(coluna_partido, dropna=False)
            .size()
            .reset_index(name=nome_contagem)
            .sort_values([nome_contagem, coluna_partido], ascending=[False, True], kind="stable")
            .reset_index(drop=True)
        )
        return resumo
    resumo = (
        quadro.groupby(coluna_partido, dropna=False)
        .agg(**{nome_contagem: (valor, "size"), valor: (valor, "sum")})
        .reset_index()
        .sort_values([valor, coluna_partido], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
    return resumo


def tabela_reais(quadro: pd.DataFrame, coluna: str = "gasto_publicidade") -> pd.DataFrame:
    visivel = quadro.copy()
    if coluna in visivel.columns:
        visivel[coluna] = visivel[coluna].map(formatar_reais)
    return visivel


def _preparar_chaves(quadro: pd.DataFrame) -> pd.DataFrame:
    chaves = quadro.copy()
    chaves["titulo_limpo"] = chaves["titulo"].map(limpar_codigo) if "titulo" in chaves.columns else ""
    chaves["cpf_limpo"] = chaves["cpf"].map(cpf_comparavel) if "cpf" in chaves.columns else ""
    chaves["nome_chave"] = chaves["nome"].map(normalizar_texto) if "nome" in chaves.columns else ""
    chaves["nasc_chave"] = chaves["nascimento"].map(normalizar_data) if "nascimento" in chaves.columns else ""
    chaves["uf_chave"] = chaves["uf"].map(limpar_codigo) if "uf" in chaves.columns else ""
    return chaves


def _conjunto_titulo(quadro: pd.DataFrame) -> set[str]:
    return {valor for valor in quadro["titulo_limpo"] if valor}


def _conjunto_cpf(quadro: pd.DataFrame) -> set[str]:
    return {valor for valor in quadro["cpf_limpo"] if valor}


def _conjunto_nome(quadro: pd.DataFrame) -> set[tuple[str, str, str]]:
    return {
        (uf, nome, nascimento)
        for uf, nome, nascimento in zip(quadro["uf_chave"], quadro["nome_chave"], quadro["nasc_chave"])
        if nome and nascimento
    }


def _permanece(origem: pd.DataFrame, destino: pd.DataFrame) -> pd.Series:
    titulos = _conjunto_titulo(destino)
    cpfs = _conjunto_cpf(destino)
    nomes = _conjunto_nome(destino)
    por_titulo = origem["titulo_limpo"].ne("") & origem["titulo_limpo"].isin(titulos)
    por_cpf = origem["cpf_limpo"].ne("") & origem["cpf_limpo"].isin(cpfs)
    por_nome = pd.Series(
        [
            bool(nome and nascimento and (uf, nome, nascimento) in nomes)
            for uf, nome, nascimento in zip(origem["uf_chave"], origem["nome_chave"], origem["nasc_chave"])
        ],
        index=origem.index,
    )
    return por_titulo | por_cpf | por_nome


def _serie_partido(quadro: pd.DataFrame, coluna: str) -> pd.Series:
    if quadro.empty or coluna not in quadro.columns:
        return pd.Series(dtype=object)
    return quadro.drop_duplicates(coluna).set_index(coluna)["partido"]


def _partido_destino(origem: pd.DataFrame, destino: pd.DataFrame) -> pd.Series:
    por_titulo = _serie_partido(destino.loc[destino["titulo_limpo"].ne("")], "titulo_limpo")
    por_cpf = _serie_partido(destino.loc[destino["cpf_limpo"].ne("")], "cpf_limpo")
    com_nome = destino.loc[destino["nome_chave"].ne("") & destino["nasc_chave"].ne("")].copy()
    if com_nome.empty:
        por_nome = pd.Series(dtype=object)
    else:
        com_nome["chave"] = list(zip(com_nome["uf_chave"], com_nome["nome_chave"], com_nome["nasc_chave"]))
        por_nome = _serie_partido(com_nome, "chave")
    partido = origem["titulo_limpo"].map(por_titulo)
    partido = partido.fillna(origem["cpf_limpo"].map(por_cpf))
    chaves_nome = pd.Series(
        list(zip(origem["uf_chave"], origem["nome_chave"], origem["nasc_chave"])),
        index=origem.index,
    )
    return partido.fillna(chaves_nome.map(por_nome))


@dataclass
class ComparacaoDisputa:
    sairam: pd.DataFrame
    entraram: pd.DataFrame
    continuam: pd.DataFrame
    mudaram_de_partido: pd.DataFrame
    eleitos_que_nao_concorrem: pd.DataFrame
    resumo_sairam: pd.DataFrame
    resumo_entraram: pd.DataFrame
    resumo_continuam: pd.DataFrame


def comparar_disputas(candidatos_2022: pd.DataFrame, candidatos_2026: pd.DataFrame) -> ComparacaoDisputa:
    anterior = _preparar_chaves(candidatos_2022)
    atual = _preparar_chaves(candidatos_2026)
    fica = _permanece(anterior, atual)
    chega = _permanece(atual, anterior)

    sairam = candidatos_2022.loc[~fica].copy()
    entraram = candidatos_2026.loc[~chega].copy()
    continuam = candidatos_2022.loc[fica].copy()
    continuam["partido_2022"] = continuam["partido"]
    continuam["partido_2026"] = _partido_destino(anterior.loc[fica], atual).to_numpy()
    mudaram = continuam.loc[
        continuam["partido_2022"].map(normalizar_texto).ne(continuam["partido_2026"].map(normalizar_texto))
    ].copy()

    if "resultado" in candidatos_2022.columns:
        eleitos = sairam.loc[sairam["resultado"].map(eh_eleito)].copy()
    else:
        eleitos = sairam.iloc[0:0].copy()

    return ComparacaoDisputa(
        sairam=sairam.reset_index(drop=True),
        entraram=entraram.reset_index(drop=True),
        continuam=continuam.reset_index(drop=True),
        mudaram_de_partido=mudaram.reset_index(drop=True),
        eleitos_que_nao_concorrem=eleitos.reset_index(drop=True),
        resumo_sairam=resumo_por_partido(sairam),
        resumo_entraram=resumo_por_partido(entraram),
        resumo_continuam=resumo_por_partido(continuam),
    )


@dataclass
class CruzamentoDeputados:
    na_disputa_2026: pd.DataFrame
    fora_da_disputa_2026: pd.DataFrame
    resumo_fora: pd.DataFrame
    resumo_na_disputa: pd.DataFrame


def cruzar_deputados(deputados: pd.DataFrame, candidatos_2026: pd.DataFrame) -> CruzamentoDeputados:
    candidatos = _preparar_chaves(candidatos_2026)
    cpfs = _conjunto_cpf(candidatos)
    nomes_civis = {
        (uf, nome)
        for uf, nome in zip(candidatos["uf_chave"], candidatos["nome_chave"])
        if nome
    }
    nomes_urna = set()
    if "nome_urna" in candidatos_2026.columns:
        nomes_urna = {
            (limpar_codigo(uf), normalizar_texto(nome))
            for uf, nome in zip(candidatos_2026["uf"], candidatos_2026["nome_urna"])
            if normalizar_texto(nome)
        }

    def esta_na_disputa(linha: pd.Series) -> bool:
        cpf = cpf_comparavel(linha.get("cpf", ""))
        if cpf and cpf in cpfs:
            return True
        uf = limpar_codigo(linha.get("uf", ""))
        civil = normalizar_texto(linha.get("nome_civil", ""))
        if civil and (uf, civil) in nomes_civis:
            return True
        for nome in (linha.get("nome_eleitoral", ""), linha.get("nome", "")):
            if (uf, normalizar_texto(nome)) in nomes_urna or (uf, normalizar_texto(nome)) in nomes_civis:
                return True
        return False

    mascara = deputados.apply(esta_na_disputa, axis=1)
    na_disputa = deputados.loc[mascara].reset_index(drop=True)
    fora = deputados.loc[~mascara].reset_index(drop=True)
    return CruzamentoDeputados(
        na_disputa_2026=na_disputa,
        fora_da_disputa_2026=fora,
        resumo_fora=resumo_por_partido(fora, nome_contagem="deputados"),
        resumo_na_disputa=resumo_por_partido(na_disputa, nome_contagem="deputados"),
    )


def grafico_barras(resumo: pd.DataFrame, titulo: str, coluna: str, eixo_y: str):
    import matplotlib.pyplot as plt

    eixo = resumo.plot.bar(
        x="partido",
        y=coluna,
        legend=False,
        figsize=(12, 4.8),
        color="#1f4e79",
    )
    eixo.set_title(titulo)
    eixo.set_xlabel("Partido")
    eixo.set_ylabel(eixo_y)
    eixo.tick_params(axis="x", labelrotation=75)
    plt.tight_layout()
    return eixo
