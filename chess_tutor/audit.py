"""Audit trail minimo (S15): "quale dato è entrato, quale decisione, chi ha autorizzato". Una riga JSON per domanda in
logs/audit.jsonl (la cartella è ignorata da git). Si registra COSA è successo, non il testo della risposta: la domanda è
troncata a 120 caratteri e non ci sono dati dell'utente oltre a quella."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def scrivi(percorso: Path, domanda: str, risposta) -> None:
    """`risposta` è un tutor.Risposta. Non solleva mai: un problema col registro non deve fermare il tutor."""
    try:
        percorso.parent.mkdir(parents=True, exist_ok=True)
        riga = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "domanda": domanda[:120],
            "bloccata": risposta.bloccata,
            "fuori_tema": risposta.fuori_tema,
            "rami": risposta.rami,
            "strumenti": risposta.tool_usati,
            "fonti": risposta.fonti,
            "note": risposta.note,
            "token": [risposta.token_prompt, risposta.token_completati],
            "latenza_s": risposta.latenza_s,
        }
        with percorso.open("a", encoding="utf-8") as f:
            f.write(json.dumps(riga, ensure_ascii=False) + "\n")
    except OSError:
        pass
