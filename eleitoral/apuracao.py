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


def _cargo(bruto: dict, codigo: str = "6") -> dict:
    cargos = bruto.get("carg") or []
    for cargo in cargos:
        if str(cargo.get("cd")) == str(codigo):
            return cargo
    if not cargos:
        nomes = {"5": "senador", "7": "deputado estadual"}
        nome = nomes.get(str(codigo), "deputado federal")
        raise ValueError(f"O arquivo do TSE não trouxe {nome}.")
    return cargos[0]


def _inteiro(valor: object) -> int:
    digitos = "".join(caractere for caractere in str(valor or "") if caractere.isdigit())
    return int(digitos) if digitos else 0


def _grupos(cargo: dict) -> list[dict]:
    federacoes = {str(item.get("n")): item for item in cargo.get("fed") or []}
    blocos: dict[str, dict] = {}
    for agrupamento in cargo.get("agr") or []:
        for partido in agrupamento.get("par") or []:
            nfed = str(partido.get("nfed") or "")
            votos = _inteiro(partido.get("tvtn"))
            votos_cadeiras = votos + _inteiro(partido.get("tval"))
            sigla = str(partido.get("sg") or "")
            if nfed:
                federacao = federacoes.get(nfed) or {}
                nome = str(federacao.get("sg") or federacao.get("com") or nfed)
                bloco = blocos.setdefault(
                    f"f:{nfed}",
                    {"nome": nome, "tipo": "federacao", "partidos": [], "votos": 0, "votosCadeiras": 0},
                )
                bloco["votos"] += votos
                bloco["votosCadeiras"] += votos_cadeiras
                if sigla and sigla not in bloco["partidos"]:
                    bloco["partidos"].append(sigla)
            elif sigla:
                blocos[f"p:{sigla}"] = {
                    "nome": sigla,
                    "tipo": "partido",
                    "partidos": [sigla],
                    "votos": votos,
                    "votosCadeiras": votos_cadeiras,
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


def cadeiras_no_instante(legendas: list[dict], candidatos: list[dict], qe: int, vagas: int) -> set[str]:
    """Quem levaria cadeira agora, pelas regras proporcionais de 2026.

    O quociente eleitoral chega pronto. A legenda usa votos válidos (nominal + legenda).
    O candidato entra pela votação nominal. A primeira fase preenche o quociente partidário
    com quem tem pelo menos 10% do quociente. As sobras seguem a média: primeiro a cláusula
    80/20 e, se ainda restar cadeira, todas as legendas, sem esse mínimo.
    """
    if qe <= 0 or vagas <= 0:
        return set()
    por_partido = {str(legenda["nome"]): legenda for legenda in legendas}
    partido_da_legenda: dict[str, str] = {}
    for legenda in legendas:
        for partido in legenda.get("partidos") or []:
            partido_da_legenda[str(partido)] = str(legenda["nome"])
    fila: dict[str, list[dict]] = {}
    for candidato in candidatos:
        legenda = partido_da_legenda.get(str(candidato.get("partido") or ""))
        if not legenda or legenda not in por_partido:
            continue
        fila.setdefault(legenda, []).append(candidato)
    for legenda, lista in fila.items():
        lista.sort(key=lambda item: (-int(item.get("votos") or 0), str(item.get("id"))))

    def alcança(votos: int, percentual: int) -> bool:
        return votos * 100 >= qe * percentual

    eleitos: set[str] = set()
    obtidas = {nome: 0 for nome in por_partido}

    def proximo(legenda: str, percentual: int | None) -> dict | None:
        for candidato in fila.get(legenda, []):
            if str(candidato["id"]) in eleitos:
                continue
            if percentual is None or alcança(int(candidato.get("votos") or 0), percentual):
                return candidato
        return None

    for nome, legenda in por_partido.items():
        quociente = int(legenda.get("votosCadeiras") or 0) // qe
        for _ in range(quociente):
            if len(eleitos) >= vagas:
                break
            candidato = proximo(nome, 10)
            if candidato is None:
                break
            eleitos.add(str(candidato["id"]))
            obtidas[nome] += 1

    def escolher(percentual_legenda: int | None, percentual_candidato: int | None) -> str | None:
        melhor: str | None = None
        for nome, legenda in por_partido.items():
            votos = int(legenda.get("votosCadeiras") or 0)
            if percentual_legenda is not None and not alcança(votos, percentual_legenda):
                continue
            if proximo(nome, percentual_candidato) is None:
                continue
            if melhor is None:
                melhor = nome
                continue
            atual = votos * (obtidas[melhor] + 1)
            anterior = int(por_partido[melhor].get("votosCadeiras") or 0) * (obtidas[nome] + 1)
            if atual > anterior or (atual == anterior and votos > int(por_partido[melhor].get("votosCadeiras") or 0)):
                melhor = nome
            elif atual == anterior and votos == int(por_partido[melhor].get("votosCadeiras") or 0) and nome < melhor:
                melhor = nome
        return melhor

    while len(eleitos) < vagas:
        nome = escolher(80, 20)
        if nome is None:
            break
        candidato = proximo(nome, 20)
        if candidato is None:
            break
        eleitos.add(str(candidato["id"]))
        obtidas[nome] += 1

    while len(eleitos) < vagas:
        nome = escolher(None, None)
        if nome is None:
            break
        candidato = proximo(nome, None)
        if candidato is None:
            break
        eleitos.add(str(candidato["id"]))
        obtidas[nome] += 1

    return eleitos


def _encontrar(pessoa: dict, por_sequencial: dict[str, dict], por_numero: dict[str, dict]) -> dict | None:
    sequencial = str(pessoa.get("sequencial2026") or "")
    if sequencial and sequencial in por_sequencial:
        return por_sequencial[sequencial]
    numero = str(pessoa.get("numero2026") or pessoa.get("numero") or "")
    return por_numero.get(numero)


def aplicar_snapshot(painel: dict, bruto: dict, codigo: str = "6") -> bool:
    """Grava votos2026, situação e quociente quando a totalização fechou.

    Devolve False sem alterar o painel enquanto ``and`` não for ``f``.
    O campo ``votos`` de 2022 permanece como estava.
    """
    if str(bruto.get("and") or "") != "f":
        return False
    cargo = _cargo(bruto, codigo)
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
