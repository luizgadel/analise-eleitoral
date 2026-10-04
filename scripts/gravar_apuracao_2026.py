"""Grava o snapshot da apuração de 2026 no JSON do painel quando o TSE fecha a totalização."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from eleitoral.apuracao import URL_APURACAO_2026, aplicar_snapshot

DESTINO = Path(os.environ.get("APURACAO_DESTINO") or (RAIZ / "painel" / "public" / "dados" / "amazonas.json"))


def main() -> None:
    if "--stdin" in sys.argv:
        bruto = json.loads(sys.stdin.read())
    else:
        resposta = requests.get(URL_APURACAO_2026, timeout=40, headers={"User-Agent": "painel-amazonas"})
        resposta.raise_for_status()
        bruto = resposta.json()
    painel = json.loads(DESTINO.read_text(encoding="utf-8"))
    if not aplicar_snapshot(painel, bruto):
        print("Apuração ainda aberta. O JSON do painel não foi alterado.")
        return
    DESTINO.write_text(json.dumps(painel, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Snapshot gravado em {DESTINO}")


if __name__ == "__main__":
    main()
