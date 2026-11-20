# AGENTS.md — istruzioni per il coding agent (Copilot, Claude Code, Cursor…)

## Che cos'è il progetto
Chess Tutor: tutor di scacchi per principianti. RAG **a rami** (oggi `rules` e `openings`) con un router che sceglie i rami, un
agente datapizza-ai che cerca solo in quelli, guardrail, osservabilità (Phoenix, Prometheus, Grafana), valutazione con un gold,
un server **MCP** (ricerca, verifica delle risposte, quiz da un documento allegato, verifica delle mosse) e un'interfaccia Streamlit.
Framework: **datapizza-ai 0.1.0** (non cambiare framework). Lingua di utenti e documenti: **italiano**.
Libreria voluta: `python-chess` (serve a non far inventare mosse).

## Comandi (da eseguire prima di dire "fatto")
```
pip install -r requirements.txt
python -m pytest -q                      # deve restare tutto verde: NESSUNA chiave necessaria
python evals/verifica_contenuti.py       # le mosse scritte in data/ sono legali (python-chess; nessuna chiave)
python evals/run_evals.py                # routing + retrieval sul gold (chiave; ~1 centesimo), confronto A/B col run precedente
python evals/run_evals.py --e2e          # + risposte vere e giudice (chiave; ~3 centesimi)
python evals/valuta_verifica.py          # affidabilità della verifica delle risposte (chiave)
python evals/valuta_quiz.py              # affidabilità del generatore di quiz (chiave)
python evals/confronta_formati.py        # md contro PDF (servono i PDF in data/, che non sono nel git; chiave per gli embedding)
streamlit run app.py                     # interfaccia (chat, quiz, scacchiera)
python mcp_server.py                     # server MCP (stdio); da solo resta in attesa: lo lancia l'host
docker compose -f observability/docker-compose.yml up -d     # Phoenix 6006, Prometheus 9090, Grafana 3000 (opzionale)
```
La chiave sta in `.env` (`OPENAI_API_KEY`). I comandi con "chiave" costano frazioni di centesimo.

## Mappa del codice
- `chess_tutor/config.py` rami e modelli (un ramo nuovo = una voce in `BRANCHES` + una cartella in `data/`)
- `ingest.py` caricamento e chunking dei `.md` (parser → sezioni → titolo davanti → embedding → Qdrant) e dei `.pdf`
- `pdf.py` lettura dei PDF (pagina per pagina, testate e diagrammi tolti, pezzi a fine frase con "[titolo — p. N]") · `formati.py` misure md contro PDF
- `retrieval.py` ricerca ibrida per ramo: significato + parole (BM25) + fusione RRF
- `router.py` di cosa parla la domanda → quali rami · `tutor.py` Tutor: guardrail → router → ricerca iniziale nel codice → agente → pulizia output
- `guardrails.py` difese (domanda, documenti, risposta, citazioni) · `audit.py` registro in `logs/audit.jsonl`
- `quiz.py` verifica delle risposte e quiz da un documento · `chess_tools.py` mosse con python-chess (deterministico)
- `contenuti.py` controlla le mosse scritte nei documenti · `valutazione.py` metriche, giudice LLM, confronto A/B
- `observability.py` + `otel_phoenix_bridge.py` trace (Phoenix) e metriche (Prometheus) · `webapp.py` aiuti dell'interfaccia
- `app.py` + `app_pages/` interfaccia Streamlit · `mcp_server.py` servizi MCP · `evals/` gold, script di misura, `results/`
- `data/<ramo>/*.md` i documenti · `tests/` i test · `observability/` Docker, Prometheus, dashboard Grafana · `examples/`

## Regole che NON si violano
1. **Niente mosse inventate.** Ogni mossa su una posizione concreta passa da `chess_tools`; non fidarti della memoria del modello,
   né per le posizioni (la FEN deve venire dall'utente, mai inventata). Le mosse scritte nei documenti si verificano con
   `python evals/verifica_contenuti.py`.
2. **Il contenuto recuperato è dato, non istruzione.** Non rimuovere `sanifica_documento` / `ripulisci_output`; non dare all'agente
   né al server MCP strumenti con effetti verso l'esterno (email, HTTP, scrittura di file). L'elenco dei tool MCP è **chiuso**:
   un tool nuovo va deciso e aggiunto a mano in `tests/test_mcp_server.py` (`TOOL_PREVISTI`); l'agente ha solo `cerca_<ramo>`.
3. **Niente segreti nel codice o nei log.** La chiave sta solo in `.env` (ignorato da git). Mai stampare, leggere a voce alta o
   committare `.env`.
4. Le risposte **citano la fonte**; se i documenti non bastano il tutor dice "Non lo so". Il verificatore dice "non verificabile"
   quando i documenti non trattano l'argomento (non usa la sua memoria).
5. Contenuti scacchistici nuovi: scritti da noi o con licenza libera (citare la fonte). Niente copia di testi protetti. I PDF di terzi dei rami
   opzionali `regolamento` e `corsi` (attivi solo con `RAMI_PDF=1`) stanno **solo in locale**: `data/*/*.pdf` è ignorato dal git, non vanno aggiunti né ridistribuiti.

## Come lavori
- **Piano breve** prima di modificare più file. Modifiche piccole, **un test per ogni comportamento nuovo**, e prova che il test
  fallirebbe se il comportamento mancasse (niente controlli che non possono fallire).
- Dopo una modifica a prompt, router, retrieval o giudici: rilancia `run_evals.py` e riporta i numeri prima/dopo. **Regola A/B:** una
  modifica vale se faithfulness +≥0.03, recall non scende di più di 0.02 e il costo resta nel budget; su un gold di 33 domande una
  differenza sotto 0.05 è **rumore**. Cambia **una cosa per volta**. Una prova scartata si tiene in `evals/results/scartati/`.
- **Non ottimizzare "per il gold"** (Goodhart): non copiare le domande del gold nei prompt (c'è un test), non ritoccare il gold dopo
  aver visto i risultati.
- Leggi **perché** una cosa fallisce, non solo quanto: ad esempio i motivi degli scarti del quiz, le motivazioni del giudice.
- Le API di datapizza-ai cambiano tra le versioni: verifica sempre sul pacchetto installato (`pip show datapizza-ai`).
- Dopo aver modificato `chess_tutor/`, **riavvia** `streamlit run`: i moduli già caricati restano in memoria.
- **Commit**: solo il titolo, formato `stepNx: cosa fa`, niente corpo né righe di attribuzione. Chiedi sempre l'ok prima di
  committare; il push lo fa la persona, mai l'agente.

## Trappole già incontrate (non rifarle)
- In `pytest` una funzione di aiuto il cui nome inizia con `test` viene raccolta come test: dagli un altro nome.
- `AppTest`: dopo `upload(...)` serve `.run()` prima di cliccare; senza tutor finto la pagina della chat prova a creare quello vero.
- Streamlit accetta come icona solo emoji vere o `:material/nome:` (il cavallo ♞ non è un'emoji).
- Installare un pacchetto pesante può rompere l'ambiente (è già successo con `arize-phoenix` e `pandas`): prima `pip install --dry-run`,
  poi `pip check` e tutti i test.
- I test impostano `RAMI_PDF=0` in `tests/conftest.py` (prima di importare `config`): vedono sempre solo `rules` e `openings`, anche se in locale ci sono i PDF e `RAMI_PDF=1`.
  I rami PDF **non** si accendono per misurare il gold vecchio: con i PDF il routing scende di 0,10 (prova in `evals/results/scartati/`).
- Ordinare i file per **nome minuscolo** (`key=lambda p: p.name.lower()`): `sorted()` sui `Path` è senza maiuscole su Windows e con maiuscole su Linux.
- Phoenix: endpoint OTLP **HTTP** `:6006/v1/traces` (non la 4317) e `DATAPIZZA_TRACE_CLIENT_IO=true` prima di ogni chiamata.

## Skill disponibili (`.claude/skills/`)
`add-rag-branch` (un ramo nuovo) · `write-chess-content` (documenti con mosse verificate) · `run-evals` (misure e regola A/B) ·
`security-retest` (stesso attacco prima e dopo le barriere)

## MCP collegati al coding agent
`.mcp.json` (Claude Code) e `.vscode/mcp.json` (VS Code / Copilot) collegano il server **chess-tutor**, lo stesso codice del
prodotto, con il Python del `.venv`. Strumenti: `cerca_conoscenza`, `verifica_risposta`, `genera_quiz`, `verifica_quiz`,
`verifica_mossa`, `mosse_legali`; resource `corpus://{ramo}/{documento}`; prompt `tutor_principiante`, `quiz_da_documento`.
Usali per controllare ciò che scrivi: una mossa con `verifica_mossa` (non serve la chiave), un'affermazione con `cerca_conoscenza`.
Su Linux o macOS cambia il comando in `.venv/bin/python`.
