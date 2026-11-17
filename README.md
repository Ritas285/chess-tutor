# ♟️ Chess Tutor — tutor di scacchi per principianti

Progetto finale del corso AITHO GenAI Academy (datapizza-ai 0.1.0). Un principiante fa domande su regole, aperture, tattica,
finali e strategia; un agente capisce di cosa parla la domanda e cerca **solo nei documenti del ramo giusto** (RAG a rami),
cita le fonti e dice "Non lo so" quando non trova.

Il progetto si costruisce **a step**. Questo README cresce con gli step.

## Stato attuale: Step 1a — corpus e ingestione del ramo `rules`
Cosa c'è: i documenti del ramo `rules` (`data/rules/`), la configurazione dei rami (`chess_tutor/config.py`) e l'ingestione
(`chess_tutor/ingest.py`): documento → pezzi (chunk) → embedding → Qdrant, con il metodo della lezione S07.

## Installazione (Windows, PowerShell, Python 3.12)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # poi apri .env e inserisci la tua OPENAI_API_KEY
```

## Provarlo
```powershell
python -m pytest -q                                    # test (senza chiave girano quelli offline)
python -m chess_tutor.ingest                           # indicizza il ramo rules e prova una ricerca (usa la chiave: frazioni di centesimo)
python -m chess_tutor.ingest "Quanto vale la donna?"   # un'altra domanda
```

## Cartelle
- `data/<ramo>/` — documenti `.md` scritti per il progetto (un ramo = una cartella)
- `chess_tutor/` — il codice
- `tests/` — i test

## Fonti e licenze
I documenti in `data/` sono scritti per questo progetto. Eventuali documenti esterni (PDF) verranno elencati con fonte e licenza.
