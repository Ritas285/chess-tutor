#!/usr/bin/env python3
"""Valuta il tutor sul gold (evals/gold.json): routing, retrieval e, con --e2e, risposte giudicate. (Step 1f, metodo S08)

    python evals/run_evals.py                    # routing + retrieval (poco costo: embedding e router, ~1 centesimo)
    python evals/run_evals.py --e2e              # + risposte vere del tutor e giudice LLM (faithfulness, relevancy): ~3 centesimi
    python evals/run_evals.py --e2e --etichetta prova-nuovo-prompt     # per riconoscere il run nel confronto
    python evals/run_evals.py --solo G01,G17     # solo alcune domande (per capire un errore)

Serve OPENAI_API_KEY. Il risultato si salva in evals/results/ e viene confrontato con l'ultimo run dello stesso tipo, con la
regola A/B del corso: una modifica vale se la faithfulness sale di almeno 0.03, la recall non scende di più di 0.02 e il costo
resta nel budget. Su un gold di 33 domande una differenza sotto 0.05 è RUMORE.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from chess_tutor import config, valutazione  # noqa: E402

TITOLI = {
    "routing": "routing sul ramo giusto", "recall_noto": "recall@3 (ramo noto)", "mrr_noto": "MRR (ramo noto)",
    "trovata_noto": "fonte trovata, tutti i gruppi (ramo noto)", "recall_router": "recall@3 (ramo scelto dal router)",
    "mrr_router": "MRR (ramo scelto dal router)", "trovata_router": "fonte trovata, tutti i gruppi (router)",
    "trovata_agente": "fonte trovata dall'agente (nelle risposte vere)", "citazione": "risposte con citazione",
    "astensione": "astensione \"Non lo so\" (fuori corpus)", "rifiuto": "rifiuto del fuori tema",
    "bloccata": "attacco fermato dal guardrail", "falsa_astensione": "falsa astensione (in corpus, dice \"Non lo so\")",
    "faithfulness": "faithfulness (giudice)", "relevancy": "relevancy (giudice)",
    "latenza_p50_s": "latenza p50 (s)", "latenza_p95_s": "latenza p95 (s)", "costo_medio_usd": "costo medio a domanda ($)",
    "costo_giudice_totale_usd": "costo del giudice, totale ($)",
}


def stampa(riassunto: dict) -> None:
    print(f"\nRISULTATI su {riassunto['n_domande']} domande")
    for nome, valore in riassunto["misure"].items():
        n = riassunto["n"].get(nome)
        print(f"  {TITOLI.get(nome, nome):<52} {valore:<9}" + (f" (su {n})" if n else ""))
    if riassunto["errori"]:
        print("\nID DA GUARDARE (non solo la media):")
        for nome, ids in riassunto["errori"].items():
            print(f"  {TITOLI.get(nome, nome):<52} {', '.join(ids)}")


def stampa_confronto(nuovo: dict, vecchio: dict) -> None:
    print(f"\nCONFRONTO con {vecchio['file']}")
    for r in valutazione.confronta(nuovo, vecchio):
        print(f"  {TITOLI.get(r['misura'], r['misura']):<52} {r['vecchio']:<9} -> {r['nuovo']:<9} ({r['delta']:+}) {r['giudizio']}")
    ab = valutazione.regola_ab(nuovo, vecchio)
    esiti = {None: "non misurabile", True: "ok", False: "NO"}
    print("\nREGOLA A/B: " + " · ".join(f"{k}: {esiti[v]}" for k, v in ab["controlli"].items()))
    print(f"  {ab['nota']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--e2e", action="store_true", help="risposte vere del tutor + giudice LLM")
    ap.add_argument("--etichetta", default="", help="nome breve del run, per riconoscerlo")
    ap.add_argument("--solo", default="", help="ID separati da virgola (es. G01,G17)")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--no-salva", action="store_true")
    args = ap.parse_args()

    if not config.OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY non impostata: copia .env.example in .env e inserisci la tua chiave (i test, invece, non la richiedono).")
    gold = valutazione.carica_gold()
    if args.solo:
        voluti = set(args.solo.split(","))
        gold = [d for d in gold if d["id"] in voluti]
    from chess_tutor.tutor import Tutor
    print("Preparo il tutor…")
    tutor = Tutor.crea()
    modo = "e2e" if args.e2e else "retrieval"
    print(f"Valuto {len(gold)} domande (modo: {modo})…")
    if args.e2e:
        righe = valutazione.esegui_e2e(tutor, gold, giudice=tutor.client)
    else:
        righe = valutazione.esegui_retrieval(tutor.ricerche, gold, client=tutor.client, k=args.k)
    riassunto = valutazione.riassumi(righe)
    stampa(riassunto)
    # un run parziale (--solo) non si salva: diventerebbe il "precedente" di un confronto con un gold diverso
    percorso = None if (args.no_salva or args.solo) else valutazione.salva(modo, righe, riassunto, etichetta=args.etichetta)
    precedente = valutazione.ultimo(modo, escludi=percorso)
    if precedente:
        stampa_confronto(riassunto, precedente)
    else:
        print("\n(Primo run di questo tipo: è la baseline, non c'è ancora un confronto.)")
    if percorso:
        print(f"\nSalvato in {percorso.relative_to(percorso.parent.parent.parent)}")


if __name__ == "__main__":
    main()
