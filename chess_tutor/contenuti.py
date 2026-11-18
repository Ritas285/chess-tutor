"""Verifica delle mosse scritte nei DOCUMENTI del corpus (data/**/*.md) con python-chess (Step 3: regola n. 1 di AGENTS.md).

Un documento che dice "1.e4 e5 2.Cf3 Cc6 3.Ac5" con una mossa impossibile insegna una cosa falsa a un principiante, e il tutor la
ripeterebbe con la fonte. Qui si cercano le sequenze che iniziano con "1." e si giocano dalla posizione iniziale: la prima mossa non
legale è un errore da correggere nel documento.

    python evals/verifica_contenuti.py            # esce con codice 1 se trova una sequenza non legale
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import config
from .chess_tools import gioca_sequenza, START

# una mossa in notazione italiana (o inglese), con segni finali (+ # ? !) già tolti
_MOSSA = re.compile(r"^(?:[KQRBNADTC]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBNDTAC])?|O-O(?:-O)?)[+#]?$")
_INIZIO = re.compile(r"(?<![\w.])1\.(?!\.)")            # "1." che non fa parte di "3.1" né di "1..."
_NUMERO = re.compile(r"^\d+\.{1,3}")


@dataclass
class Sequenza:
    file: str
    riga: int
    mosse: list[str]


def estrai_sequenze(testo: str, file: str = "") -> list[Sequenza]:
    """Le sequenze di mosse che iniziano con "1." in un testo. Si ferma alla prima parola che non è una mossa o a un punto finale."""
    trovate = []
    for numero_riga, riga in enumerate(testo.splitlines(), 1):
        for inizio in _INIZIO.finditer(riga):
            mosse: list[str] = []
            for token in riga[inizio.start():].split():
                fine = token[-1] in ".,;:)" and not _NUMERO.fullmatch(token) and not token.endswith("...")
                pulito = _NUMERO.sub("", token).rstrip(".,;:)").rstrip("?!")
                if not pulito and _NUMERO.fullmatch(token):         # un numero di mossa isolato: "2."
                    continue
                if not _MOSSA.match(pulito.rstrip("+#") + ("+" if pulito.endswith("+") else "#" if pulito.endswith("#") else "")):
                    break
                mosse.append(pulito)
                if fine:
                    break
            if mosse:
                trovate.append(Sequenza(file, numero_riga, mosse))
    return trovate


@dataclass
class Problema:
    sequenza: Sequenza
    mossa_numero: int
    mossa: str
    messaggio: str


def controlla_sequenze(sequenze: list[Sequenza]) -> list[Problema]:
    """Gioca ogni sequenza dalla posizione iniziale. -> le sequenze che a un certo punto non sono legali."""
    problemi = []
    for s in sequenze:
        esito = gioca_sequenza(START, ", ".join(s.mosse))
        if esito.errore:
            quale, testo, e = esito.errore
            problemi.append(Problema(s, quale, testo, e.messaggio))
    return problemi


def controlla_documenti(cartella: Path | None = None) -> tuple[list[Sequenza], list[Problema]]:
    """Tutte le sequenze nei .md di `data/` (o di un'altra cartella) e i problemi trovati."""
    radice = Path(cartella) if cartella else config.DATA_DIR
    sequenze: list[Sequenza] = []
    for f in sorted(radice.rglob("*.md")):
        sequenze += estrai_sequenze(f.read_text(encoding="utf-8"), str(f.relative_to(radice)))
    return sequenze, controlla_sequenze(sequenze)
