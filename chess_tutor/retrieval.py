"""Ricerca per ramo: significato (embedding) + parole esatte (BM25) + fusione RRF. (Step 1b, metodo della lezione S08)

  dense  = ricerca per SIGNIFICATO: trova testi che parlano della stessa cosa, anche con parole diverse
  bm25   = ricerca per PAROLE: trova le parole esatte (come un "Cerca" intelligente): utile per simboli come O-O-O
  ibrido = le due classifiche unite con RRF (Reciprocal Rank Fusion): un risultato in alto in entrambe vince
"""
from __future__ import annotations

import argparse
import re
import unicodedata

from rank_bm25 import BM25Okapi

from . import config, ingest

MODI = ("dense", "bm25", "ibrido")
K0_RRF = 60      # valore standard del corso (S08): non va "tarato"
POOL = 10        # quanti candidati prende ciascuna ricerca prima della fusione


def tokenizza(testo: str) -> list[str]:
    """Spezza un testo in parole per BM25. Parte dal tokenizzatore di S08 (`[a-z0-9][a-z0-9\\-_/.]*`, che tiene insieme
    codici come INC-2026-051 e quindi anche O-O-O) con adattamenti per l'italiano e la notazione scacchistica,
    scelti misurando (vedi evals/confronta_ricerca.py):
      - via gli accenti (perché = perche: chi scrive spesso li omette);
      - via la punteggiatura finale ("arrocco." deve combaciare con "arrocco");
      - restano i simboli = # + (e8=D, #, +)."""
    t = unicodedata.normalize("NFD", testo.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return [x.rstrip(".-_/") for x in re.findall(r"[a-z0-9#=+][a-z0-9\-_/.=#+]*", t)]


def tokenizza_corso(testo: str) -> list[str]:
    """Il tokenizzatore di S08 così com'è (solo per il confronto negli esperimenti)."""
    return re.findall(r"[a-z0-9][a-z0-9\-_/.]*", testo.lower())


def rrf(classifiche: list[list[int]], k0: int = K0_RRF) -> list[int]:
    """Unisce più classifiche (liste di posizioni dei chunk, dal migliore). Ogni risultato prende 1/(k0 + posizione)
    da ogni classifica in cui compare; poi si ordina per punteggio totale (formula di S08)."""
    punti: dict[int, float] = {}
    for classifica in classifiche:
        for posizione, i in enumerate(classifica):
            punti[i] = punti.get(i, 0.0) + 1.0 / (k0 + posizione)
    return sorted(punti, key=punti.get, reverse=True)


class Ricerca:
    """Cerca nei chunk di UN ramo (già indicizzati con ingest.indicizza_ramo)."""

    def __init__(self, vs, embedder, ramo: str, tokenizzatore=None):
        self.vs, self.embedder, self.ramo = vs, embedder, ramo
        self.chunks = ingest.chunk_del_ramo(vs, ramo)
        self._posizione = {str(c.id): i for i, c in enumerate(self.chunks)}
        self._tok = tokenizzatore or tokenizza
        self._token_chunk = [set(self._tok(c.text)) for c in self.chunks]
        self._bm25 = BM25Okapi([self._tok(c.text) for c in self.chunks]) if self.chunks else None

    def _classifica_dense(self, domanda: str, n: int) -> list[int]:
        trovati = ingest.cerca(self.vs, self.embedder, self.ramo, domanda, n)
        return [self._posizione[str(c.id)] for c in trovati if str(c.id) in self._posizione]

    def _classifica_bm25(self, domanda: str, n: int) -> list[int]:
        """Solo i chunk che contengono almeno una parola della domanda: con corpora minuscoli BM25 può dare punteggi
        nulli o negativi anche a chunk che combaciano, quindi il criterio è la parola in comune, non punteggio > 0."""
        if not self._bm25:
            return []
        parole = self._tok(domanda)
        punteggi = self._bm25.get_scores(parole)
        con_parole = [i for i, tokens in enumerate(self._token_chunk) if tokens & set(parole)]
        return sorted(con_parole, key=lambda i: punteggi[i], reverse=True)[:n]

    def cerca(self, domanda: str, k: int = 3, modo: str = "ibrido") -> list:
        if modo not in MODI:
            raise ValueError(f"modo sconosciuto: {modo}. Validi: {', '.join(MODI)}")
        pool = max(k, POOL)
        classifiche = []
        if modo in ("dense", "ibrido"):
            classifiche.append(self._classifica_dense(domanda, pool))
        if modo in ("bm25", "ibrido"):
            classifiche.append(self._classifica_bm25(domanda, pool))
        ordine = rrf(classifiche) if modo == "ibrido" else classifiche[0]
        return [self.chunks[i] for i in ordine[:k]]


def crea_ricerche(embedder, rami=None, vs=None, data_dir=None) -> dict[str, Ricerca]:
    """Indicizza i rami (tutti, se non se ne indicano) e restituisce una Ricerca per ramo: {"rules": ..., "openings": ...}.
    `data_dir` serve ai test, per indicizzare una cartella diversa da data/ (es. con un documento "avvelenato")."""
    vs = vs or ingest.crea_vector_store()
    ricerche = {}
    for ramo in rami or config.BRANCHES:
        ingest.indicizza_ramo(vs, embedder, ramo, data_dir=data_dir, verbose=False)
        ricerche[ramo] = Ricerca(vs, embedder, ramo)
    return ricerche


def _stampa(titolo: str, risultati: list) -> None:
    print(f"  {titolo}")
    if not risultati:
        print("     (nessun risultato)")
    for i, h in enumerate(risultati, 1):
        print(f"     {i}. [{ingest.etichetta(h)}] {ingest.anteprima(h)}…")


def main() -> None:
    ap = argparse.ArgumentParser(description="Cerca nei documenti di un ramo. Serve OPENAI_API_KEY (frazioni di centesimo).")
    ap.add_argument("domanda", nargs="?", default="Cosa vuol dire O-O-O?")
    ap.add_argument("--ramo", default="rules", choices=list(config.BRANCHES))
    ap.add_argument("--modo", default="ibrido", choices=MODI)
    ap.add_argument("--confronta", action="store_true", help="mostra i tre modi uno sotto l'altro")
    ap.add_argument("-k", type=int, default=3)
    args = ap.parse_args()

    embedder, vs = ingest.crea_embedder(), ingest.crea_vector_store()
    ingest.indicizza_ramo(vs, embedder, args.ramo, verbose=False)
    ricerca = Ricerca(vs, embedder, args.ramo)
    print(f"Domanda: {args.domanda}")
    for modo in (MODI if args.confronta else (args.modo,)):
        _stampa(f"modo '{modo}':", ricerca.cerca(args.domanda, args.k, modo))


if __name__ == "__main__":
    main()
