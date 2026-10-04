"""Download e leitura dos CSVs abertos do TSE."""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from eleitoral.config import (
    COLUNAS_CANDIDATOS,
    COLUNAS_DESPESAS,
    COLUNAS_EXIBICAO_CANDIDATO,
    COLUNAS_VOTOS,
    DATA_CORTE_2026,
    DIR_BRUTOS,
    DIR_PROCESSADOS,
    RENOMEAR_CANDIDATO,
    TAMANHO_PEDACO,
    URL_CANDIDATOS,
    URL_CONTAS,
    URL_VOTOS_2022,
    USER_AGENT,
)
from eleitoral.regras import (
    escolher_coluna_tipo,
    escolher_csvs,
    detectar_encoding,
    eh_publicidade,
    formatar_data,
    formatar_inteiro,
    formatar_reais,
    limpar_codigo,
    normalizar_texto,
    parse_inteiro,
    parse_valor,
    somente_digitos,
)


class ErroFonte(RuntimeError):
    """Falha ao obter ou interpretar um arquivo oficial."""


def _url_arquivo_historico(url: str) -> str | None:
    """Cópia crua no Internet Archive quando o CDN do TSE recusa o acesso."""
    try:
        resposta = requests.get(
            "https://archive.org/wayback/available",
            params={"url": url},
            headers={"User-Agent": USER_AGENT},
            timeout=40,
        )
        resposta.raise_for_status()
        snapshot = resposta.json().get("archived_snapshots", {}).get("closest", {})
    except (requests.RequestException, ValueError):
        return None
    if not snapshot.get("available") or not snapshot.get("url"):
        return None
    # if_ devolve o arquivo original. id_ redireciona capturas grandes
    # para uma cópia mais antiga e incompleta do mesmo endereço.
    return re.sub(
        r"(https?://web\.archive\.org/web/\d+)/",
        r"\1if_/",
        snapshot["url"],
        count=1,
    )


def _gravar_download(resposta: requests.Response, destino: Path) -> None:
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    total = int(resposta.headers.get("Content-Length") or 0)
    baixado = 0
    with parcial.open("wb") as arquivo:
        for bloco in resposta.iter_content(chunk_size=1024 * 1024):
            if not bloco:
                continue
            arquivo.write(bloco)
            baixado += len(bloco)
            if total:
                print(f"\rBaixando {destino.name}: {baixado / total:.0%}", end="", flush=True)
    if total:
        print()
    with parcial.open("rb") as verificacao:
        cabecalho = verificacao.read(2)
    if cabecalho != b"PK":
        parcial.unlink(missing_ok=True)
        raise ErroFonte(f"O download de {destino.name} não veio como arquivo zip.")
    parcial.replace(destino)


def baixar_arquivo(url: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0:
        print(f"Arquivo local: {destino.name}")
        return destino

    cabecalhos = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Referer": "https://dadosabertos.tse.jus.br/",
    }
    ultimo_erro: Exception | None = None
    for tentativa in range(1, 4):
        try:
            with requests.get(url, headers=cabecalhos, stream=True, timeout=180) as resposta:
                if resposta.status_code == 403:
                    copia = _url_arquivo_historico(url)
                    if copia is None:
                        raise ErroFonte(
                            "O TSE recusou o download (403). "
                            f"Baixe manualmente {url} e salve o arquivo em {destino}."
                        )
                    print("O TSE recusou o download. Usando a cópia pública do Internet Archive.")
                    with requests.get(copia, headers=cabecalhos, stream=True, timeout=180) as arquivo_copia:
                        arquivo_copia.raise_for_status()
                        _gravar_download(arquivo_copia, destino)
                else:
                    resposta.raise_for_status()
                    _gravar_download(resposta, destino)
            print(f"Download concluído: {destino.name} ({destino.stat().st_size / 1024 / 1024:.1f} MB)")
            return destino
        except ErroFonte:
            destino.with_suffix(destino.suffix + ".parcial").unlink(missing_ok=True)
            raise
        except requests.RequestException as erro:
            ultimo_erro = erro
            destino.with_suffix(destino.suffix + ".parcial").unlink(missing_ok=True)
            print(f"Tentativa {tentativa} falhou: {erro}")
    raise ErroFonte(f"Não foi possível baixar {url}.") from ultimo_erro


def _carimbo(origem: Path) -> str:
    estatistica = origem.stat()
    return f"{estatistica.st_size}:{estatistica.st_mtime_ns}"


def _cache_valido(cache: Path, origem: Path) -> bool:
    carimbo = cache.with_suffix(cache.suffix + ".carimbo")
    return cache.exists() and carimbo.exists() and carimbo.read_text(encoding="utf-8").strip() == _carimbo(origem)


def _gravar_cache(quadro: pd.DataFrame, cache: Path, origem: Path) -> None:
    cache.parent.mkdir(parents=True, exist_ok=True)
    quadro.to_csv(cache, index=False, sep=";", encoding="utf-8-sig")
    cache.with_suffix(cache.suffix + ".carimbo").write_text(_carimbo(origem), encoding="utf-8")
    print(f"Tabela salva em {cache}")


def _ler_cache(cache: Path) -> pd.DataFrame:
    print(f"Lendo tabela já processada: {cache.name}")
    return pd.read_csv(cache, sep=";", dtype=str, encoding="utf-8-sig", keep_default_na=False)


def _abrir_zip(caminho: Path) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(caminho)
    except zipfile.BadZipFile as erro:
        raise ErroFonte(
            f"O arquivo {caminho.name} está incompleto ou corrompido. Apague-o e execute a célula de novo."
        ) from erro


def _encoding_do_membro(arquivo_zip: zipfile.ZipFile, nome: str) -> str:
    with arquivo_zip.open(nome) as membro:
        return detectar_encoding(membro.read(2_000_000))


def _cabecalho(arquivo_zip: zipfile.ZipFile, nome: str, encoding: str) -> list[str]:
    with arquivo_zip.open(nome) as membro:
        linha = io.TextIOWrapper(membro, encoding=encoding, newline="").readline()
    return [coluna.strip().strip('"') for coluna in linha.rstrip("\r\n").split(";")]


def _iterar_csv(arquivo_zip: zipfile.ZipFile, nome: str, colunas: list[str]):
    encoding = _encoding_do_membro(arquivo_zip, nome)
    disponiveis = set(_cabecalho(arquivo_zip, nome, encoding))
    usar = [coluna for coluna in colunas if coluna in disponiveis]
    if not usar:
        raise ErroFonte(f"Nenhuma coluna esperada em {nome}. Colunas: {sorted(disponiveis)[:12]}")
    membro = arquivo_zip.open(nome)
    texto = io.TextIOWrapper(membro, encoding=encoding, newline="")
    try:
        leitor = pd.read_csv(
            texto,
            sep=";",
            dtype=str,
            usecols=usar,
            chunksize=TAMANHO_PEDACO,
            keep_default_na=False,
        )
        for pedaco in leitor:
            yield pedaco, disponiveis
    finally:
        texto.close()


def _limpar_serie(serie: pd.Series) -> pd.Series:
    return serie.map(limpar_codigo)


def _padronizar_candidato(quadro: pd.DataFrame) -> pd.DataFrame:
    renomear = {origem: destino for origem, destino in RENOMEAR_CANDIDATO.items() if origem in quadro.columns}
    quadro = quadro.rename(columns=renomear)
    for coluna in quadro.columns:
        if quadro[coluna].dtype == object or str(quadro[coluna].dtype) == "string":
            quadro[coluna] = quadro[coluna].map(limpar_codigo)
    if "nome_urna" in quadro.columns and "nome" in quadro.columns:
        vazio = quadro["nome_urna"].eq("")
        quadro.loc[vazio, "nome_urna"] = quadro.loc[vazio, "nome"]
    if "partido" in quadro.columns:
        quadro.loc[quadro["partido"].eq(""), "partido"] = "(sem sigla)"
    if "sequencial" not in quadro.columns:
        raise ErroFonte("O arquivo de candidatos não tem a coluna SQ_CANDIDATO.")
    quadro = quadro.drop_duplicates(subset=["sequencial"]).reset_index(drop=True)
    ordenacao = [coluna for coluna in ("partido", "uf", "nome_urna") if coluna in quadro.columns]
    if ordenacao:
        quadro = quadro.sort_values(ordenacao, kind="stable").reset_index(drop=True)
    return quadro


def _codigo_igual(serie: pd.Series, esperado: str) -> pd.Series:
    return serie.map(somente_digitos).str.lstrip("0").eq(esperado)


def _cargo_tse(cargo: int) -> tuple[str, str, str]:
    if int(cargo) == 7:
        return "7", "DEPUTADO ESTADUAL", "deputado_estadual"
    return "6", "DEPUTADO FEDERAL", "deputado_federal"


def _mascara_cargo(pedaco: pd.DataFrame, cargo: int = 6) -> pd.Series:
    codigo, descricao, _slug = _cargo_tse(cargo)
    if "CD_CARGO" in pedaco.columns and pedaco["CD_CARGO"].map(limpar_codigo).ne("").any():
        return _codigo_igual(pedaco["CD_CARGO"], codigo)
    if "DS_CARGO" in pedaco.columns:
        return pedaco["DS_CARGO"].map(normalizar_texto).eq(descricao)
    return pd.Series(True, index=pedaco.index)


def _mascara_deputado_federal(pedaco: pd.DataFrame) -> pd.Series:
    return _mascara_cargo(pedaco, 6)


def _mascara_ordinaria(pedaco: pd.DataFrame) -> pd.Series:
    if "NM_TIPO_ELEICAO" in pedaco.columns and pedaco["NM_TIPO_ELEICAO"].map(limpar_codigo).ne("").any():
        tipo = pedaco["NM_TIPO_ELEICAO"].map(normalizar_texto)
        return tipo.str.contains("ORDIN", na=False)
    if "CD_TIPO_ELEICAO" in pedaco.columns and pedaco["CD_TIPO_ELEICAO"].map(limpar_codigo).ne("").any():
        return _codigo_igual(pedaco["CD_TIPO_ELEICAO"], "2")
    return pd.Series(True, index=pedaco.index)


def _mascara_turno(pedaco: pd.DataFrame) -> pd.Series:
    if "NR_TURNO" not in pedaco.columns:
        return pd.Series(True, index=pedaco.index)
    turno = pedaco["NR_TURNO"].map(limpar_codigo)
    return turno.eq("") | turno.eq("1")


def _uf(valor: str | None) -> str | None:
    if valor is None or not str(valor).strip():
        return None
    return str(valor).strip().upper()


def _mascara_uf(pedaco: pd.DataFrame, uf: str | None, coluna: str = "SG_UF") -> pd.Series:
    if uf is None or coluna not in pedaco.columns:
        return pd.Series(True, index=pedaco.index)
    return pedaco[coluna].map(limpar_codigo).str.upper().eq(uf)


def _filtrar_candidatos(
    pedaco: pd.DataFrame, ano: int, somente_aptos: bool, uf: str | None = None, cargo: int = 6
) -> pd.DataFrame:
    mascara = _mascara_cargo(pedaco, cargo) & _mascara_ordinaria(pedaco) & _mascara_turno(pedaco)
    mascara = mascara & _mascara_uf(pedaco, uf)
    if "ANO_ELEICAO" in pedaco.columns:
        ano_texto = pedaco["ANO_ELEICAO"].map(limpar_codigo)
        mascara = mascara & (ano_texto.eq("") | ano_texto.eq(str(ano)))
    if somente_aptos and "DS_SITUACAO_CANDIDATURA" in pedaco.columns:
        situacao = pedaco["DS_SITUACAO_CANDIDATURA"].map(normalizar_texto)
        mascara = mascara & (situacao.eq("") | situacao.eq("APTO"))
    return pedaco.loc[mascara]


def candidatos_do_arquivo(
    caminho: Path, ano: int, somente_aptos: bool = True, uf: str | None = None, cargo: int = 6
) -> pd.DataFrame:
    uf = _uf(uf)
    quadros: list[pd.DataFrame] = []
    with _abrir_zip(caminho) as arquivo_zip:
        nomes = escolher_csvs(arquivo_zip.namelist(), "consulta_cand", uf=uf)
        if not nomes:
            raise ErroFonte(
                f"{caminho.name} não contém consulta de candidatos. Arquivos: {arquivo_zip.namelist()[:8]}"
            )
        for nome in nomes:
            print(f"Lendo {Path(nome).name}")
            for pedaco, _disponiveis in _iterar_csv(arquivo_zip, nome, COLUNAS_CANDIDATOS):
                filtrado = _filtrar_candidatos(pedaco, ano, somente_aptos, uf=uf, cargo=cargo)
                if not filtrado.empty:
                    quadros.append(filtrado)
    if not quadros:
        aviso = ""
        if somente_aptos:
            aviso = " Se a situação da candidatura vier com outro rótulo, use carregar_candidatos(ano, somente_aptos=False)."
        _codigo, descricao, _slug = _cargo_tse(cargo)
        raise ErroFonte(f"Nenhum candidato a {descricao.lower()} em {ano} no arquivo {caminho.name}.{aviso}")
    return _padronizar_candidato(pd.concat(quadros, ignore_index=True))


def carregar_candidatos(ano: int, somente_aptos: bool = True, uf: str | None = None, cargo: int = 6) -> pd.DataFrame:
    if ano not in URL_CANDIDATOS:
        raise ErroFonte(f"Não há endereço configurado para os candidatos de {ano}.")
    uf = _uf(uf)
    origem = baixar_arquivo(URL_CANDIDATOS[ano], DIR_BRUTOS / f"consulta_cand_{ano}.zip")
    sufixo = "aptos" if somente_aptos else "todos"
    recorte = f"_{uf}" if uf else ""
    _codigo, _descricao, slug = _cargo_tse(cargo)
    cache = DIR_PROCESSADOS / f"candidatos_{slug}_{ano}_{sufixo}{recorte}.csv"
    if _cache_valido(cache, origem):
        return _ler_cache(cache)
    quadro = candidatos_do_arquivo(origem, ano, somente_aptos=somente_aptos, uf=uf, cargo=cargo)
    _gravar_cache(quadro, cache, origem)
    return quadro


def _agregar_votos(caminho: Path, uf: str | None = None, cargo: int = 6) -> pd.DataFrame:
    uf = _uf(uf)
    votos: dict[str, int] = {}
    atributos: dict[str, dict[str, str]] = {}
    with _abrir_zip(caminho) as arquivo_zip:
        nomes = escolher_csvs(arquivo_zip.namelist(), "votacao_candidato_munzona", uf=uf)
        if not nomes:
            raise ErroFonte(f"{caminho.name} não contém a votação nominal por município e zona.")
        for nome in nomes:
            print(f"Lendo {Path(nome).name}")
            for pedaco, disponiveis in _iterar_csv(arquivo_zip, nome, COLUNAS_VOTOS):
                if "QT_VOTOS_NOMINAIS" not in disponiveis:
                    raise ErroFonte(f"{Path(nome).name} não tem a coluna QT_VOTOS_NOMINAIS.")
                pedaco = pedaco.loc[
                    _mascara_cargo(pedaco, cargo)
                    & _mascara_turno(pedaco)
                    & _mascara_ordinaria(pedaco)
                    & _mascara_uf(pedaco, uf)
                ]
                if pedaco.empty or "SQ_CANDIDATO" not in pedaco.columns:
                    continue
                pedaco = pedaco.copy()
                pedaco["sequencial"] = pedaco["SQ_CANDIDATO"].map(limpar_codigo)
                pedaco["votos"] = pd.to_numeric(pedaco["QT_VOTOS_NOMINAIS"], errors="coerce").fillna(0).astype(int)
                somas = pedaco.groupby("sequencial", sort=False)["votos"].sum()
                for sequencial, total in somas.items():
                    if not sequencial:
                        continue
                    votos[sequencial] = votos.get(sequencial, 0) + int(total)
                for _, linha in pedaco.drop_duplicates("sequencial").iterrows():
                    sequencial = linha["sequencial"]
                    if sequencial and sequencial not in atributos:
                        atributos[sequencial] = {
                            "uf": limpar_codigo(linha.get("SG_UF", "")),
                            "partido": limpar_codigo(linha.get("SG_PARTIDO", "")) or "(sem sigla)",
                            "numero": limpar_codigo(linha.get("NR_CANDIDATO", "")),
                            "nome": limpar_codigo(linha.get("NM_CANDIDATO", "")),
                            "nome_urna": limpar_codigo(linha.get("NM_URNA_CANDIDATO", ""))
                            or limpar_codigo(linha.get("NM_CANDIDATO", "")),
                            "resultado": limpar_codigo(linha.get("DS_SIT_TOT_TURNO", "")),
                        }
    if not votos:
        _codigo, descricao, _slug = _cargo_tse(cargo)
        raise ErroFonte(f"A votação de {descricao.lower()} em 2022 não foi encontrada no arquivo.")
    quadro = pd.DataFrame({"sequencial": list(votos), "votos": list(votos.values())})
    detalhes = pd.DataFrame([{"sequencial": chave, **valor} for chave, valor in atributos.items()])
    return quadro.merge(detalhes, on="sequencial", how="left")


def juntar_votos(votos: pd.DataFrame, candidatos: pd.DataFrame) -> pd.DataFrame:
    atributos = [
        coluna
        for coluna in ("sequencial", "uf", "partido", "numero", "nome", "nome_urna", "resultado", "situacao", "federacao")
        if coluna in candidatos.columns
    ]
    base = candidatos.loc[:, atributos].drop_duplicates("sequencial")
    quadro = base.merge(votos.loc[:, ["sequencial", "votos"]], on="sequencial", how="left")
    quadro["votos"] = quadro["votos"].fillna(0).astype(int)
    extras = votos.loc[~votos["sequencial"].isin(set(base["sequencial"]))].copy()
    if not extras.empty:
        extras["votos"] = extras["votos"].fillna(0).astype(int)
        quadro = pd.concat([quadro, extras], ignore_index=True)
    quadro["votos"] = quadro["votos"].astype(int)
    return quadro.sort_values(["votos", "partido", "nome_urna"], ascending=[False, True, True]).reset_index(drop=True)


def carregar_votos(candidatos_2022: pd.DataFrame, uf: str | None = None, cargo: int = 6) -> pd.DataFrame:
    uf = _uf(uf)
    origem = baixar_arquivo(URL_VOTOS_2022, DIR_BRUTOS / "votacao_candidato_munzona_2022.zip")
    recorte = f"_{uf}" if uf else ""
    _codigo, _descricao, slug = _cargo_tse(cargo)
    cache = DIR_PROCESSADOS / f"votos_{slug}_2022{recorte}.csv"
    if _cache_valido(cache, origem):
        quadro = _ler_cache(cache)
        quadro["votos"] = quadro["votos"].map(parse_inteiro)
        return quadro.sort_values(["votos", "partido", "nome_urna"], ascending=[False, True, True]).reset_index(drop=True)
    quadro = juntar_votos(_agregar_votos(origem, uf=uf, cargo=cargo), candidatos_2022)
    _gravar_cache(quadro, cache, origem)
    return quadro


@dataclass
class GastosPublicidade:
    por_candidato: pd.DataFrame
    por_partido: pd.DataFrame
    categorias: pd.DataFrame
    texto: str


def _acumular_despesas(
    caminho: Path,
    sequenciais: set[str],
    data_corte: date | None,
    uf: str | None = None,
    somente_publicidade: bool = True,
    cargo: int = 6,
) -> tuple[dict[str, float], dict[str, dict[str, float | int | bool]], dict[str, int | date | None | str]]:
    uf = _uf(uf)
    gastos: dict[str, float] = {}
    categorias: dict[str, dict[str, float | int | bool]] = {}
    resumo: dict[str, int | date | None | str] = {
        "incluidas": 0,
        "apos_corte": 0,
        "sem_data": 0,
        "menor_data": None,
        "maior_data": None,
        "gerado_em": "",
        "coluna_tipo": "",
    }
    with _abrir_zip(caminho) as arquivo_zip:
        nomes = []
        for trecho in ("despesas_contratadas", "despesa_contratada"):
            nomes = escolher_csvs(arquivo_zip.namelist(), trecho, uf=uf)
            if nomes:
                break
        if not nomes:
            raise ErroFonte(
                f"{caminho.name} não contém despesas contratadas. "
                f"Arquivos encontrados: {[Path(nome).name for nome in arquivo_zip.namelist()[:12]]}"
            )
        for nome in nomes:
            print(f"Lendo {Path(nome).name}")
            for pedaco, disponiveis in _iterar_csv(arquivo_zip, nome, COLUNAS_DESPESAS):
                coluna_tipo = escolher_coluna_tipo(list(disponiveis))
                if coluna_tipo is None or coluna_tipo not in pedaco.columns:
                    raise ErroFonte(
                        "Não encontrei a coluna de tipo da despesa "
                        "(DS_ORIGEM_DESPESA, DS_TIPO_DESPESA ou DS_NATUREZA_DESPESA)."
                    )
                resumo["coluna_tipo"] = coluna_tipo
                if not resumo["gerado_em"] and "DT_GERACAO" in pedaco.columns and not pedaco.empty:
                    resumo["gerado_em"] = limpar_codigo(pedaco["DT_GERACAO"].iloc[0])
                if "SQ_CANDIDATO" not in pedaco.columns:
                    continue
                pedaco = pedaco.loc[_mascara_cargo(pedaco, cargo) & _mascara_uf(pedaco, uf)].copy()
                pedaco["sequencial"] = pedaco["SQ_CANDIDATO"].map(limpar_codigo)
                pedaco = pedaco.loc[pedaco["sequencial"].isin(sequenciais)]
                if pedaco.empty:
                    continue
                if "DT_DESPESA" in pedaco.columns:
                    datas = pd.to_datetime(pedaco["DT_DESPESA"], dayfirst=True, errors="coerce")
                else:
                    datas = pd.Series(pd.NaT, index=pedaco.index)
                if data_corte is not None:
                    sem_data = datas.isna()
                    resumo["sem_data"] = int(resumo["sem_data"]) + int(sem_data.sum())
                    depois = datas.notna() & (datas > pd.Timestamp(data_corte))
                    resumo["apos_corte"] = int(resumo["apos_corte"]) + int(depois.sum())
                    pedaco = pedaco.loc[~sem_data & ~depois]
                    datas = datas.loc[pedaco.index]
                if pedaco.empty:
                    continue
                validas = datas.dropna()
                if not validas.empty:
                    menor_pedaco = validas.min().date()
                    maior_pedaco = validas.max().date()
                    menor = resumo["menor_data"]
                    maior = resumo["maior_data"]
                    resumo["menor_data"] = menor_pedaco if menor is None or menor_pedaco < menor else menor
                    resumo["maior_data"] = maior_pedaco if maior is None or maior_pedaco > maior else maior
                temporario = pd.DataFrame(
                    {
                        "sequencial": pedaco["sequencial"].to_numpy(),
                        "tipo": pedaco[coluna_tipo].map(lambda valor: limpar_codigo(valor) or "(sem tipo)").to_numpy(),
                        "valor": pedaco["VR_DESPESA_CONTRATADA"].map(parse_valor).to_numpy()
                        if "VR_DESPESA_CONTRATADA" in pedaco.columns
                        else 0.0,
                    }
                )
                if somente_publicidade:
                    temporario["publicidade"] = temporario["tipo"].map(eh_publicidade)
                else:
                    temporario["publicidade"] = True
                for tipo, grupo in temporario.groupby("tipo", sort=False):
                    registro = categorias.setdefault(
                        str(tipo),
                        {
                            "lancamentos": 0,
                            "valor": 0.0,
                            "publicidade": bool(grupo["publicidade"].iloc[0]),
                        },
                    )
                    registro["lancamentos"] = int(registro["lancamentos"]) + int(len(grupo))
                    registro["valor"] = float(registro["valor"]) + float(grupo["valor"].sum())
                publicidade = temporario.loc[temporario["publicidade"]]
                resumo["incluidas"] = int(resumo["incluidas"]) + int(len(publicidade))
                for sequencial, total in publicidade.groupby("sequencial", sort=False)["valor"].sum().items():
                    gastos[str(sequencial)] = gastos.get(str(sequencial), 0.0) + float(total)
    return gastos, categorias, resumo


def montar_gastos(
    candidatos: pd.DataFrame,
    gastos: dict[str, float],
    categorias: dict[str, dict[str, float | int | bool]],
    resumo: dict[str, int | date | None | str],
    ano: int,
    data_corte: date | None,
    uf: str | None = None,
    somente_publicidade: bool = True,
) -> GastosPublicidade:
    from eleitoral.analise import resumo_por_partido

    colunas = [
        coluna
        for coluna in ("sequencial", "partido", "uf", "numero", "nome_urna", "nome", "resultado")
        if coluna in candidatos.columns
    ]
    por_candidato = candidatos.loc[:, colunas].drop_duplicates("sequencial").copy()
    por_candidato["gasto_publicidade"] = por_candidato["sequencial"].map(gastos).fillna(0.0).astype(float)
    por_candidato = por_candidato.sort_values(
        ["gasto_publicidade", "partido", "nome_urna"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    por_partido = resumo_por_partido(por_candidato, valor="gasto_publicidade")
    tabela_categorias = pd.DataFrame(
        [
            {
                "tipo": tipo,
                "lancamentos": int(dados["lancamentos"]),
                "valor": float(dados["valor"]),
                "entra_na_publicidade": "sim" if dados["publicidade"] else "não",
            }
            for tipo, dados in categorias.items()
        ]
    )
    if tabela_categorias.empty:
        tabela_categorias = pd.DataFrame(columns=["tipo", "lancamentos", "valor", "entra_na_publicidade"])
    else:
        tabela_categorias = tabela_categorias.sort_values("valor", ascending=False).reset_index(drop=True)

    corte = f"até {formatar_data(data_corte)}" if data_corte else "prestação final do pleito"
    gerado = resumo["gerado_em"] or "data não informada no arquivo"
    recorte = f" Recorte: {uf}." if uf else ""
    assunto = "de publicidade" if somente_publicidade else "da campanha, de todos os tipos"
    texto = (
        f"Deputado federal {ano}: despesas contratadas {assunto}, {corte}.{recorte} "
        f"Arquivo do TSE gerado em {gerado}. "
        f"Período com despesa datada: {formatar_data(resumo['menor_data'])} a {formatar_data(resumo['maior_data'])}. "
        f"Lançamentos de publicidade somados: {formatar_inteiro(resumo['incluidas'])}. "
        f"Lançamentos depois do corte: {formatar_inteiro(resumo['apos_corte'])}. "
        f"Lançamentos sem data: {formatar_inteiro(resumo['sem_data'])}. "
        f"Coluna de classificação: {resumo['coluna_tipo']}. "
        f"Total: {formatar_reais(por_candidato['gasto_publicidade'].sum())}."
    )
    return GastosPublicidade(por_candidato, por_partido, tabela_categorias, texto)


def carregar_gastos_publicidade(
    ano: int,
    candidatos: pd.DataFrame,
    data_corte: date | None = None,
    uf: str | None = None,
    somente_publicidade: bool = True,
    cargo: int = 6,
) -> GastosPublicidade:
    if ano not in URL_CONTAS:
        raise ErroFonte(f"Não há prestação de contas configurada para {ano}.")
    if data_corte is None and ano == 2026:
        data_corte = DATA_CORTE_2026
    uf = _uf(uf)
    origem = baixar_arquivo(URL_CONTAS[ano], DIR_BRUTOS / f"prestacao_contas_candidatos_{ano}.zip")
    corte_nome = data_corte.isoformat() if data_corte else "completa"
    recorte = f"_{uf}" if uf else ""
    prefixo = "publicidade" if somente_publicidade else "campanha"
    _codigo, _descricao, slug = _cargo_tse(cargo)
    cache = DIR_PROCESSADOS / f"{prefixo}_{slug}_{ano}{recorte}_{corte_nome}.csv"
    nome_categorias = (
        f"{prefixo}_categorias_{ano}{recorte}_{corte_nome}.csv"
        if slug == "deputado_federal"
        else f"{prefixo}_categorias_{slug}_{ano}{recorte}_{corte_nome}.csv"
    )
    cache_categorias = DIR_PROCESSADOS / nome_categorias
    cache_texto = DIR_PROCESSADOS / f"{prefixo}_{slug}_{ano}{recorte}_{corte_nome}.txt"
    if _cache_valido(cache, origem) and cache_categorias.exists() and cache_texto.exists():
        por_candidato = _ler_cache(cache)
        por_candidato["gasto_publicidade"] = por_candidato["gasto_publicidade"].map(parse_valor)
        categorias = _ler_cache(cache_categorias)
        if "valor" in categorias.columns:
            categorias["valor"] = categorias["valor"].map(parse_valor)
        if "lancamentos" in categorias.columns:
            categorias["lancamentos"] = categorias["lancamentos"].map(parse_inteiro)
        from eleitoral.analise import resumo_por_partido

        return GastosPublicidade(
            por_candidato,
            resumo_por_partido(por_candidato, valor="gasto_publicidade"),
            categorias,
            cache_texto.read_text(encoding="utf-8"),
        )
    sequenciais = {limpar_codigo(valor) for valor in candidatos["sequencial"] if limpar_codigo(valor)}
    gastos, categorias, resumo = _acumular_despesas(
        origem, sequenciais, data_corte, uf=uf, somente_publicidade=somente_publicidade, cargo=cargo
    )
    relatorio = montar_gastos(
        candidatos,
        gastos,
        categorias,
        resumo,
        ano,
        data_corte,
        uf=uf,
        somente_publicidade=somente_publicidade,
    )
    _gravar_cache(relatorio.por_candidato, cache, origem)
    _gravar_cache(relatorio.categorias, cache_categorias, origem)
    cache_texto.write_text(relatorio.texto, encoding="utf-8")
    return relatorio


def colunas_para_exibir(quadro: pd.DataFrame, preferidas: list[str] | None = None) -> pd.DataFrame:
    preferidas = preferidas or COLUNAS_EXIBICAO_CANDIDATO
    colunas = []
    for coluna in preferidas:
        if coluna not in quadro.columns:
            continue
        preenchida = quadro[coluna].map(limpar_codigo).ne("")
        if preenchida.any():
            colunas.append(coluna)
    return quadro.loc[:, colunas]
