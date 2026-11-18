"""Crea un PDF semplice (solo testo) per i test: nessuna libreria in più, nessun PDF vero nel repository (diritti)."""
from __future__ import annotations

from pathlib import Path


def _esc(riga: str) -> str:
    return riga.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def crea_pdf(percorso: Path, pagine: list[list[str]]) -> Path:
    """`pagine` = per ogni pagina la lista delle sue righe di testo (come le estrae pypdf: una riga visiva per volta)."""
    n = len(pagine)
    oggetti = ["<< /Type /Catalog /Pages 2 0 R >>",
               f"<< /Type /Pages /Kids [{' '.join(f'{4 + 2 * i} 0 R' for i in range(n))}] /Count {n} >>",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    for i, righe in enumerate(pagine):
        flusso = "BT /F1 11 Tf 14 TL 40 800 Td " + " ".join(f"({_esc(r)}) Tj T*" for r in righe) + " ET"
        oggetti.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> "
                       f"/Contents {5 + 2 * i} 0 R >>")
        oggetti.append(f"<< /Length {len(flusso.encode('latin-1'))} >>\nstream\n{flusso}\nendstream")
    corpo, offset = b"%PDF-1.4\n", []
    for k, o in enumerate(oggetti, 1):
        offset.append(len(corpo))
        corpo += f"{k} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(corpo)
    corpo += f"xref\n0 {len(oggetti) + 1}\n0000000000 65535 f \n".encode()
    corpo += "".join(f"{o:010d} 00000 n \n" for o in offset).encode()
    corpo += f"trailer\n<< /Size {len(oggetti) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    percorso.write_bytes(corpo)
    return percorso
