"""Router: capisce di cosa parla la domanda e sceglie in quali rami cercare. (Step 1c)

È una piccola chiamata al modello che compila un "modulo" (output strutturato con Pydantic, come i giudici di S08):
se la domanda riguarda gli scacchi, quali rami, quanto è sicuro. Poi l'agente riceve SOLO gli strumenti di ricerca di quei rami.

Come è stato progettato il prompt (misurato su domande di storia degli scacchi, che il modello scartava come "fuori tema"):
  - prompt "è fuori tema?" in negativo: 3/18 storia non scartata; con 4 esempi: 10/18
  - domanda in POSITIVO ("riguarda gli scacchi?"): 5/18; in positivo + 4 esempi: 18/18  <- scelta
Nessuna delle due idee da sola bastava.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from . import config


class RouteOut(BaseModel):
    """Il modulo che il modello compila. Tutti i campi obbligatori, niente valori predefiniti né vincoli numerici:
    così è compatibile con gli output strutturati rigidi di OpenAI."""
    about_chess: bool = Field(description=(
        "true se la domanda ha a che fare con gli scacchi in qualunque modo: regole, aperture, tattica, finali, strategia, "
        "ma anche storia degli scacchi, campioni, tornei, curiosità, computer che giocano a scacchi. "
        "false solo se parla d'altro (cucina, sport, meteo, calcoli...)"))
    branches: list[str] = Field(description="chiavi dei rami più vicini all'argomento (almeno uno se about_chess è true), al massimo due")
    confidence: float = Field(description="quanto sei sicuro, da 0 a 1")


ESEMPI = (
    "\nESEMPI:\n"
    "- \"Chi era Garry Kasparov?\" -> about_chess=true (storia degli scacchi), ramo più vicino\n"
    "- \"Quando sono nati gli scacchi?\" -> about_chess=true (storia degli scacchi), ramo più vicino\n"
    "- \"Chi ha vinto il Mondiale di calcio?\" -> about_chess=false\n"
    "- \"Cosa significa Cxe5?\" -> about_chess=true (notazione degli scacchi: mosse e simboli senza la parola \"scacchi\"), ramo più vicino\n"
    "- \"Mi dai una ricetta per la pizza?\" -> about_chess=false"
)


def prompt_router() -> str:
    """Le descrizioni dei rami vengono da config.py: aggiungere un ramo lo rende subito visibile al router."""
    rami = "\n".join(f"- {b.key}: {b.description}" for b in config.BRANCHES.values())
    return (
        "Sei il router di un tutor di scacchi per principianti. Prima di tutto decidi se la domanda riguarda gli scacchi "
        "(about_chess). Poi scegli in quali rami della conoscenza cercare (uno, o due se la domanda tocca due temi). "
        "Se riguarda gli scacchi scegli comunque il ramo più vicino, anche quando i rami non contengono la risposta: "
        "sarà l'agente a dire che nei documenti non c'è. Rami:\n" + rami + ESEMPI
    )


@dataclass
class Decisione:
    rami: list[str]
    fuori_tema: bool = False
    confidenza: float = 0.0
    token_prompt: int = 0
    token_completati: int = 0
    ripiego: bool = False        # True se il router non ha dato una scelta valida: si cerca in TUTTI i rami


def _token(risposta) -> tuple[int, int]:
    uso = getattr(risposta, "usage", None)
    return int(getattr(uso, "prompt_tokens", 0) or 0), int(getattr(uso, "completion_tokens", 0) or 0)


def instrada(domanda: str, client) -> Decisione:
    """Decide i rami. Se la chiamata fallisce o la scelta non è valida NON si blocca l'utente: si dà all'agente
    ogni ramo (costa un po' di più, ma risponde)."""
    try:
        risposta = client.structured_response(input=domanda, output_cls=RouteOut, system_prompt=prompt_router())
        out = risposta.structured_data[0]
    except Exception:       # noqa: BLE001 - qualunque errore del servizio: ripiego
        return Decisione(rami=list(config.BRANCHES), ripiego=True)
    tp, tc = _token(risposta)
    confidenza = min(1.0, max(0.0, float(out.confidence)))
    if not out.about_chess:
        return Decisione(rami=[], fuori_tema=True, confidenza=confidenza, token_prompt=tp, token_completati=tc)
    rami = [r for r in dict.fromkeys(out.branches) if r in config.BRANCHES][:2]     # via doppioni e rami inventati
    if not rami:
        return Decisione(rami=list(config.BRANCHES), confidenza=confidenza, token_prompt=tp, token_completati=tc, ripiego=True)
    return Decisione(rami=rami, confidenza=confidenza, token_prompt=tp, token_completati=tc)
