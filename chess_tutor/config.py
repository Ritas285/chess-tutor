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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Come in tutto il corso: gpt-4o-mini per le risposte, text-embedding-3-small per gli embedding (1536 numeri per testo)
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMB_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMB_DIM = 1536
EMB_NAME = "content_embedding"                  # il nome del vettore deve essere lo stesso in collection, embedder e ricerca

# Le due "manopole" del chunking (S07): dimensione massima del pezzo e sovrapposizione tra pezzi consecutivi
CHUNK_MAX_CHAR = 1024
CHUNK_OVERLAP = 128


@dataclass(frozen=True)
class Branch:
    key: str            # nome della cartella in data/ e della collection
    label: str          # nome per l'utente
    description: str    # cosa contiene: lo leggerà il router (Step 1c) per scegliere il ramo


BRANCHES: dict[str, Branch] = {b.key: b for b in [
    Branch("rules", "Regole e notazione",
           "Come si muovono i pezzi, scacco/matto/stallo/patta, arrocco, en passant, promozione, valore dei pezzi, "
           "notazione algebrica."),
]}
