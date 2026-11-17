#!/usr/bin/env python3
"""Confronta i tre modi di ricerca (solo significato, solo parole, ibrido) sulle domande di prova. (Step 1b, metodo S08)

    python evals/confronta_ricerca.py              # confronto dei tre modi
    python evals/confronta_ricerca.py --tokenizzatori   # confronto del tokenizzatore del corso con quello adattato

Misure: "primo" = il documento giusto è al PRIMO posto; "top3" = è tra i primi 3. Serve OPENAI_API_KEY (frazioni di centesimo).
Con poche domande una differenza di 1 è rumore: guarda il trend e gli ID sbagliati, non solo i totali (regola del corso).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from chess_tutor import ingest, retrieval  # noqa: E402

DOMANDE = json.loads((Path(__file__).parent / "domande_ricerca.json").read_text(encoding="utf-8"))["domande"]


def misura(ricerca: retrieval.Ricerca, modo: str) -> dict:
    risultati = {"semantica": [0, 0, 0], "lessicale": [0, 0, 0]}      # [primo, top3, totale]
    sbagliate = []
    for d in DOMANDE:
        fonti = [h.metadata["source_file"] for h in ricerca.cerca(d["domanda"], 3, modo)]
        r = risultati[d["tipo"]]
        r[2] += 1
        r[0] += bool(fonti) and fonti[0] in d["attesi"]
        r[1] += any(f in d["attesi"] for f in fonti)
        if not fonti or fonti[0] not in d["attesi"]:
            sbagliate.append(f"{d['id']} ({d['domanda']}) -> {fonti}")
    return {"risultati": risultati, "sbagliate": sbagliate}


def stampa_tabella(righe: list[tuple[str, dict]]) -> None:
    print(f"{'':<34}| semantiche (8)      | lessicali (5)       | tutte (13)")
    print(f"{'':<34}| primo   top3        | primo   top3        | primo   top3")
    for nome, m in righe:
        s, lx = m["risultati"]["semantica"], m["risultati"]["lessicale"]
        print(f"{nome:<34}| {s[0]}/{s[2]}     {s[1]}/{s[2]}        | {lx[0]}/{lx[2]}     {lx[1]}/{lx[2]}        | "
              f"{s[0] + lx[0]}/13   {s[1] + lx[1]}/13")
    for nome, m in righe:
        for s in m["sbagliate"]:
            print(f"   x {nome}: {s}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizzatori", action="store_true")
    args = ap.parse_args()

    embedder, vs = ingest.crea_embedder(), ingest.crea_vector_store()
    ingest.indicizza_ramo(vs, embedder, "rules", verbose=False)
    if args.tokenizzatori:
        righe = [(f"bm25, tokenizzatore {nome}", misura(retrieval.Ricerca(vs, embedder, "rules", tok), "bm25"))
                 for nome, tok in (("del corso", retrieval.tokenizza_corso), ("adattato", retrieval.tokenizza))]
        righe += [(f"ibrido, tokenizzatore {nome}", misura(retrieval.Ricerca(vs, embedder, "rules", tok), "ibrido"))
                  for nome, tok in (("del corso", retrieval.tokenizza_corso), ("adattato", retrieval.tokenizza))]
    else:
        ricerca = retrieval.Ricerca(vs, embedder, "rules")
        righe = [(f"modo '{modo}'", misura(ricerca, modo)) for modo in retrieval.MODI]
    stampa_tabella(righe)


if __name__ == "__main__":
    main()
