"""Lettura dei PDF per i rami della conoscenza (Step 6: confronto md contro PDF).

Un Markdown dice da solo dove cominciano le sezioni (il parser ne fa un pezzo ciascuna, con il titolo davanti). Un PDF no: è
testo spezzato in righe visive, con intestazioni su ogni pagina, numeri di pagina e, nei manuali di scacchi, diagrammi che
diventano righe senza senso ("XABCDEFGHY", "8rsnlwqk+-tr("). Qui si fa il minimo per renderlo cercabile, senza inventare struttura:

  1. si legge pagina per pagina con pypdf (il numero di pagina serve a citare la fonte: "file.pdf › p. 6");
  2. si tolgono le righe che si ripetono su ogni pagina (intestazione, percorso del file Word) e le righe dei diagrammi;
  3. si riuniscono le sillabazioni ("frat-\\ntempo") e le righe in un solo testo;
  4. si fanno pezzi di al più CHUNK_MAX_CHAR caratteri, a fine frase, dentro la stessa pagina, con "[titolo — p. N]" davanti
     (come per i .md: stesso contextual retrieval, ma la "sezione" è la pagina).

I PDF NON stanno nel git (diritti non liberi): vedi README. Le funzioni qui sotto non dipendono da quali PDF ci siano.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from datapizza.core.models import PipelineComponent
from datapizza.type import Chunk
from pypdf import PdfReader

from . import config

# righe che si ripetono su ogni pagina (testate): percorso del file Word, testata della Federazione, titolo corrente
_TESTATE = [
    re.compile(r"^[A-Za-z]:\\.*\.docx?\s+\d+\s*$"),                                  # "E:\documenti\...\Corso.doc  12"
    re.compile(r"^Federazione Scacchistica Italiana.*Pag\.\s*\d+\s*/\s*\d+\s*$"),    # "Federazione ... Pag. 6/10"
    re.compile(r"^Manualetto di scacchi\s*$"),                                       # titolo corrente del manuale
    re.compile(r"^\s*\d{1,3}\s*$"),                                                  # numero di pagina da solo
]
# diagrammi scritti con un carattere speciale: ogni riga della scacchiera diventa "8rsnlwqk+-tr(" o "4-+R+-+-+$"
_DIAGRAMMA = re.compile(r"^[1-8][A-Za-z+\-]{8,12}[()$#%&'!\"]$|^[xX]ABCDEFGHY$|^xabcdefghy$")


def titolo_da_nome(percorso: Path) -> str:
    """Il titolo del documento, dal nome del file ("FSI_regole_di_base.pdf" -> "FSI regole di base")."""
    return re.sub(r"[_\s]+", " ", percorso.stem).strip()


def pulisci_pagina(testo: str) -> str:
    """Il testo di UNA pagina, senza testate né diagrammi, con le righe riunite in un solo paragrafo."""
    righe = []
    for riga in testo.splitlines():
        r = riga.strip()
        if not r or _DIAGRAMMA.match(r) or any(t.match(r) for t in _TESTATE):
            continue
        righe.append(r)
    unito = ""
    for r in righe:
        if unito.endswith("-") and r[:1].islower():          # "frat-" + "tempo" -> "frattempo"
            unito = unito[:-1] + r
        else:
            unito = f"{unito} {r}" if unito else r
    return re.sub(r"\s+", " ", unito).strip()


def spezza(testo: str, massimo: int | None = None) -> list[str]:
    """Pezzi di al più `massimo` caratteri, a fine frase (se una frase da sola è più lunga, si taglia sugli spazi)."""
    massimo = massimo or config.CHUNK_MAX_CHAR
    frasi = re.split(r"(?<=[.!?:;])\s+", testo)
    pezzi, corrente = [], ""
    for frase in frasi:
        while len(frase) > massimo:                           # frase lunghissima (elenchi, diagrammi rimasti): taglio sugli spazi
            taglio = frase.rfind(" ", 0, massimo) or massimo
            if corrente:
                pezzi.append(corrente)
                corrente = ""
            pezzi.append(frase[:taglio].strip())
            frase = frase[taglio:].strip()
        if corrente and len(corrente) + 1 + len(frase) > massimo:
            pezzi.append(corrente)
            corrente = frase
        else:
            corrente = f"{corrente} {frase}".strip()
    if corrente:
        pezzi.append(corrente)
    return [p for p in pezzi if p]


def pezzi_del_pdf(percorso: Path, minimo: int = 40) -> list[tuple[int, str]]:
    """[(numero di pagina da 1, testo del pezzo)] per tutto il PDF. Le pagine con meno di `minimo` caratteri (copertine,
    pagine di sole immagini) non danno pezzi."""
    risultato = []
    for numero, pagina in enumerate(PdfReader(str(percorso)).pages, 1):
        testo = pulisci_pagina(pagina.extract_text() or "")
        if len(testo) < minimo:
            continue
        risultato.extend((numero, p) for p in spezza(testo))
    return risultato


class LeggiPdf(PipelineComponent):
    """Primo passo della pipeline per un PDF: percorso del file -> lista di Chunk (poi ci pensa ChunkEmbedder).
    Fa da parser e da splitter insieme e mette già "[titolo — p. N]" davanti: non serve AggiungiTitolo."""

    def _run(self, file_path: str) -> list[Chunk]:
        percorso = Path(file_path)
        titolo = titolo_da_nome(percorso)
        return [Chunk(id=str(uuid.uuid4()), text=f"[{titolo} — p. {n}]\n{t}",
                      metadata={"titolo": titolo, "sezione": f"p. {n}", "pagina": n})
                for n, t in pezzi_del_pdf(percorso)]

    async def _a_run(self, file_path: str) -> list[Chunk]:
        return self._run(file_path)
