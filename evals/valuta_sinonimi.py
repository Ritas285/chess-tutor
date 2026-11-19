#!/usr/bin/env python3
"""Il giudice del quiz capisce le parole diverse? 16 casi con riferimento fisso (evals/gold_sinonimi.json).

    python evals/valuta_sinonimi.py [etichetta]  [--ripeti N]

Serve OPENAI_API_KEY (circa 1 centesimo a giro). Il giudice è un modello: con --ripeti N si rilancia N volte lo stesso gold per
vedere se l'esito cambia da un giro all'altro. Misure: sinonimi accettati (su 8), trabocchetti respinti (su 8) e soprattutto gli
errori GRAVI = accettare come corretta una risposta errata (i trabocchetti che passano).
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from chess_tutor import config, quiz, valutazione  # noqa: E402

CASI = json.loads((Path(__file__).parent / "gold_sinonimi.json").read_text(encoding="utf-8"))["casi"]


def main() -> None:
    if not config.OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY non impostata: copia .env.example in .env e inserisci la tua chiave.")
    args = sys.argv[1:]
    giri = 1
    if "--ripeti" in args:
        i = args.index("--ripeti")
        giri = int(args[i + 1])
        del args[i:i + 2]
    etichetta = args[0] if args else ""
    from datapizza.clients.openai import OpenAIClient
    client = OpenAIClient(api_key=config.OPENAI_API_KEY, model=config.CHAT_MODEL)

    righe = []
    for giro in range(1, giri + 1):
        for c in CASI:
            g, _ = quiz.verifica_risposta(c["domanda"], c["risposta"], client=client, riferimento=c["riferimento"])
            righe.append({"giro": giro, "id": c["id"], "gruppo": c["gruppo"], "atteso": c["atteso"], "esito": g.esito,
                          "giusto": g.esito == c["atteso"], "grave": c["atteso"] == "errata" and g.esito == "corretta",
                          "feedback": g.feedback})
            print(f"giro {giro}  {c['id']}  atteso={c['atteso']:<9} esito={g.esito:<16} {'ok ' if righe[-1]['giusto'] else 'XX '}"
                  f"{'GRAVE ' if righe[-1]['grave'] else ''}{c['risposta'][:45]!r}")

    n = len(righe)
    sin = [r for r in righe if r["gruppo"] == "sinonimo"]
    tra = [r for r in righe if r["gruppo"] == "trabocchetto"]
    sin_ok, tra_ok = sum(r["giusto"] for r in sin), sum(r["giusto"] for r in tra)
    gravi = [f"{r['id']}(giro {r['giro']})" for r in righe if r["grave"]]
    print(f"\nESITO GIUSTO: {sum(r['giusto'] for r in righe)}/{n} · sinonimi accettati: {sin_ok}/{len(sin)} · "
          f"trabocchetti respinti: {tra_ok}/{len(tra)} · ERRORI GRAVI: {len(gravi)} {gravi}")
    sbagliati = [r for r in righe if not r["giusto"]]
    if sbagliati:
        print("\nID DA GUARDARE (con la motivazione del giudice):")
        for r in sbagliati:
            print(f"  {r['id']} (giro {r['giro']}): atteso {r['atteso']}, dato {r['esito']}: {r['feedback'][:160]}")
    riassunto = {"n_domande": n, "n": {}, "errori": {"sinonimi": sorted({r["id"] for r in sbagliati})},
                 "misure": {"sinonimi_accettati": round(sin_ok / len(sin), 4), "trabocchetti_respinti": round(tra_ok / len(tra), 4),
                            "sinonimi_errori_gravi": len(gravi)}}
    percorso = valutazione.salva("sinonimi", righe, riassunto, etichetta=etichetta)
    print(f"\nSalvato in evals/results/{percorso.name}")


if __name__ == "__main__":
    main()
