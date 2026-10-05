"""Gera o JSON e as fotos usados pelo painel do Amazonas."""

from __future__ import annotations

import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from eleitoral.analise import _preparar_chaves, comparar_disputas, cruzar_deputados, resumo_por_partido
from eleitoral.camara import carregar_deputados_atuais
from eleitoral.regras import eh_eleito, somente_digitos
from eleitoral.tse import carregar_candidatos, carregar_gastos_publicidade, carregar_votos

PAINEL = RAIZ / "painel" / "public"
DIVULGA_2026 = RAIZ / "dados" / "processados" / "divulga_despesas_2026_AM.json"
FOTOS_ELEITOS = PAINEL / "fotos" / "eleitos"
FOTOS_2026 = PAINEL / "fotos" / "2026"
ZIP_FOTOS = Path(r"C:\Users\Luiz\Downloads\foto_cand2026_AM_div.zip")
PARTICULAS = {"da", "de", "do", "das", "dos", "e", "por", "pela", "pelo"}


def exibir_nome(valor: object) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    partes = []
    for indice, parte in enumerate(texto.split()):
        baixa = parte.lower()
        if indice and baixa in PARTICULAS:
            partes.append(baixa)
        else:
            partes.append(baixa.capitalize())
    return " ".join(partes)


def exibir_resultado(valor: object) -> str:
    texto = str(valor or "").upper()
    if "MÉDIA" in texto or "MEDIA" in texto:
        return "Eleito pela média"
    if "QP" in texto:
        return "Eleito pelo quociente"
    return exibir_nome(valor)


# Votos válidos oficiais de deputado federal no Amazonas em 2022 (nominal + legenda).
VOTOS_VALIDOS_2022_AM = 1_991_796
VAGAS_DEPUTADO_FEDERAL_AM = 8
# Deputado estadual no Amazonas em 2022: 1.972.089 votos válidos e 24 cadeiras.
VOTOS_VALIDOS_ESTADUAL_2022_AM = 1_972_089
VAGAS_DEPUTADO_ESTADUAL_AM = 24
# Senador no Amazonas em 2022: uma cadeira, eleição majoritária.
VAGAS_SENADOR_2022_AM = 1
CORTE_UMA_SEMANA_2022 = date(2022, 9, 25)
URL_APURACAO = {
    5: "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/am/am-c0005-e006259-u.json",
    6: "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/am/am-c0006-e006259-u.json",
    7: "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/am/am-c0007-e006259-u.json",
}
ARQUIVO_VOTOS = {
    5: "votos_senador_2022_AM.csv",
    6: "votos_deputado_federal_2022_AM.csv",
    7: "votos_deputado_estadual_2022_AM.csv",
}
ARQUIVO_PAINEL = {
    5: "amazonas-senador.json",
    6: "amazonas.json",
    7: "amazonas-estadual.json",
}


def nota_quociente(cargo: int, votos_validos: int) -> str:
    milhar = f"{votos_validos:,}".replace(",", ".")
    if cargo == 5:
        return (
            f"Senador no Amazonas em 2022 é eleição majoritária: {milhar} votos nominais e 1 cadeira, "
            "para o mais votado. O quociente dos deputados não distribui essa vaga. "
            "A raia soma o voto nominal de cada partido."
        )
    if cargo == 7:
        return (
            "Quociente eleitoral de deputado estadual no Amazonas em 2022: "
            "1.972.089 votos válidos divididos por 24 cadeiras. A fração 0,375 é desprezada. "
            "Os 80% desse quociente eram o mínimo para o partido ou a federação disputar as sobras. "
            "A raia soma o voto nominal de cada federação e de cada partido que concorreu sozinho. "
            "O voto de legenda entra no quociente e não está separado nesta raia."
        )
    return (
        "Quociente eleitoral de deputado federal no Amazonas em 2022: "
        "1.991.796 votos válidos divididos por 8 cadeiras. A fração 0,5 é desprezada. "
        "Os 80% desse quociente eram o mínimo para o partido ou a federação disputar as sobras. "
        "A raia soma o voto nominal de cada federação e de cada partido que concorreu sozinho. "
        "O voto de legenda entra no quociente e não está separado nesta raia."
    )


def quociente_eleitoral(votos_validos: int, vagas: int) -> int:
    """Divisão do TSE: fração até 0,5 é desprezada; acima de 0,5, arredonda para cima."""
    quociente = votos_validos / vagas
    inteiro = int(quociente)
    if quociente - inteiro > 0.5:
        return inteiro + 1
    return inteiro


def montar_federacoes(caminho: Path) -> list[dict]:
    """Cada federação é um bloco. Partido fora de federação entra sozinho."""
    quadro = pd.read_csv(caminho, sep=";", dtype=str)
    quadro["votos"] = pd.to_numeric(quadro["votos"], errors="coerce").fillna(0).astype(int)
    quadro["federacao"] = quadro["federacao"].fillna("").str.strip()
    quadro["partido"] = quadro["partido"].fillna("").str.strip()
    vazios = {"", "#NULO", "#NULO#", "#NE", "#NE#", "-1"}

    def bloco(linha: pd.Series) -> tuple[str, str]:
        federacao = str(linha.federacao)
        if federacao not in vazios:
            return "federacao", federacao
        return "partido", str(linha.partido)

    quadro["tipo"] = quadro.apply(lambda linha: bloco(linha)[0], axis=1)
    quadro["nome"] = quadro.apply(lambda linha: bloco(linha)[1], axis=1)
    grupos = []
    for (tipo, nome), pedaco in quadro.groupby(["tipo", "nome"], sort=False):
        if not nome or nome in vazios:
            continue
        if tipo == "federacao":
            partidos = [parte.strip() for parte in nome.split("/") if parte.strip()]
        else:
            partidos = [nome]
        grupos.append(
            {
                "nome": nome,
                "tipo": tipo,
                "partidos": partidos,
                "votos": int(pedaco["votos"].sum()),
            }
        )
    grupos.sort(key=lambda item: (-item["votos"], item["nome"]))
    acumulado = 0
    for item in grupos:
        item["inicio"] = acumulado
        acumulado += item["votos"]
        item["fim"] = acumulado
    return grupos


def ler_coluna(caminho: Path, coluna: str) -> dict[str, float]:
    quadro = pd.read_csv(caminho, sep=";", dtype={"sequencial": str})
    return {str(linha.sequencial): float(getattr(linha, coluna) or 0) for linha in quadro.itertuples(index=False)}


def sequencial_no_destino(origem: pd.DataFrame, destino: pd.DataFrame) -> dict[str, str]:
    anterior = _preparar_chaves(origem)
    atual = _preparar_chaves(destino)

    def indice(quadro: pd.DataFrame, coluna: str) -> pd.Series:
        base = quadro.loc[quadro[coluna].astype(str).ne("")].drop_duplicates(coluna)
        return base.set_index(coluna)["sequencial"].astype(str)

    por_titulo = indice(atual, "titulo_limpo")
    por_cpf = indice(atual, "cpf_limpo")
    com_nome = atual.loc[atual["nome_chave"].ne("") & atual["nasc_chave"].ne("")].copy()
    com_nome["chave"] = list(zip(com_nome["uf_chave"], com_nome["nome_chave"], com_nome["nasc_chave"]))
    por_nome = indice(com_nome, "chave") if not com_nome.empty else pd.Series(dtype=object)
    achado = anterior["titulo_limpo"].map(por_titulo)
    achado = achado.fillna(anterior["cpf_limpo"].map(por_cpf))
    chaves = pd.Series(
        list(zip(anterior["uf_chave"], anterior["nome_chave"], anterior["nasc_chave"])),
        index=anterior.index,
    )
    achado = achado.fillna(chaves.map(por_nome))
    return {
        str(origem_seq): str(destino_seq)
        for origem_seq, destino_seq in zip(anterior["sequencial"].astype(str), achado.fillna(""))
        if destino_seq
    }


def pessoa(linha, foto: str = "") -> dict:
    return {
        "nome": exibir_nome(linha.get("nome", "")),
        "nomeUrna": exibir_nome(linha.get("nome_urna", "") or linha.get("nome", "")),
        "partido": str(linha.get("partido", "")),
        "numero": str(linha.get("numero", "")),
        "foto": foto,
    }


def baixar_foto(url: str, destino: Path) -> bool:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 1000:
        return True
    try:
        resposta = requests.get(url, timeout=40, headers={"User-Agent": "painel-amazonas"})
        resposta.raise_for_status()
        if not resposta.content.startswith(b"\xff\xd8") and not resposta.content.startswith(b"\x89PNG"):
            return False
        destino.write_bytes(resposta.content)
        return True
    except requests.RequestException:
        return False


def copiar_fotos_2026(sequenciais: set[str]) -> dict[str, str]:
    caminhos: dict[str, str] = {}
    if not ZIP_FOTOS.exists():
        return caminhos
    FOTOS_2026.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_FOTOS) as arquivo:
        for nome in arquivo.namelist():
            base = Path(nome).name
            if not base.upper().startswith("FAM") or not base.lower().endswith(".jpg"):
                continue
            sequencial = "".join(caractere for caractere in base if caractere.isdigit())
            if sequencial not in sequenciais:
                continue
            destino = FOTOS_2026 / f"{sequencial}.jpg"
            if not destino.exists():
                destino.write_bytes(arquivo.read(nome))
            caminhos[sequencial] = f"/fotos/2026/{sequencial}.jpg"
    return caminhos


def main(cargo: int = 6) -> None:
    cargo = int(cargo) if int(cargo) in (5, 6, 7) else 6
    federal = cargo == 6
    senador = cargo == 5
    candidatos_2022 = carregar_candidatos(2022, uf="AM", cargo=cargo)
    candidatos_2026 = carregar_candidatos(2026, uf="AM", cargo=cargo)
    deputados = carregar_deputados_atuais(uf="AM") if federal else None
    comparacao = comparar_disputas(candidatos_2022, candidatos_2026)
    cruzamento = cruzar_deputados(deputados, candidatos_2026) if federal else None

    fotos_2026 = copiar_fotos_2026(set(candidatos_2026["sequencial"].astype(str)))
    deputados_por_cpf = {}
    if deputados is not None:
        deputados_por_cpf = {
            somente_digitos(linha.cpf): linha for linha in deputados.itertuples(index=False)
        }
    partido_2026 = {
        str(linha.sequencial): str(linha.partido_2026)
        for linha in comparacao.continuam.itertuples(index=False)
    }
    arquivo_votos = RAIZ / "dados" / "processados" / ARQUIVO_VOTOS[cargo]
    carregar_votos(candidatos_2022, uf="AM", cargo=cargo)
    votos = ler_coluna(arquivo_votos, "votos")
    federacoes = montar_federacoes(arquivo_votos)
    if senador:
        votos_validos = int(sum(votos.values()))
        vagas = VAGAS_SENADOR_2022_AM
    elif cargo == 7:
        votos_validos = VOTOS_VALIDOS_ESTADUAL_2022_AM
        vagas = VAGAS_DEPUTADO_ESTADUAL_AM
    else:
        votos_validos = VOTOS_VALIDOS_2022_AM
        vagas = VAGAS_DEPUTADO_FEDERAL_AM
    qe = quociente_eleitoral(votos_validos, vagas)
    oitenta = round(qe * 0.8)
    gastos_2022 = carregar_gastos_publicidade(2022, candidatos_2022, uf="AM", somente_publicidade=False, cargo=cargo)
    gastos_ate_semana = carregar_gastos_publicidade(
        2022,
        candidatos_2022,
        data_corte=CORTE_UMA_SEMANA_2022,
        uf="AM",
        somente_publicidade=False,
        cargo=cargo,
    )
    gastos_2026 = carregar_gastos_publicidade(2026, candidatos_2026, uf="AM", somente_publicidade=False, cargo=cargo)
    gasto_2022 = {
        str(linha.sequencial): float(linha.gasto_publicidade)
        for linha in gastos_2022.por_candidato.itertuples(index=False)
    }
    gasto_ate_semana = {
        str(linha.sequencial): float(linha.gasto_publicidade)
        for linha in gastos_ate_semana.por_candidato.itertuples(index=False)
    }
    gasto_2026 = {
        str(linha.sequencial): float(linha.gasto_publicidade)
        for linha in gastos_2026.por_candidato.itertuples(index=False)
    }
    nota_2026 = (
        "Mesma soma, só com despesa datada. O arquivo do TSE foi gerado em 04/09/2026 "
        "e o período datado vai até 03/09/2026. Lançamentos sem data ficaram de fora."
    )
    if federal and DIVULGA_2026.exists():
        divulga = json.loads(DIVULGA_2026.read_text(encoding="utf-8"))
        gasto_2026 = {str(item["sequencial"]): float(item["total"]) for item in divulga["candidatos"]}
        nota_2026 = str(divulga["nota"])
    seq_2026 = sequencial_no_destino(candidatos_2022, candidatos_2026)
    seq_2022 = sequencial_no_destino(candidatos_2026, candidatos_2022)
    ficha_2026 = {str(linha.sequencial): linha for linha in candidatos_2026.itertuples(index=False)}

    eleitos = []
    for linha in candidatos_2022.loc[candidatos_2022["resultado"].map(eh_eleito)].itertuples(index=False):
        deputado = deputados_por_cpf.get(somente_digitos(linha.cpf))
        foto = ""
        partido_atual = str(linha.partido)
        if deputado is not None:
            partido_atual = str(deputado.partido)
            arquivo = FOTOS_ELEITOS / f"{deputado.id}.jpg"
            url = f"https://www.camara.leg.br/internet/deputado/bandep/{deputado.id}.jpg"
            if baixar_foto(url, arquivo):
                foto = f"/fotos/eleitos/{deputado.id}.jpg"
        if not foto:
            foto = fotos_2026.get(seq_2026.get(str(linha.sequencial), ""), "")
        registro = pessoa(linha._asdict(), foto)
        if deputado is not None:
            registro["nomeUrna"] = exibir_nome(deputado.nome)
            registro["nome"] = exibir_nome(deputado.nome_civil or linha.nome)
        registro.update(
            {
                "resultado": exibir_resultado(linha.resultado),
                "partidoAtual": partido_atual,
                "partido2026": partido_2026.get(str(linha.sequencial), ""),
                "concorre2026": str(linha.sequencial) in partido_2026,
                "votos": int(votos.get(str(linha.sequencial), 0)),
                "gasto2022": round(gasto_2022.get(str(linha.sequencial), 0.0), 2),
                "gasto2026": round(gasto_2026.get(seq_2026.get(str(linha.sequencial), ""), 0.0), 2),
            }
        )
        eleitos.append(registro)
    eleitos.sort(key=lambda item: item["votos"], reverse=True)
    fotos_eleitos = {item["numero"]: item["foto"] for item in eleitos}

    def linha_desempenho(linha, disputou_2022: bool) -> dict:
        sequencial = str(linha.sequencial)
        if disputou_2022:
            outro = seq_2026.get(sequencial, "")
            ficha = ficha_2026.get(outro) if outro else None
            registro = pessoa(linha._asdict(), fotos_eleitos.get(str(linha.numero), "") or fotos_2026.get(outro, ""))
            registro.update(
                {
                    "disputou2022": True,
                    "eleito": eh_eleito(linha.resultado),
                    "votos": int(votos.get(sequencial, 0)),
                    "gasto2022": round(gasto_2022.get(sequencial, 0.0), 2),
                    "gastoAteSemana": round(gasto_ate_semana.get(sequencial, 0.0), 2),
                    "gasto2026": round(gasto_2026.get(outro, 0.0), 2) if outro else None,
                    "concorre2026": bool(outro),
                    "partido2026": str(ficha.partido) if ficha is not None else "",
                    "numero2026": str(ficha.numero) if ficha is not None else "",
                    "sequencial2026": str(ficha.sequencial) if ficha is not None else "",
                }
            )
            return registro
        registro = pessoa(linha._asdict(), fotos_2026.get(sequencial, ""))
        registro.update(
            {
                "disputou2022": False,
                "eleito": False,
                "votos": None,
                "gasto2022": None,
                "gasto2026": round(gasto_2026.get(sequencial, 0.0), 2),
                "concorre2026": True,
                "partido2026": str(linha.partido),
                "numero2026": str(linha.numero),
                "sequencial2026": sequencial,
            }
        )
        return registro

    desempenho = [linha_desempenho(linha, True) for linha in candidatos_2022.itertuples(index=False)]
    desempenho.extend(
        linha_desempenho(linha, False)
        for linha in candidatos_2026.itertuples(index=False)
        if str(linha.sequencial) not in seq_2022
    )
    desempenho.sort(key=lambda item: (item["votos"] is None, -(item["votos"] or 0), item["nomeUrna"]))

    gasto_partido_2026: dict[str, float] = {}
    for linha in candidatos_2026.itertuples(index=False):
        sigla = str(linha.partido)
        gasto_partido_2026[sigla] = gasto_partido_2026.get(sigla, 0.0) + gasto_2026.get(str(linha.sequencial), 0.0)
    gasto_partido_2022 = {}
    for linha in candidatos_2022.itertuples(index=False):
        sigla = str(linha.partido)
        gasto_partido_2022[sigla] = gasto_partido_2022.get(sigla, 0.0) + gasto_2022.get(str(linha.sequencial), 0.0)
    publicidade_partidos = []
    for sigla in sorted(
        set(gasto_partido_2022) | set(gasto_partido_2026),
        key=lambda item: (-(gasto_partido_2022.get(item, 0) + gasto_partido_2026.get(item, 0)), item),
    ):
        publicidade_partidos.append(
            {
                "partido": sigla,
                "gasto2022": round(gasto_partido_2022.get(sigla, 0.0), 2),
                "gasto2026": round(gasto_partido_2026.get(sigla, 0.0), 2),
            }
        )

    contagem_2022 = {
        str(linha.partido): int(linha.candidatos)
        for linha in resumo_por_partido(candidatos_2022).itertuples(index=False)
    }
    contagem_2026 = {
        str(linha.partido): int(linha.candidatos)
        for linha in resumo_por_partido(candidatos_2026).itertuples(index=False)
    }
    partidos = []
    for sigla in sorted(set(contagem_2022) | set(contagem_2026), key=lambda item: (-(contagem_2022.get(item, 0) + contagem_2026.get(item, 0)), item)):
        partidos.append(
            {
                "partido": sigla,
                "candidatos2022": contagem_2022.get(sigla, 0),
                "candidatos2026": contagem_2026.get(sigla, 0),
            }
        )

    def lista(quadro, ano_foto: str = "") -> list[dict]:
        registros = []
        for linha in quadro.itertuples(index=False):
            foto = ""
            if ano_foto == "2026":
                foto = fotos_2026.get(str(linha.sequencial), "")
            registros.append(pessoa(linha._asdict(), foto))
        return registros

    trocas = []
    for linha in comparacao.mudaram_de_partido.itertuples(index=False):
        trocas.append(
            {
                "nomeUrna": exibir_nome(linha.nome_urna),
                "nome": exibir_nome(linha.nome),
                "partido2022": str(linha.partido_2022),
                "partido2026": str(linha.partido_2026),
            }
        )

    fora = []
    if not federal:
        for item in eleitos:
            if item["concorre2026"]:
                continue
            fora.append({"nome": item["nome"], "partido": item["partidoAtual"], "foto": item["foto"]})
    else:
        for linha in cruzamento.fora_da_disputa_2026.itertuples(index=False):
            arquivo = FOTOS_ELEITOS / f"{linha.id}.jpg"
            foto = f"/fotos/eleitos/{linha.id}.jpg" if arquivo.exists() else ""
            fora.append(
                {
                    "nome": exibir_nome(linha.nome),
                    "partido": str(linha.partido),
                    "foto": foto,
                }
            )

    payload = {
        "uf": "AM",
        "estado": "Amazonas",
        "totais": {
            "candidatos2022": int(len(candidatos_2022)),
            "candidatos2026": int(len(candidatos_2026)),
            "eleitos2022": len(eleitos),
            "deputados": len(eleitos) if deputados is None else int(len(deputados)),
            "sairam": int(len(comparacao.sairam)),
            "entraram": int(len(comparacao.entraram)),
            "continuam": int(len(comparacao.continuam)),
            "trocaramPartido": len(trocas),
            "votos2022": int(sum(votos.values())),
            "publicidade2022": round(sum(gasto_2022.values()), 2),
            "publicidade2026": round(sum(gasto_2026.values()), 2),
        },
        "eleitos": eleitos,
        "desempenho": desempenho,
        "publicidadePartidos": publicidade_partidos,
        "notaVotos": "Votos nominais do primeiro turno da eleição ordinária de 2022.",
        "notaPublicidade2022": "Soma de todas as despesas contratadas da campanha, de qualquer tipo. Prestação de contas de 2022, arquivo gerado pelo TSE em 16/11/2025.",
        "notaGastoAntecipado": (
            "Despesas contratadas com data até 25/09/2022, inclusive, uma semana antes do primeiro turno de 02/10/2022. "
            "A porcentagem divide esse valor pelo total final da mesma prestação de contas. "
            "Quem fechou a campanha com despesa zero fica fora do gráfico."
        ),
        "notaPublicidade2026": nota_2026,
        "quociente": {
            "votosValidos": votos_validos,
            "vagas": vagas,
            "qe": qe,
            "oitenta": oitenta,
            "nota": nota_quociente(cargo, votos_validos),
        },
        "federacoes": federacoes,
        "partidos": partidos,
        "sairam": lista(comparacao.sairam),
        "entraram": lista(comparacao.entraram, "2026"),
        "trocas": trocas,
        "foraDaDisputa": fora,
        "notaFotos2026": "As fotos de 2026 vêm do arquivo oficial foto_cand2026_AM divulgado pelo TSE.",
        "notaEleitos": (
            "As fotos dos eleitos são as oficiais da Câmara dos Deputados."
            if federal
            else "Os eleitos são os que o TSE marcou como eleitos em 2022."
        ),
        "cargo": {5: "senador", 7: "estadual"}.get(cargo, "federal"),
        "codigoCargo": str(cargo),
        "rotulo": {5: "Senador", 7: "Deputado estadual"}.get(cargo, "Deputado federal"),
        "majoritario": senador,
        "apuracaoUrl": URL_APURACAO[cargo],
    }
    destino = PAINEL / "dados" / ARQUIVO_PAINEL[cargo]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON: {destino}")
    print(f"Eleitos com foto: {sum(1 for item in eleitos if item['foto'])}/{len(eleitos)}")
    print(f"Fotos 2026: {len(fotos_2026)}")
    if federal:
        amom = next(item for item in desempenho if item.get("gastoAteSemana") and "Amom" in item["nomeUrna"])
        print(
            f"Amom ate 25/09: {amom['gastoAteSemana']:.2f} de {amom['gasto2022']:.2f} "
            f"({amom['gastoAteSemana'] / amom['gasto2022'] * 100:.2f}%)"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--estadual", action="store_true")
    parser.add_argument("--senador", action="store_true")
    args = parser.parse_args()
    if args.senador:
        main(5)
    elif args.estadual:
        main(7)
    else:
        main(6)
