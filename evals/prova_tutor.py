#!/usr/bin/env python3
"""Prova il tutor su 12 domande vere e misura: routing, citazioni, astensione, rifiuto del fuori tema, latenza, costo. (Step 1c)

    python evals/prova_tutor.py

Serve OPENAI_API_KEY (12 domande: pochi centesimi). Non è il gold finale (Step 1f): con poche domande una differenza di 1
è rumore, quindi guarda il trend e le righe sbagliate, non solo i totali (regola del corso, S08).
"""
from __future__ import annotations

import json
import logging
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from chess_tutor.tutor import Tutor  # noqa: E402

DOMANDE = json.loads((Path(__file__).parent / "domande_tutor.json").read_text(encoding="utf-8"))["domande"]
CITA = re.compile(r"\[[^\]]+\.md[^\]]*\]")        # una citazione tipo [03_mosse_speciali.md › L'arrocco]


def main() -> None:
    print("Preparo il tutor…")
    tutor = Tutor.crea()
    righe, lat, costi = [], [], []
    ok = {"routing": [], "citazione": [], "astensione": [], "rifiuto": []}
    for d in DOMANDE:
        r = tutor.ask(d["domanda"])
        lat.append(r.latenza_s)
        costi.append(r.costo_usd)
        nota = ""
        if d["tipo"] == "in_corpus":
            ok["routing"].append(set(d["rami"]) <= set(r.rami))
            ok["citazione"].append(bool(CITA.search(r.testo)))
            nota = f"rami={r.rami} cita={ok['citazione'][-1]} tool={len(r.tool_usati)}"
        elif d["tipo"] == "fuori_corpus":
            ok["astensione"].append("non lo so" in r.testo.lower())
            nota = f"rami={r.rami} astenuta={ok['astensione'][-1]}"
        else:
            ok["rifiuto"].append(r.fuori_tema)
            nota = f"fuori_tema={r.fuori_tema}"
        righe.append(f"{d['id']:<3} {r.latenza_s:>5.1f}s ${r.costo_usd:.5f}  {nota}  | {r.testo[:70]!r}")
    print("\n".join(righe))

    def pct(xs):
        return f"{sum(xs)}/{len(xs)}"
    print("\nRISULTATI")
    print(f"  routing sul ramo giusto (domande nei documenti) : {pct(ok['routing'])}")
    print(f"  risposte con citazione della fonte              : {pct(ok['citazione'])}")
    print(f"  astensione \"Non lo so\" (scacchi fuori corpus)    : {pct(ok['astensione'])}")
    print(f"  rifiuto del fuori tema                          : {pct(ok['rifiuto'])}")
    lat_ord = sorted(lat)
    print(f"  latenza p50 {statistics.median(lat):.1f}s · p95 {lat_ord[min(len(lat_ord) - 1, int(0.95 * len(lat_ord)))]:.1f}s"
          f" · costo medio ${statistics.mean(costi):.5f} a domanda")


if __name__ == "__main__":
    main()
