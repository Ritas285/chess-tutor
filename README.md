# ♟️ Chess Tutor — tutor di scacchi per principianti

Progetto finale del corso AITHO GenAI Academy (datapizza-ai 0.1.0). Un principiante fa domande su regole, aperture, tattica,
finali e strategia; un agente capisce di cosa parla la domanda e cerca **solo nei documenti del ramo giusto** (RAG a rami),
cita le fonti e dice "Non lo so" quando non trova.

Il progetto si costruisce **a step**. Questo README cresce con gli step.

## Stato attuale: Step 1b — ricerca ibrida sul ramo `rules`
- **Step 1a — ingestione** (`chess_tutor/ingest.py`): documenti del ramo `rules` (`data/rules/`) → pezzi (chunk) → embedding → Qdrant,
  con il metodo della lezione S07.
- **Step 1b — ricerca** (`chess_tutor/retrieval.py`): ricerca per **significato** (embedding), per **parole esatte** (BM25) e
  **ibrida** (le due classifiche unite con RRF), con il metodo della lezione S08. `evals/confronta_ricerca.py` confronta i tre modi.

## Installazione (Windows, PowerShell, Python 3.12)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # poi apri .env e inserisci la tua OPENAI_API_KEY
```

## Provarlo
```powershell
python -m pytest -q                                                 # test (senza chiave girano quelli offline)
python -m chess_tutor.ingest "Come funziona l'arrocco?"             # indicizza il ramo rules e prova una ricerca per significato
python -m chess_tutor.retrieval "Cosa vuol dire O-O-O?" --confronta # i tre modi di ricerca uno sotto l'altro
python evals/confronta_ricerca.py                                   # tabella: solo significato, solo parole, ibrido
```
Le ultime tre righe usano la chiave OpenAI (frazioni di centesimo per prova).

## Cartelle
- `data/<ramo>/` — documenti `.md` scritti per il progetto (un ramo = una cartella)
- `chess_tutor/` — il codice
- `evals/` — domande di prova e script di confronto
- `tests/` — i test

## Fonti e licenze
I documenti in `data/` sono scritti per questo progetto. Eventuali documenti esterni (PDF) verranno elencati con fonte e licenza.
