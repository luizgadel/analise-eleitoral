"""Regras puras de limpeza, filtro e comparação. Sem download."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

from eleitoral.config import CARGO_DEPUTADO_FEDERAL, TERMOS_PUBLICIDADE

_VAZIOS = {"", "#NULO", "#NULO#", "#NE", "#NE#", "NAN", "NONE", "NAT", "-1", "<NA>"}
_FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d", "%d/%m/%Y %H:%M:%S")


def normalizar_texto(valor: object) -> str:
    if valor is None:
        return ""
    texto = str(valor).strip()
    if texto.upper() in _VAZIOS:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = texto.upper()
    return re.sub(r"\s+", " ", texto).strip()


def limpar_codigo(valor: object) -> str:
    texto = str(valor).strip() if valor is not None else ""
    if texto.endswith(".0"):
        texto = texto[:-2]
    if texto.upper() in _VAZIOS:
        return ""
    return texto


def somente_digitos(valor: object) -> str:
    return re.sub(r"\D", "", limpar_codigo(valor))


def cpf_comparavel(valor: object) -> str:
    digitos = somente_digitos(valor)
    if len(digitos) != 11:
        return ""
    return digitos


def normalizar_data(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor).strip()
    if texto.upper() in _VAZIOS:
        return ""
    texto = texto.split(" ")[0]
    for formato in _FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    return ""


def parse_data(valor: object) -> date | None:
    iso = normalizar_data(valor)
    if not iso:
        return None
    ano, mes, dia = iso.split("-")
    return date(int(ano), int(mes), int(dia))


def parse_valor(valor: object) -> float:
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    texto = str(valor).strip()
    if texto.upper() in _VAZIOS:
        return 0.0
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    texto = re.sub(r"[^0-9.\-]", "", texto)
    if texto in {"", "-", ".", "-."}:
        return 0.0
    try:
        return float(texto)
    except ValueError:
        return 0.0


def parse_inteiro(valor: object) -> int:
    return int(round(parse_valor(valor)))


def eh_publicidade(valor: object) -> bool:
    texto = normalizar_texto(valor)
    if not texto:
        return False
    return any(termo in texto for termo in TERMOS_PUBLICIDADE)


def eh_eleito(resultado: object) -> bool:
    texto = normalizar_texto(resultado)
    return texto.startswith("ELEITO")


def eh_deputado_federal(codigo_cargo: object, descricao_cargo: object = "") -> bool:
    codigo = somente_digitos(codigo_cargo)
    if codigo:
        return int(codigo) == CARGO_DEPUTADO_FEDERAL
    return normalizar_texto(descricao_cargo) == "DEPUTADO FEDERAL"


def eh_eleicao_ordinaria(descricao: object, codigo: object = "") -> bool:
    texto = normalizar_texto(descricao)
    if texto:
        return "ORDIN" in texto
    codigo_limpo = somente_digitos(codigo)
    if codigo_limpo:
        return int(codigo_limpo) == 2
    return True


def eh_turno_deputado(turno: object) -> bool:
    texto = limpar_codigo(turno)
    if not texto:
        return True
    return texto == "1"


def eh_apto(situacao: object) -> bool:
    texto = normalizar_texto(situacao)
    if not texto:
        return True
    return texto == "APTO"


def dentro_do_periodo(data_despesa: date | None, data_corte: date | None) -> bool:
    if data_corte is None:
        return True
    if data_despesa is None:
        return False
    return data_despesa <= data_corte


def escolher_csvs(nomes: list[str], trecho: str, uf: str | None = None) -> list[str]:
    """Prefere o CSV do estado quando a UF é informada; senão, o arquivo nacional."""
    trecho_minusculo = trecho.lower()
    candidatos = [
        nome
        for nome in nomes
        if nome.lower().endswith(".csv") and trecho_minusculo in Path(nome).name.lower()
    ]
    if uf:
        marca = f"_{uf.strip().upper()}.CSV"
        do_estado = [nome for nome in candidatos if Path(nome).name.upper().endswith(marca)]
        if do_estado:
            return do_estado
    brasil = [nome for nome in candidatos if "BRASIL" in Path(nome).name.upper()]
    return brasil or candidatos


def escolher_coluna_tipo(colunas: list[str]) -> str | None:
    from eleitoral.config import COLUNAS_TIPO_DESPESA

    for coluna in COLUNAS_TIPO_DESPESA:
        if coluna in colunas:
            return coluna
    if "DS_DESPESA" in colunas:
        return "DS_DESPESA"
    return None


def detectar_encoding(amostra: bytes) -> str:
    if amostra.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    texto = amostra.decode("latin-1", errors="replace")
    mojibake = ("Ã£", "Ã¡", "Ã©", "Ã§", "Ãµ", "Ãº", "Ã´", "Ã‰", "Ã‡")
    if any(marca in texto for marca in mojibake):
        return "utf-8"
    return "latin-1"


def formatar_inteiro(valor: object) -> str:
    return f"{int(round(parse_valor(valor))):,}".replace(",", ".")


def formatar_reais(valor: object) -> str:
    texto = f"{parse_valor(valor):,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_data(valor: date | None) -> str:
    if valor is None:
        return "sem data"
    return valor.strftime("%d/%m/%Y")
