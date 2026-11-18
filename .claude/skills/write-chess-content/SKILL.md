---
name: write-chess-content
description: Scrive o corregge documenti didattici di scacchi per il corpus, verificando le mosse con python-chess. Usala per ogni nuovo contenuto in data/.
---
- Italiano semplice, per principianti. Notazione italiana nel testo (C cavallo, A alfiere, T torre, D donna, R re) e mosse in forma
  `1.e4 e5 2.Cf3 Cc6`. Le lettere dei pezzi sono **maiuscole**.
- Struttura: `# Titolo`, poi sezioni `## ...` autonome di 80-200 parole (il chunker spezza per sezione e antepone titolo e sezione).
- **Ogni sequenza di mosse va verificata**, e prima di dire "fatto" si lancia: `python evals/verifica_contenuti.py` (nessuna chiave).
  Cerca ogni sequenza che inizia con `1.`, la gioca dalla posizione iniziale con python-chess e fallisce (codice 1) alla prima mossa
  non legale, dicendo file, riga e perché. Per una singola mossa su una posizione: `chess_tools.verifica_mossa(fen, mossa)` o il tool
  MCP `verifica_mossa`. Non scrivere varianti che non hai verificato, e non inventare posizioni.
- Una sequenza deve **iniziare dalla posizione iniziale** con `1.`; un frammento (`3...Ac5`) non viene controllato: scrivilo con la
  sequenza completa se vuoi che lo sia.
- Niente numeri statistici non verificabili, niente affermazioni assolute ("sempre", "il migliore") senza motivo.
- Contenuto proprio o con licenza libera (es. CC BY-SA: cita la fonte nel README). Mai incollare testi protetti.
- Dopo aver scritto un documento nuovo: `python -m pytest -q` e, se il ramo ha un gold, `python evals/run_evals.py`.
