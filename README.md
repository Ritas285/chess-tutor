# ♟️ Chess Tutor — tutor di scacchi per principianti

Progetto finale del corso AITHO GenAI Academy (datapizza-ai 0.1.0). Un principiante fa domande su regole e aperture degli
scacchi; un **router** capisce di cosa parla la domanda, un **agente** cerca **solo nei documenti del ramo giusto** (RAG a rami),
risponde citando le fonti e dice "Non lo so" quando i documenti non bastano.

Il progetto si costruisce **a step**. Questo README cresce con gli step.

## Come funziona (stato attuale: Step 1c)
```
domanda ─► router (LLM, output strutturato) ─► agente con SOLO il tool del ramo scelto ─► risposta con fonti
              │ rami scelti / fuori tema            └─ cerca_<ramo>: ricerca ibrida (significato + parole + RRF)
              ▼
        fuori tema: risposta fissa, nessuna ricerca
```
- **Ingestione** (`chess_tutor/ingest.py`, S07): documenti `.md` → una **sezione = un pezzo** con `[titolo — sezione]` davanti
  (*contextual retrieval*, S08) → embedding → Qdrant in memoria. Una collection per ramo.
- **Ricerca** (`chess_tutor/retrieval.py`, S08): per **significato** (embedding), per **parole** (BM25) e **ibrida** (RRF).
- **Router** (`chess_tutor/router.py`): una chiamata al modello che compila un modulo (Pydantic): la domanda riguarda gli scacchi?
  in quali rami cercare? Il prompt è stato scelto misurando 5 varianti.
- **Tutor** (`chess_tutor/tutor.py`, S03/S11): prompt di sistema + agente datapizza-ai con un tool per ramo. La prima ricerca
  la **impone il codice** (`tool_choice="required_first"`): con "auto" il modello rispondeva a memoria su domande fuori corpus.
  L'agente non ha nessuno strumento con effetti verso l'esterno (minimo privilegio, S15).
- **Rami** (`chess_tutor/config.py`): `rules` (regole e notazione) e `openings` (aperture). Aggiungere un ramo = una riga in
  `config.py` + una cartella in `data/` con i documenti `.md`.

## Installazione (Windows, PowerShell, Python 3.12)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # poi apri .env e inserisci la tua OPENAI_API_KEY
```

## Provarlo
```powershell
python -m pytest -q                                              # test (senza chiave girano quelli offline)
python -m chess_tutor.tutor "Come funziona l'arrocco?"           # il tutor risponde, con fonti e costo
python -m chess_tutor.tutor "Cos'è la difesa siciliana?"         # il router sceglie il ramo aperture
python -m chess_tutor.tutor "Che ricetta usi per la carbonara?"  # fuori tema: nessuna ricerca
python evals/prova_tutor.py                                      # 12 domande vere: routing, citazioni, astensione, latenza, costo
python -m chess_tutor.retrieval "Cosa vuol dire O-O-O?" --confronta   # i tre modi di ricerca uno sotto l'altro
python evals/confronta_ricerca.py                                # tabella: solo significato, solo parole, ibrido
```
I comandi che usano il modello consumano la chiave OpenAI (circa $0,0003 a domanda).

## Cartelle
- `data/<ramo>/` — documenti `.md` scritti per il progetto (un ramo = una cartella)
- `chess_tutor/` — il codice
- `evals/` — domande di prova e script di misura
- `tests/` — i test

## Fonti e licenze
I documenti in `data/` sono scritti per questo progetto. Eventuali documenti esterni (PDF) verranno elencati con fonte e licenza.
