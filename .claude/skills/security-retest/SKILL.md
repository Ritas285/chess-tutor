---
name: security-retest
description: Procedura di red team e retest: fissa un attacco, lancialo, aggiungi barriere su passaggi diversi, rilancia lo STESSO attacco. Usala quando tocchi strumenti, prompt o guardrail.
---
1. **Fissa l'attacco**: vettore (per esempio un documento avvelenato nel corpus o una risposta d'allievo con un ordine), bersaglio e canale
   d'uscita (un link, un segreto, una fonte inventata). Scrivilo nei test: `tests/test_sicurezza.py` (documento avvelenato, modello
   "ingenuo" `ModelloIngenuo` in `tests/fakes.py` che cade sempre), `tests/test_guardrails.py`, `tests/test_quiz.py`.
2. **PRIMA**: mostra che l'attacco riesce con le barriere spente. `guardrails.Controlli` ha un interruttore per ogni barriera
   (`input`, `documenti`, `output`, `citazioni`).
3. **Barriere su passaggi diversi**: domanda (`controlla_domanda`), documenti recuperati (`sanifica_documento`, per frase), risposta
   (`ripulisci_output`), citazioni (`ancora_citazioni`), minimo privilegio (l'agente ha solo `cerca_<ramo>`; l'elenco dei tool MCP è chiuso
   in `tests/test_mcp_server.py`), registro (`logs/audit.jsonl`).
4. **DOPO**: stesso attacco, la catena si ferma. Con il modello vero: `python evals/retest_sicurezza.py` (chiave, 2-3 minuti).
   Riporta onestamente anche quando il modello vero **non cade comunque**: le barriere lavorano sul danno, non sulla fortuna.
5. Controlla che il compito **legittimo** funzioni ancora (risposta utile: una barriera che spegne le risposte buone non serve; è già
   successo con la barriera sui documenti che toglieva l'intera riga: ora toglie la frase) e che le domande vere non vengano bloccate
   (falsi allarmi). Congela la configurazione: se cambi un prompt, ripeti il retest.
