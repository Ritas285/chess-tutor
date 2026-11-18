#!/usr/bin/env python3
"""Controlla con python-chess che le mosse scritte nei documenti di data/ siano legali. Nessuna chiave, nessuna rete, pochi secondi.

    python evals/verifica_contenuti.py

Esce con codice 1 se trova una sequenza non legale (da correggere nel documento). Serve dopo ogni modifica ai file in data/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chess_tutor.contenuti import controlla_documenti  # noqa: E402


def main() -> int:
    sequenze, problemi = controlla_documenti()
    print(f"Sequenze di mosse trovate nei documenti: {len(sequenze)}")
    for s in sequenze:
        print(f"  {s.file}:{s.riga}  {' '.join(s.mosse)}")
    if problemi:
        print(f"\nNON LEGALI: {len(problemi)}")
        for p in problemi:
            print(f"  {p.sequenza.file}:{p.sequenza.riga}  mossa {p.mossa_numero} «{p.mossa}» di «{' '.join(p.sequenza.mosse)}»: {p.messaggio}")
        return 1
    print("\nTutte le sequenze sono legali.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
