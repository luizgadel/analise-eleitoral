"""Apuração ao vivo de deputado federal em 2026, a partir do JSON unificado do TSE."""

from __future__ import annotations

from eleitoral.regras import normalizar_texto

URL_APURACAO_2026 = (
    "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/am/am-c0006-e006259-u.json"
)


def voto_valido(candidato: dict) -> int:
    """Conta o vap só quando a destinação é voto válido, sem anulação e sem legenda."""
    destinacao = normalizar_texto(candidato.get("dvt"))
    if "VALIDO" not in destinacao or "ANULADO" in destinacao or "LEGENDA" in destinacao:
        return 0
    digitos = "".join(caractere for caractere in str(candidato.get("vap") or "") if caractere.isdigit())
    return int(digitos) if digitos else 0


def _cargo(bruto: dict) -> dict:
    cargos = bruto.get("carg") or []
    for cargo in cargos:
        if str(cargo.get("cd")) == "6":
            return cargo
    if not cargos:
        raise ValueError("O arquivo do TSE não trouxe deputado federal.")
    return cargos[0]


def _grupos(cargo: dict) -> list[dict]:
    federacoes = {str(item.get("n")): item for item in cargo.get("fed") or []}
    blocos: dict[str, dict] = {}
    for agrupamento in cargo.get("agr") or []:
        for partido in agrupamento.get("par") or []:
            nfed = str(partido.get("nfed") or "")
            votos = int("".join(c for c in str(partido.get("tvtn") or "0") if c.isdigit()) or "0")
            sigla = str(partido.get("sg") or "")
            if nfed:
                federacao = federacoes.get(nfed) or {}
                nome = str(federacao.get("sg") or federacao.get("com") or nfed)
                bloco = blocos.setdefault(
                    f"f:{nfed}",
                    {"nome": nome, "tipo": "federacao", "partidos": [], "votos": 0},
                )
                bloco["votos"] += votos
                if sigla and sigla not in bloco["partidos"]:
                    bloco["partidos"].append(sigla)
            elif sigla:
                blocos[f"p:{sigla}"] = {
                    "nome": sigla,
                    "tipo": "partido",
                    "partidos": [sigla],
                    "votos": votos,
                }
    grupos = sorted(blocos.values(), key=lambda item: (-item["votos"], item["nome"]))
    acumulado = 0
    for item in grupos:
        item["inicio"] = acumulado
        acumulado += item["votos"]
        item["fim"] = acumulado
    return grupos


def _indice(cargo: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    por_sequencial: dict[str, dict] = {}
    por_numero: dict[str, dict] = {}
    for agrupamento in cargo.get("agr") or []:
        for partido in agrupamento.get("par") or []:
            for candidato in partido.get("cand") or []:
                ficha = {
                    "sequencial": str(candidato.get("sqcand") or ""),
                    "numero": str(candidato.get("n") or ""),
                    "votos": voto_valido(candidato),
                    "percentual": str(candidato.get("pvap") or ""),
                    "eleito": str(candidato.get("e") or "") == "s",
                    "situacao": str(candidato.get("st") or ""),
                }
                if ficha["sequencial"]:
                    por_sequencial[ficha["sequencial"]] = ficha
                if ficha["numero"]:
                    por_numero[ficha["numero"]] = ficha
    return por_sequencial, por_numero


def _encontrar(pessoa: dict, por_sequencial: dict[str, dict], por_numero: dict[str, dict]) -> dict | None:
    sequencial = str(pessoa.get("sequencial2026") or "")
    if sequencial and sequencial in por_sequencial:
        return por_sequencial[sequencial]
    numero = str(pessoa.get("numero2026") or pessoa.get("numero") or "")
    return por_numero.get(numero)


def aplicar_snapshot(painel: dict, bruto: dict) -> bool:
    """Grava votos2026, situação e quociente quando a totalização fechou.

    Devolve False sem alterar o painel enquanto ``and`` não for ``f``.
    O campo ``votos`` de 2022 permanece como estava.
    """
    if str(bruto.get("and") or "") != "f":
        return False
    cargo = _cargo(bruto)
    por_sequencial, por_numero = _indice(cargo)
    for pessoa in painel.get("desempenho") or []:
        if not pessoa.get("concorre2026"):
            continue
        votos_2022 = pessoa.get("votos")
        ficha = _encontrar(pessoa, por_sequencial, por_numero)
        if ficha is None:
            pessoa["votos2026"] = None
            pessoa["situacao2026"] = ""
            pessoa["eleito2026"] = False
        else:
            pessoa["votos2026"] = ficha["votos"]
            pessoa["situacao2026"] = ficha["situacao"]
            pessoa["eleito2026"] = ficha["eleito"]
        if pessoa.get("votos") != votos_2022:
            raise RuntimeError("O snapshot alterou os votos de 2022.")
    qe = int("".join(c for c in str(cargo.get("qe") or "0") if c.isdigit()) or "0")
    secoes = bruto.get("s") or {}
    painel["quociente2026"] = {
        "qe": qe,
        "oitenta": round(qe * 0.8),
        "vagas": int("".join(c for c in str(cargo.get("nv") or "0") if c.isdigit()) or "0"),
        "votosNominais": int("".join(c for c in str((bruto.get("v") or {}).get("vnom") or "0") if c.isdigit()) or "0"),
        "carimbo": f"{bruto.get('dt') or ''} {bruto.get('ht') or ''}".strip(),
        "secoes": {
            "pst": str(secoes.get("pst") or ""),
            "st": str(secoes.get("st") or ""),
            "ts": str(secoes.get("ts") or ""),
        },
        "federacoes": _grupos(cargo),
    }
    return True
