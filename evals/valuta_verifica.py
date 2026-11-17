#!/usr/bin/env python3
"""Quanto è affidabile la VERIFICA delle risposte (Step 2a)? 16 risposte di esito noto (evals/gold_verifica.json).

    python evals/valuta_verifica.py

Serve OPENAI_API_KEY (circa 1 centesimo). Misure: esiti giusti su 16, e soprattutto gli errori GRAVI: accettare una risposta
sbagliata (errata -> corretta) o respingerne una giusta (corretta -> errata). Con 16 casi una differenza di 1 è rumore (S08):
si guardano gli ID sbagliati e le motivazioni, non solo il totale.
"""
from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from chess_tutor import config, quiz, valutazione  # noqa: E402

CASI = json.loads((Path(__file__).parent / "gold_verifica.json").read_text(encoding="utf-8"))["casi"]
GRAVI = {("errata", "corretta"), ("corretta", "errata")}


def main() -> None:
    if not config.OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY non impostata: copia .env.example in .env e inserisci la tua chiave.")
    from chess_tutor.tutor import Tutor
    print("Preparo l'indice…")
    tutor = Tutor.crea()
    righe = []
    for c in CASI:
        g, fonti = quiz.verifica_risposta(c["domanda"], c["risposta"], client=tutor.client, ricerche=tutor.ricerche)
        riga = {"id": c["id"], "atteso": c["atteso"], "esito": g.esito, "giusto": g.esito == c["atteso"],
                "grave": (c["atteso"], g.esito) in GRAVI, "feedback": g.feedback, "fonti": fonti}
        righe.append(riga)
        print(f"{c['id']}  atteso={c['atteso']:<16} esito={g.esito:<16} {'ok ' if riga['giusto'] else 'XX '}{'GRAVE ' if riga['grave'] else ''}"
              f"{c['domanda'][:40]!r}")

    giusti = sum(r["giusto"] for r in righe)
    gravi = [r["id"] for r in righe if r["grave"]]
    print(f"\nESITO GIUSTO: {giusti}/{len(righe)} · ERRORI GRAVI (accetta lo sbagliato / respinge il giusto): {len(gravi)} {gravi}")
    for atteso in ("corretta", "parziale", "errata", "non_verificabile"):
        esiti = Counter(r["esito"] for r in righe if r["atteso"] == atteso)
        print(f"  atteso {atteso:<16} -> " + ", ".join(f"{k}: {v}" for k, v in esiti.most_common()))
    sbagliati = [r for r in righe if not r["giusto"]]
    if sbagliati:
        print("\nID DA GUARDARE (con la motivazione del giudice):")
        for r in sbagliati:
            print(f"  {r['id']}: atteso {r['atteso']}, dato {r['esito']}: {r['feedback'][:160]}")
    riassunto = {"n_domande": len(righe), "n": {}, "errori": {"verifica": [r["id"] for r in sbagliati]},
                 "misure": {"verifica_esiti_giusti": round(giusti / len(righe), 4), "verifica_errori_gravi": len(gravi)}}
    percorso = valutazione.salva("verifica", righe, riassunto)
    print(f"\nSalvato in evals/results/{percorso.name}")


if __name__ == "__main__":
    main()
