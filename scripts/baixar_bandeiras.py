"""Baixa bandeiras e logomarcas dos partidos usados no painel."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "painel" / "public" / "bandeiras"
ARQUIVOS = {
    "AGIR": "Logomarca do Partido Agir.png",
    "AVANTE": "Bandeira-partido-avante.png",
    "CIDADANIA": "Cidadania (Brasil) logo (variant 1).svg",
    "DC": "Bandeira-democracia-cristã.png",
    "MDB": "Movimento Democrático Brasileiro (2017).svg",
    "MISSÃO": "Bandeira do Partido Missão.svg",
    "MOBILIZA": "Bandeira Mobiliza.svg",
    "NOVO": "Partido Novo flag (2023).svg",
    "PATRIOTA": "Logotipo do partido Patriota.svg",
    "PC do B": "PCdoB flag.svg",
    "PCDOB": "PCdoB flag.svg",
    "PDT": "Bandeira.PDT.png",
    "PL": "Bandeira do Partido Liberal (Brasil).svg",
    "PODE": "Podemos (Brasil) logo.svg",
    "PP": "Progressistas (Brazil) logo.svg",
    "PROS": "Logomarca do Partido Republicano da Ordem Social (PROS), do Brasil.png",
    "PSB": "Logo of the Brazilian Socialist Party (wordmark color).svg",
    "PSC": "PSC logo(cortado).png",
    "PSD": "PSD Brazil logo.svg",
    "PSDB": "Logo of the Brazilian Social Democracy Party (2023).svg",
    "PSOL": "Bandeira Amarela-Roxa PSOL.png",
    "PSTU": "PSTU vetor.svg",
    "PT": "Bandeira do Partido dos Trabalhadores (2022).svg",
    "PTB": "PTB (2024) flag.jpg",
    "PV": "Bandeira Partido Verde Brasil.svg",
    "REDE": "Rede Sustentabilidade logo.svg",
    "REPUBLICANOS": "Republicanos logo.png",
    "SOLIDARIEDADE": "Solidariedade 77 (Brasil) logo.svg",
    "UNIÃO": "União Brasil logo.svg",
    "UP": "Logo - UP site.png",
}
DIRETOS = {
    "PMN": "https://www.camara.leg.br/internet/Deputado/img/partidos/PMN.gif",
    "REPUBLICANOS": "https://upload.wikimedia.org/wikipedia/pt/0/0d/Republicanos_logo.png",
    "UP": "https://upload.wikimedia.org/wikipedia/pt/0/00/Logo_-_UP_site.png",
}


def slug(sigla: str) -> str:
    texto = unicodedata.normalize("NFD", sigla)
    return "".join(caractere for caractere in texto if unicodedata.category(caractere) != "Mn").replace(" ", "")


def extensao(conteudo: bytes) -> str:
    if conteudo.startswith(b"\x89PNG"):
        return ".png"
    if conteudo.startswith(b"\xff\xd8"):
        return ".jpg"
    if conteudo.startswith(b"GIF"):
        return ".gif"
    if conteudo.startswith(b"<svg") or conteudo.startswith(b"<?xml"):
        return ".svg"
    return ""


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for antigo in DESTINO.glob("*"):
        if antigo.is_file():
            antigo.unlink()

    sessao = requests.Session()
    sessao.headers["User-Agent"] = "painel-amazonas/1.0 (local research)"
    titulos = sorted({f"File:{nome}" for nome in ARQUIVOS.values()})
    resposta = sessao.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "titles": "|".join(titulos),
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 320,
            "format": "json",
        },
        timeout=60,
    )
    resposta.raise_for_status()
    por_arquivo = {}
    for pagina in resposta.json()["query"]["pages"].values():
        if "missing" in pagina or "imageinfo" not in pagina:
            print("sem arquivo", pagina.get("title"))
            continue
        info = pagina["imageinfo"][0]
        por_arquivo[pagina["title"].removeprefix("File:")] = info.get("thumburl") or info["url"]

    mapa = {}
    baixados: dict[str, str] = {}
    for sigla, arquivo in ARQUIVOS.items():
        url = por_arquivo.get(arquivo)
        if not url:
            print("falta", sigla)
            continue
        nome = slug(sigla if sigla != "PCDOB" else "PCdoB")
        if arquivo in baixados:
            mapa[sigla] = baixados[arquivo]
            continue
        imagem = sessao.get(url, timeout=60)
        imagem.raise_for_status()
        sufixo = extensao(imagem.content)
        if not sufixo:
            print("formato", sigla, imagem.headers.get("content-type"))
            continue
        destino = DESTINO / f"{nome}{sufixo}"
        destino.write_bytes(imagem.content)
        caminho = f"/bandeiras/{destino.name}"
        baixados[arquivo] = caminho
        mapa[sigla] = caminho
        print("ok", sigla, destino.name, len(imagem.content))

    for sigla, url in DIRETOS.items():
        imagem = sessao.get(url, timeout=40)
        sufixo = extensao(imagem.content)
        if imagem.status_code != 200 or not sufixo:
            print("falta", sigla)
            continue
        destino = DESTINO / f"{slug(sigla)}{sufixo}"
        destino.write_bytes(imagem.content)
        mapa[sigla] = f"/bandeiras/{destino.name}"
        print("ok", sigla)

    (DESTINO / "mapa.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=2), encoding="utf-8")
    print("partidos", len(mapa))


if __name__ == "__main__":
    main()
