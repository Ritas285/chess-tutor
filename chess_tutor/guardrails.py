"""Guardrail (Step 1e, lezione S15). Tutti DETERMINISTICI (codice normale, testabile senza chiave) e su passaggi diversi:

  input      -> controlla_domanda(): domanda vuota, troppo lunga o con un tentativo di injection: bloccata PRIMA di chiamare il modello
  retrieval  -> sanifica_documento(): i passaggi recuperati sono DATI; le righe che sembrano ordini vengono tolte prima del modello
  output     -> ripulisci_output(): via link esterni (canale di esfiltrazione: un'immagine markdown basta) e segreti
  grounding  -> ancora_citazioni(): una citazione [file.md] vale solo se quel documento è stato davvero recuperato in questo turno
  privilegi  -> (tutor.py) l'agente ha solo gli strumenti di ricerca: nessuna email, HTTP o scrittura di file
  audit      -> (audit.py) chi ha deciso cosa

Regola d'oro di S15: i controlli veri stanno FUORI dal modello. Il prompt (tutor.SYSTEM_PROMPT) è solo un livello in più.
Limite onesto: le regole a parole chiave si aggirano; per questo ci sono più barriere, e la prompt injection si mitiga, non si elimina.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CARATTERI_DOMANDA = 1000

_INIEZIONE = [
    r"ignor[ae]\s+(tutte\s+)?(le\s+)?(istruzioni|regole)", r"dimentica\s+(tutto|le\s+istruzioni)",
    r"ignore\s+(all\s+|the\s+)?(previous\s+|above\s+)?instructions", r"system\s*prompt", r"prompt\s+di\s+sistema",
    r"sei\s+ora\s+un", r"you\s+are\s+now", r"rivela\s+(le\s+)?(tue\s+)?istruzioni", r"reveal\s+your\s+(instructions|prompt)",
    r"IMPORTANT\s+(OPERATING\s+)?INSTRUCTION", r"(invia|manda|send)\s+.{0,40}(email|mail|http)",
    r"(api[_ -]?key|password|token|secret)\s*[:=]",
]
_RE_INIEZIONE = re.compile("|".join(_INIEZIONE), re.I)
_RE_FRASI = re.compile(r"(?<=[.!?])\s+")
_RE_URL = re.compile(r"https?://[^\s)\"'>\]]+")
_RE_SEGRETO = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+)", re.I)
_RE_CITAZIONE = re.compile(r"\[([^\[\]]+?\.(?:md|txt|pdf))(?:\s*›[^\]]*)?\]", re.I)


@dataclass
class Controlli:
    """Gli interruttori dei guardrail (come i flag `Controls` di S15): servono a mostrare il RETEST, lo stesso attacco
    con le barriere spente e poi accese. In uso normale sono tutti accesi."""
    input: bool = True
    documenti: bool = True
    output: bool = True
    citazioni: bool = True

    @classmethod
    def nessuno(cls) -> "Controlli":
        return cls(False, False, False, False)


@dataclass
class Verdetto:
    ok: bool
    motivo: str = ""


def controlla_domanda(testo: str) -> Verdetto:
    if not testo or not testo.strip():
        return Verdetto(False, "domanda vuota")
    if len(testo) > MAX_CARATTERI_DOMANDA:
        return Verdetto(False, f"domanda troppo lunga (massimo {MAX_CARATTERI_DOMANDA} caratteri)")
    if _RE_INIEZIONE.search(testo):
        return Verdetto(False, "la richiesta sembra voler cambiare le mie istruzioni: posso aiutarti solo con gli scacchi")
    return Verdetto(True)


def sanifica_documento(testo: str) -> tuple[str, list[str]]:
    """Neutralizza le FRASI che sembrano ordini per l'assistente (injection INDIRETTA: il veleno sta nel documento).
    Ritorna (testo ripulito, frasi sospette trovate).

    Si toglie la frase, non l'intera riga: il parser dei documenti può mettere un paragrafo su una riga sola, e togliere la riga
    butterebbe anche il contenuto buono (misurato col modello vero: risposta utile 5/5 -> 0/5, e un attaccante potrebbe far
    "sparire" un paragrafo aggiungendoci una frase sospetta)."""
    sospette, righe = [], []
    for riga in testo.splitlines():
        frasi = _RE_FRASI.split(riga)
        if not any(_RE_INIEZIONE.search(f) for f in frasi):
            righe.append(riga)
            continue
        nuove = []
        for frase in frasi:
            if _RE_INIEZIONE.search(frase):
                sospette.append(frase.strip()[:80])
                nuove.append("[testo rimosso: sembrava un'istruzione nascosta nel documento]")
            else:
                nuove.append(frase)
        righe.append(" ".join(nuove))
    return "\n".join(righe), sospette


def ripulisci_output(testo: str, domini_ammessi: tuple[str, ...] = ()) -> tuple[str, list[str]]:
    """Tratta l'output del modello come input NON fidato: via i link esterni (un'immagine markdown basta a far uscire dati,
    senza nessun tool) e i segreti. Il tutor non ha bisogno di link: `domini_ammessi` è vuoto."""
    motivi: list[str] = []

    def _url(m: re.Match) -> str:
        host = m.group(0).split("/")[2]
        if any(host.endswith(d) for d in domini_ammessi):
            return m.group(0)
        motivi.append(f"link esterno rimosso ({host})")
        return "[link rimosso]"

    pulito = _RE_URL.sub(_url, testo)
    if _RE_SEGRETO.search(pulito):
        pulito = _RE_SEGRETO.sub("[segreto rimosso]", pulito)
        motivi.append("possibile segreto rimosso")
    return pulito, motivi


def ancora_citazioni(testo: str, fonti_recuperate: list[str]) -> tuple[str, list[str]]:
    """Toglie le citazioni a file che NON sono tra i passaggi recuperati in questo turno (fonti inventate o riprese dalla
    memoria del modello). `fonti_recuperate` ha voci come "03_mosse_speciali.md › L'arrocco". (Idea dell'hackathon:
    fix_citations nel codice, perché il prompt da solo non bastava.)"""
    ammessi = {f.split("›")[0].strip().lower() for f in fonti_recuperate}
    motivi: list[str] = []

    def _verifica(m: re.Match) -> str:
        nome = m.group(1).strip().lower()
        if nome in ammessi:
            return m.group(0)
        motivi.append(f"citazione non ancorata rimossa ({m.group(1).strip()})")
        return "[fonte non verificata]"

    return _RE_CITAZIONE.sub(_verifica, testo), motivi
