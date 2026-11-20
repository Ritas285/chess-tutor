"""Configurazione: percorsi, modelli e rami della conoscenza. Un solo posto da modificare.

Aggiungere un ramo = una voce in BRANCHES + una cartella in data/<ramo>/ con i documenti .md.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")                      # la chiave sta solo in .env (mai nel git)

DATA_DIR = ROOT / "data"
AUDIT_PATH = ROOT / "logs" / "audit.jsonl"      # registro di cosa decide il tutor (cartella ignorata da git)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Come in tutto il corso: gpt-4o-mini per le risposte, text-embedding-3-small per gli embedding (1536 numeri per testo)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMB_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMB_DIM = 1536
PRICE_IN, PRICE_OUT = 0.15, 0.60                # $ per 1M token (gpt-4o-mini, listino del corso): per stimare il costo a domanda
# Il listino è in dollari; l'app mostra il costo in euro con un cambio APPROSSIMATO e fisso (non è un cambio in tempo reale):
# si cambia con EUR_PER_USD nel .env. Metriche (Prometheus/Grafana) e misure (evals) restano in dollari.
EUR_PER_USD = float(os.getenv("EUR_PER_USD", "0.92"))
EMB_NAME = "content_embedding"                  # il nome del vettore deve essere lo stesso in collection, embedder e ricerca

# Manopola del chunking (S07): dimensione massima di un pezzo. Con NodeSplitter (che non ha sovrapposizione) ogni SEZIONE
# del documento diventa un pezzo, finché sta sotto questo limite; una sezione più lunga viene spezzata per paragrafi.
CHUNK_MAX_CHAR = 1024


@dataclass(frozen=True)
class Branch:
    key: str            # nome della cartella in data/ e della collection
    label: str          # nome per l'utente
    description: str    # cosa contiene: lo leggerà il router (Step 1c) per scegliere il ramo


BRANCHES: dict[str, Branch] = {b.key: b for b in [
    Branch("rules", "Regole e notazione",
           "Come si muovono i pezzi, scacco/matto/stallo/patta, arrocco, en passant, promozione, valore dei pezzi, "
           "notazione algebrica."),
    Branch("openings", "Aperture",
           "Principi di apertura, Italiana, Spagnola, Siciliana, Francese, Gambetto di Donna, Londra, Indiana di Re, "
           "trappole e matti rapidi (matto del barbiere, matto del pazzo)."),
    Branch("tactics", "Tattiche",
           "Tattiche per vincere materiale: forchetta (attacco doppio), inchiodatura, infilata, scacco di scoperta, forchetta di "
           "pedone, pezzi indifesi, come cercare una tattica e come difendersi dalle minacce dell'avversario."),
]}

# Rami OPZIONALI con documenti PDF trovati online (Step 6, prova md contro PDF). I PDF non stanno nel git (diritti
# non liberi, vedi README): il ramo esiste solo se RAMI_PDF=1 (nel .env o nell'ambiente) E la cartella data/<ramo>/ contiene PDF.
# Senza, il progetto si comporta esattamente come prima (stessi rami, stesse misure, stessi test).
RAMI_PDF: list[Branch] = [
    Branch("regolamento", "Regolamento (PDF)",
           "Regolamento di base della Federazione Scacchistica Italiana: obiettivo della partita, scacchiera e posizione iniziale, "
           "movimento e cattura dei pezzi, presa en passant, promozione, arrocco, mosse legali e illegali, regola del pezzo "
           "toccato, fine della partita (scaccomatto, stallo, patta, 50 mosse)."),
    Branch("corsi", "Corsi per principianti (PDF)",
           "Manuale e dispensa per principianti: matti elementari (matto in fondo, re e donna o re e torre contro re), finali di "
           "pedone (regola del quadrato), temi tattici (forchetta, infilata, scoperta, doppio, matto affogato), controllo del "
           "centro, valore e importanza dei pezzi, consigli per le mosse iniziali."),
]


def rami_attivi(base: dict[str, Branch], extra: list[Branch], data_dir: Path, abilitati: bool) -> dict[str, Branch]:
    """I rami di `base` e, se `abilitati`, anche quelli di `extra` che hanno davvero dei PDF in data_dir/<ramo>/."""
    rami = dict(base)
    if abilitati:
        for b in extra:
            if any((data_dir / b.key).glob("*.pdf")):
                rami[b.key] = b
    return rami


BRANCHES = rami_attivi(BRANCHES, RAMI_PDF, DATA_DIR, os.getenv("RAMI_PDF") == "1")
