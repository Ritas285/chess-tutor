---
name: run-evals
description: Lancia le valutazioni (routing, retrieval, risposte, verifica, quiz) e le interpreta con la regola A/B del corso. Usala dopo ogni modifica a prompt, router, chunking, retrieval o giudici.
---
1. `python evals/run_evals.py` (routing e retrieval) e `python evals/run_evals.py --e2e` (risposte vere con giudice). Servono la chiave
   in `.env` e costano pochi centesimi. I risultati finiscono in `evals/results/` e vengono confrontati con l'ultimo run dello stesso tipo.
   Per capire un errore: `--solo G12,G24`. Per dare un nome al run: `--etichetta nome-breve`.
2. Per la verifica delle risposte: `python evals/valuta_verifica.py`; per il generatore di quiz: `python evals/valuta_quiz.py`.
3. **Regola A/B** (stesso gold prima e dopo, **una modifica per volta**): la modifica vale solo se la faithfulness sale di almeno 0.03, la
   recall non scende di più di 0.02 e il costo resta nel budget (≤ $0,005 a domanda). Il budget di latenza è p50 ≤ 4 s: **oggi non è
   rispettato** (circa 5,5-5,9 s), non fingere il contrario.
4. Su 33 domande una differenza **sotto 0.05 è rumore**: non cantare vittoria. Il giudice è unico e cambia voto da un run all'altro.
5. Guarda gli **ID sbagliati** e le motivazioni, non solo le medie. Una misura che "migliora" senza migliorare le risposte è un campanello
   (è già successo: routing a 1.0 con più costo e nessuna risposta migliore).
6. Non aggiungere parole chiave o esempi che copiano le domande del gold (Goodhart; un test lo vieta). Una prova scartata si salva in
   `evals/results/scartati/`, non si cancella.
