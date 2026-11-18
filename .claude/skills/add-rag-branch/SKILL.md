---
name: add-rag-branch
description: Aggiunge un nuovo ramo di conoscenza al tutor (cartella dati, config, gold, test, misure). Usala quando l'utente vuole coprire un nuovo argomento di scacchi.
---
Un ramo = una cartella in `data/` + una voce in `config.BRANCHES`. Niente altro codice: router e agente lo vedono da soli.

1. **Documenti.** Crea `data/<ramo>/` con 2-4 file `.md` numerati (`01_...md`): un `# Titolo`, poi sezioni `## ...` brevi di 80-200 parole,
   una sezione = un'idea (il chunker fa un pezzo per sezione e antepone titolo e sezione). Per il contenuto usa la skill `write-chess-content`.
2. **Configurazione.** Aggiungi `Branch("<ramo>", "Etichetta", "descrizione")` in `chess_tutor/config.py`. La descrizione la legge il
   router LLM: elenca gli argomenti veri del ramo, in positivo, con le parole che userebbe un principiante.
3. **Gold.** In `evals/gold.json` aggiungi 3-4 domande `in_corpus` con `rami` e `attesi` (gruppi di file: basta uno per gruppo; una
   domanda a due rami ha due gruppi). **Non ritoccare le domande esistenti** e non copiarle nei prompt.
4. **Test.** Controlla `tests/test_rami.py` e `tests/test_router.py` (il router ha già un test che il prompt contiene le descrizioni dei rami);
   `tests/test_valutazione.py` verifica che i file attesi dal gold esistano nei rami indicati.
5. **Verifica.** `python -m pytest -q`, `python evals/verifica_contenuti.py`, poi `python evals/run_evals.py` e `--e2e`: riporta
   routing, recall@3 e MRR **prima e dopo** (vedi `run-evals`). Se il routing delle domande vecchie peggiora, il ramo nuovo "ruba" domande:
   correggi le descrizioni, non il gold.

Non toccare i guardrail. Un ramo nuovo non deve avere strumenti con effetti verso l'esterno.
