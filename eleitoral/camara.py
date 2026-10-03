"""Deputados federais em exercício na Câmara dos Deputados."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

from eleitoral.config import DIR_PROCESSADOS, URL_DEPUTADOS, USER_AGENT
from eleitoral.regras import limpar_codigo
from eleitoral.tse import ErroFonte


def _sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return sessao


def _listar_deputados(sessao: requests.Session, uf: str | None = None) -> list[dict]:
    url: str | None = URL_DEPUTADOS
    parametros: dict | None = {"itens": 100, "ordem": "ASC", "ordenarPor": "nome"}
    if uf:
        parametros["siglaUf"] = uf
    registros: list[dict] = []
    while url:
        resposta = sessao.get(url, params=parametros, timeout=60)
        resposta.raise_for_status()
        corpo = resposta.json()
        registros.extend(corpo.get("dados", []))
        parametros = None
        url = next((link["href"] for link in corpo.get("links", []) if link.get("rel") == "next"), None)
    return registros


def _detalhe(identificador: int) -> dict:
    with _sessao() as sessao:
        resposta = sessao.get(f"{URL_DEPUTADOS}/{identificador}", timeout=60)
        resposta.raise_for_status()
        return resposta.json().get("dados", {})


def carregar_deputados_atuais(atualizar: bool = False, uf: str | None = None) -> pd.DataFrame:
    """Lista oficial dos deputados em exercício, com o partido atual de cada um."""
    if uf:
        uf = uf.strip().upper()
    cache = DIR_PROCESSADOS / f"deputados_atuais_{uf}.csv" if uf else DIR_PROCESSADOS / "deputados_atuais.csv"
    if cache.exists() and not atualizar:
        print(f"Lendo tabela já processada: {cache.name}")
        return pd.read_csv(cache, sep=";", dtype=str, encoding="utf-8-sig", keep_default_na=False)

    print("Consultando a Câmara dos Deputados...")
    sessao = _sessao()
    try:
        lista = _listar_deputados(sessao, uf=uf)
    except requests.RequestException as erro:
        raise ErroFonte("Não foi possível consultar os deputados em exercício na API da Câmara.") from erro
    if not lista:
        raise ErroFonte("A API da Câmara não devolveu deputados em exercício.")

    detalhes: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        tarefas = {pool.submit(_detalhe, int(item["id"])): int(item["id"]) for item in lista}
        concluidas = 0
        for tarefa in as_completed(tarefas):
            identificador = tarefas[tarefa]
            concluidas += 1
            try:
                detalhes[identificador] = tarefa.result()
            except requests.RequestException:
                detalhes[identificador] = {}
            if concluidas % 100 == 0 or concluidas == len(tarefas):
                print(f"Fichas consultadas: {concluidas} de {len(tarefas)}")

    linhas = []
    for item in lista:
        identificador = int(item["id"])
        ficha = detalhes.get(identificador, {})
        status = ficha.get("ultimoStatus") or {}
        linhas.append(
            {
                "id": str(identificador),
                "nome": limpar_codigo(item.get("nome")),
                "nome_eleitoral": limpar_codigo(status.get("nomeEleitoral") or item.get("nome")),
                "nome_civil": limpar_codigo(ficha.get("nomeCivil")),
                "partido": limpar_codigo(status.get("siglaPartido") or item.get("siglaPartido")) or "(sem sigla)",
                "uf": limpar_codigo(status.get("siglaUf") or item.get("siglaUf")),
                "cpf": limpar_codigo(ficha.get("cpf")),
                "nascimento": limpar_codigo(ficha.get("dataNascimento")),
                "situacao": limpar_codigo(status.get("situacao")),
                "email": limpar_codigo(status.get("email") or item.get("email")),
                "legislatura": limpar_codigo(status.get("idLegislatura") or item.get("idLegislatura")),
            }
        )
    quadro = pd.DataFrame(linhas)
    quadro = quadro.sort_values(["partido", "uf", "nome"], kind="stable").reset_index(drop=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    quadro.to_csv(cache, index=False, sep=";", encoding="utf-8-sig")
    print(f"Tabela salva em {cache}")
    return quadro
