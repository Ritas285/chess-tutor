"""Confronto md contro PDF (Step 6): aiuti per misurare il retrieval in modo indipendente dal formato.

Il gold dei rami PDF (evals/gold_pdf.json) non dice "il file giusto è X" (con un PDF solo non avrebbe senso, e un .md ha altri
nomi di sezione) ma "la risposta sta nel pezzo che contiene QUESTA frase". Un pezzo è giusto se contiene una delle frasi,
confrontate senza accenti, maiuscole, spazi e punteggiatura. Così si misura lo stesso gold su pezzi tagliati in modi diversi.

`pdf_a_md` serve alla PROVA CONTROLLATA: stesso testo di un PDF, scritto come Markdown con le sezioni, per vedere cosa cambia
quando il formato dice dove cominciano gli argomenti (e il testo, parola per parola, è lo stesso).
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from . import pdf


def norma(testo: str) -> str:
    """Solo lettere minuscole senza accento e cifre: ‘Il Cavallo, ’ e "il cavallo" diventano uguali."""
    t = unicodedata.normalize("NFD", testo.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def posizione_della_risposta(testi: list[str], frasi: list[str]) -> int | None:
    """Il posto (da 1) del primo pezzo che contiene una delle frasi; None se nessuno la contiene."""
    cercate = [norma(f) for f in frasi if norma(f)]
    for posto, testo in enumerate(testi, 1):
        t = norma(testo)
        if any(f in t for f in cercate):
            return posto
    return None


def metriche(posizioni: list[int | None], massimo: int = 5) -> dict:
    """primo = la risposta è nel primo pezzo; top3 = è tra i primi 3; mrr = media di 1/posto (0 oltre `massimo`)."""
    n = len(posizioni)
    if not n:
        return {"n": 0, "primo": 0.0, "top3": 0.0, "mrr": 0.0}
    return {"n": n,
            "primo": sum(p == 1 for p in posizioni) / n,
            "top3": sum(p is not None and p <= 3 for p in posizioni) / n,
            "mrr": sum(1 / p for p in posizioni if p is not None and p <= massimo) / n}


def _titolo(riga: str, prima_vuota: bool, dopo_piena: bool) -> bool:
    """Una riga che sembra un titolo: corta, senza punteggiatura finale, maiuscola iniziale, isolata tra righe vuote."""
    r = riga.strip()
    if not r or "   " in r or len(r.split()) > 7 or r[-1] in ".:;,…" or not r[0].isupper():
        return False
    return prima_vuota and dopo_piena


def pdf_a_md(percorso: Path) -> str:
    """Lo STESSO testo del PDF come Markdown: titoli (righe tutte maiuscole o corte e isolate) diventano "## ", il resto sono
    paragrafi. Toglie testate e diagrammi come fa la lettura dei PDF. Funziona su documenti semplici (regolamento FSI),
    non è un convertitore generale."""
    righe: list[str] = []
    for pagina in PdfReader(str(percorso)).pages:
        for riga in (pagina.extract_text() or "").splitlines():
            r = riga.strip()
            if r and (pdf._DIAGRAMMA.match(r) or any(t.match(r) for t in pdf._TESTATE)):
                continue
            righe.append(riga.rstrip())
        righe.append("")                                                  # confine di pagina = riga vuota
    sezioni: list[tuple[str, list[str]]] = [("", [])]
    for i, riga in enumerate(righe):
        r = riga.strip()
        prima_vuota = i == 0 or not righe[i - 1].strip()
        dopo_piena = i + 1 < len(righe) and bool(righe[i + 1].strip())
        if r and r.isupper() and len(r) > 6:                              # titolo in maiuscolo; due righe di fila = un titolo
            if sezioni[-1][1] == [] and sezioni[-1][0]:
                sezioni[-1] = (f"{sezioni[-1][0]} {r.capitalize()}", [])
            else:
                sezioni.append((r.capitalize(), []))
        elif r and _titolo(riga, prima_vuota, dopo_piena):
            sezioni.append((r, []))
        elif r:
            sezioni[-1][1].append(r)
    titolo_doc = pdf.titolo_da_nome(percorso)
    parti = [f"# {titolo_doc}", ""]
    for titolo, corpo in sezioni:
        testo = ""
        for r in corpo:
            testo = testo[:-1] + r if testo.endswith("-") and r[:1].islower() else f"{testo} {r}".strip()
        testo = re.sub(r"\s+", " ", testo).strip()
        if not testo:
            continue
        if titolo:
            parti += [f"## {titolo}", ""]
        parti += [testo, ""]
    return "\n".join(parti)
