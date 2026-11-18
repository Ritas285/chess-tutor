#!/usr/bin/env python3
"""Md contro PDF (Step 6, richiesta di Giuseppe): cambia qualcosa nel retrieval se i documenti sono PDF invece che Markdown?

    python evals/confronta_formati.py                # le due prove, poi salva in evals/results/
    python evals/confronta_formati.py --routing      # + il router sceglie i rami giusti? (chiama il modello: pochi centesimi)
    python evals/confronta_formati.py --solo-gold    # controlla solo che le frasi del gold ci siano nei PDF (offline, niente chiave)

Serve OPENAI_API_KEY per gli embedding (24 domande + ~140 pezzi: frazioni di centesimo). Servono i tre PDF in data/regolamento/ e
data/corsi/ (non stanno nel git: vedi README).

PROVA A, controllata: lo stesso regolamento della Federazione (12 domande) come PDF e come Markdown con le sezioni. Il TESTO e' lo
stesso, cambia solo cosa fa l'ingestione: nel PDF i pezzi sono per pagina e frase, nel md una sezione = un pezzo con il titolo
davanti. Una differenza qui e' dovuta al formato (e al modo di tagliare che il formato permette), non al contenuto.
PROVA B, realistica: i rami PDF veri ('corsi': manuale e dispensa, con diagrammi rovinati e testate) e 'regolamento'.

Con 12 domande per ramo una differenza di 1 domanda (8 punti percentuali) e' rumore: si guardano il trend e le domande sbagliate.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

os.environ["RAMI_PDF"] = "1"                      # i rami PDF esistono solo con questa variabile: va impostata prima degli import
RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
logging.disable(logging.CRITICAL)

from chess_tutor import config, formati, ingest, pdf, retrieval  # noqa: E402

GOLD = json.loads((Path(__file__).parent / "gold_pdf.json").read_text(encoding="utf-8"))["domande"]
RISULTATI = Path(__file__).parent / "results"
K = 5


def controlla_gold() -> list[str]:
    """Offline: ogni frase del gold deve trovarsi in almeno un pezzo del suo ramo (altrimenti la domanda e' impossibile)."""
    problemi = []
    for ramo in ("regolamento", "corsi"):
        testi = [t for f in ingest.documenti_del_ramo(ramo) for _, t in pdf.pezzi_del_pdf(f)]
        for d in (d for d in GOLD if d["ramo"] == ramo):
            if formati.posizione_della_risposta(testi, d["frasi"]) is None:
                problemi.append(f"{d['id']}: nessuna frase trovata nel ramo '{ramo}' ({d['domanda']})")
    return problemi


def misura(ricerca: retrieval.Ricerca, domande: list[dict], modo: str) -> tuple[dict, list[str]]:
    posizioni, sbagliate = [], []
    for d in domande:
        pezzi = ricerca.cerca(d["domanda"], K, modo)
        p = formati.posizione_della_risposta([c.text for c in pezzi], d["frasi"])
        posizioni.append(p)
        if p is None or p > 3:
            sbagliate.append(f"{d['id']} ({d['domanda']}): risposta {'non trovata' if p is None else f'al posto {p}'}")
    return formati.metriche(posizioni, K), sbagliate


def statistiche(ricerca: retrieval.Ricerca) -> dict:
    lun = [len(c.text) for c in ricerca.chunks]
    return {"pezzi": len(lun), "media_caratteri": sum(lun) // max(len(lun), 1), "max": max(lun, default=0)}


def riga(nome: str, m: dict) -> str:
    return f"  {nome:<34} primo {m['primo']:.2f}   top3 {m['top3']:.2f}   MRR {m['mrr']:.2f}   (n={m['n']})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--routing", action="store_true", help="controlla anche quali rami sceglie il router (chiama il modello)")
    ap.add_argument("--solo-gold", action="store_true", help="solo controllo offline delle frasi del gold")
    args = ap.parse_args()

    manca = [r for r in ("regolamento", "corsi") if r not in config.BRANCHES]
    if manca:
        sys.exit(f"Mancano i PDF dei rami {manca}: mettili in data/<ramo>/ (vedi README, sezione PDF).")
    problemi = controlla_gold()
    if problemi:
        sys.exit("Gold non valido (la frase non e' nei PDF):\n  " + "\n  ".join(problemi))
    print(f"Gold PDF: {len(GOLD)} domande, tutte le frasi si trovano nei PDF.")
    if args.solo_gold:
        return

    embedder, vs = ingest.crea_embedder(), ingest.crea_vector_store()
    ricerche = {}
    for ramo in ("regolamento", "corsi"):
        ingest.indicizza_ramo(vs, embedder, ramo, verbose=False)
        ricerche[ramo] = retrieval.Ricerca(vs, embedder, ramo)
    fsi = ingest.documenti_del_ramo("regolamento")[0]
    # CONTROLLO della dimensione: stesso PDF tagliato in pezzi piccoli e grandi. Senza, una differenza md/PDF potrebbe essere solo
    # "i primi 3 pezzi del PDF contengono 3 volte piu' testo": qui si vede quanto pesa la dimensione e quanto il formato.
    dimensione_originale = config.CHUNK_MAX_CHAR
    for massimo in (300, 2000):
        config.CHUNK_MAX_CHAR = massimo                       # pdf.spezza legge questo valore a ogni chiamata
        nome = f"regolamento_pdf{massimo}"
        cartella_pdf = Path(tempfile.mkdtemp()) / nome
        cartella_pdf.mkdir()
        (cartella_pdf / fsi.name).write_bytes(fsi.read_bytes())
        ingest.indicizza_ramo(vs, embedder, nome, data_dir=cartella_pdf.parent, verbose=False)
        ricerche[nome] = retrieval.Ricerca(vs, embedder, nome)
    config.CHUNK_MAX_CHAR = dimensione_originale
    with tempfile.TemporaryDirectory() as tmp:
        cartella = Path(tmp) / "regolamento_md"
        cartella.mkdir()
        (cartella / (fsi.stem + ".md")).write_text(formati.pdf_a_md(fsi), encoding="utf-8")
        ingest.indicizza_ramo(vs, embedder, "regolamento_md", data_dir=Path(tmp), verbose=False)
        ricerche["regolamento_md"] = retrieval.Ricerca(vs, embedder, "regolamento_md")
    dom = {r: [d for d in GOLD if d["ramo"] == r] for r in ("regolamento", "corsi")}

    out: dict = {"prova_A_stesso_testo": {}, "prova_B_rami_pdf": {}}
    print("\nPROVA A (controllata): stesso regolamento FSI, 12 domande. Cambiano formato e dimensione dei pezzi, non il testo")
    varianti = (("PDF, pezzi piccoli (max 300)", "regolamento_pdf300"), ("PDF, pezzi normali (max 1024)", "regolamento"),
                ("PDF, pezzi grandi (max 2000)", "regolamento_pdf2000"), ("Markdown (una sezione = un pezzo)", "regolamento_md"))
    for nome, ramo in varianti:
        ric = ricerche[ramo]
        st = statistiche(ric)
        top3 = [sum(len(c.text) for c in ric.cerca(d["domanda"], 3, "ibrido")) for d in dom["regolamento"]]
        st["testo_nei_primi_3_pezzi"] = sum(top3) // len(top3)
        print(f" {nome}: {st['pezzi']} pezzi, in media {st['media_caratteri']} car.; i primi 3 pezzi portano ~{st['testo_nei_primi_3_pezzi']} car.")
        out["prova_A_stesso_testo"][nome] = {"statistiche": st}
        for modo in retrieval.MODI:
            m, sbagliate = misura(ric, dom["regolamento"], modo)
            print(riga(f"modo {modo}", m))
            out["prova_A_stesso_testo"][nome][modo] = {**m, "sbagliate": sbagliate}
            if modo == "ibrido":
                for s in sbagliate:
                    print(f"      x {s}")

    print("\nPROVA B (realistica): ramo 'corsi' = manuale + dispensa, 12 domande")
    st = statistiche(ricerche["corsi"])
    print(f" {st['pezzi']} pezzi, in media {st['media_caratteri']} caratteri")
    out["prova_B_rami_pdf"]["corsi"] = {"statistiche": st}
    for modo in retrieval.MODI:
        m, sbagliate = misura(ricerche["corsi"], dom["corsi"], modo)
        print(riga(f"modo {modo}", m))
        out["prova_B_rami_pdf"]["corsi"][modo] = {**m, "sbagliate": sbagliate}
        if modo == "ibrido":
            for s in sbagliate:
                print(f"      x {s}")

    if args.routing:
        from datapizza.clients.openai import OpenAIClient

        from chess_tutor import router
        client = OpenAIClient(api_key=config.OPENAI_API_KEY, model=config.CHAT_MODEL)
        print(f"\nROUTING con {len(config.BRANCHES)} rami ({', '.join(config.BRANCHES)}): il router sceglie il ramo del PDF?")
        # Il ramo md `rules` tratta GLI STESSI argomenti del regolamento FSI: per le domande sul regolamento scegliere `rules` va bene
        # (la risposta c'e' lo stesso); si conta a parte quante volte il ramo PDF e' stato davvero scelto.
        ok, ok_pdf, righe = 0, 0, []
        for d in GOLD:
            scelti = router.instrada(d["domanda"], client).rami
            accettati = {d["ramo"], "rules"} if d["ramo"] == "regolamento" else {d["ramo"]}
            giusto = bool(accettati & set(scelti))
            ok += giusto
            ok_pdf += d["ramo"] in scelti
            righe.append({"id": d["id"], "atteso": d["ramo"], "scelti": scelti, "ok": giusto})
            if not giusto:
                print(f"      x {d['id']} ({d['domanda']}): atteso {sorted(accettati)}, scelti {scelti}")
        print(f"  ramo accettabile tra i scelti: {ok}/{len(GOLD)};  il ramo PDF atteso e' stato scelto: {ok_pdf}/{len(GOLD)}")
        out["routing"] = {"corretti": ok, "ramo_pdf_scelto": ok_pdf, "totale": len(GOLD), "dettaglio": righe}

    RISULTATI.mkdir(exist_ok=True)
    percorso = RISULTATI / f"{datetime.now():%Y%m%d-%H%M%S}_formati.json"
    percorso.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSalvato: {percorso.relative_to(RADICE)}")


if __name__ == "__main__":
    main()
