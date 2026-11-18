"""Aiuti dell'interfaccia Streamlit (Step 1h): tutto ciò che non è "disegnare" sta qui, così si prova senza avviare l'app.

L'app vera sono `app.py` (la navigazione) e le pagine in `app_pages/` (script diretti). Qui ci sono: la creazione unica del tutor
(indice + modello, messi in cache), la trasformazione di una `Risposta` nel messaggio da mostrare, e il disegno di esito del quiz.
"""
from __future__ import annotations

from html import escape

import streamlit as st

from . import config, observability
from .tutor import Risposta, Tutor

# ---------- il caricamento a tema scacchi ----------
FRASI_ATTESA = ("Cerco nei documenti…", "Scelgo il ramo giusto…", "Preparo la mossa…")

# Un cavallo salta lungo una fila di otto caselle (crema e verde, come il tema). Solo CSS: niente JavaScript. Le frasi cambiano da sole.
# Con "riduci animazioni" attivo nel sistema il cavallo sta fermo e resta la prima frase. Le classi iniziano con "sc-" per non toccare altro.
_STILE_ATTESA = """
<style>
.sc-attesa{display:flex;align-items:center;gap:1rem;padding:.35rem 0}
.sc-attesa .sc-fila{position:relative;flex:none;width:256px;height:32px;border-radius:4px;
  background:repeating-linear-gradient(90deg,#EEEED2 0 32px,#4F7A39 32px 64px);box-shadow:0 0 0 1px rgba(69,65,60,.35)}
.sc-attesa .sc-cavallo{position:absolute;left:0;top:0;width:32px;height:32px;line-height:32px;text-align:center;font-size:26px;
  color:#262421;text-shadow:0 0 2px #EEEED2,0 0 3px #EEEED2;animation:sc-salti 3.6s ease-in-out infinite alternate}
@keyframes sc-salti{
  0%{transform:translate(0,0)} 8.3%{transform:translate(32px,-20px)} 16.7%{transform:translate(64px,0)}
  25%{transform:translate(96px,-20px)} 33.3%{transform:translate(128px,0)} 41.7%{transform:translate(160px,-20px)}
  50%{transform:translate(192px,0)} 58.3%{transform:translate(208px,-20px)} 66.7%,100%{transform:translate(224px,0)}}
.sc-attesa .sc-testo{position:relative;flex:1;min-width:12em;height:1.6em}
.sc-attesa .sc-testo span{position:absolute;left:0;top:0;opacity:0;animation:sc-frase 9s infinite}
.sc-attesa .sc-testo span:nth-child(2){animation-delay:3s}
.sc-attesa .sc-testo span:nth-child(3){animation-delay:6s}
@keyframes sc-frase{0%{opacity:0} 6%,30%{opacity:1} 36%,100%{opacity:0}}
@media (prefers-reduced-motion:reduce){
  .sc-attesa .sc-cavallo{animation:none}
  .sc-attesa .sc-testo span{animation:none;opacity:0}
  .sc-attesa .sc-testo span:first-child{opacity:1}}
</style>
"""


def html_attesa(frasi: tuple[str, ...] = FRASI_ATTESA) -> str:
    """Il caricamento a tema scacchi come HTML (si prova senza avviare l'app). Le frasi si ripetono a rotazione, 3 secondi ciascuna."""
    spans = "".join(f"<span>{escape(f)}</span>" for f in frasi)
    return (f'{_STILE_ATTESA}<div class="sc-attesa" role="status" aria-live="polite" aria-label="Il tutor sta preparando la risposta">'
            f'<div class="sc-fila" aria-hidden="true"><div class="sc-cavallo">♞︎</div></div>'
            f'<div class="sc-testo">{spans}</div></div>')


def attesa_scacchi(frasi: tuple[str, ...] = FRASI_ATTESA, bolla: bool = True):
    """Mostra il caricamento e restituisce il segnaposto: a fine attesa si chiama `.empty()` (meglio dentro un try/finally).
    `bolla=True` lo mette dentro un messaggio del tutor (chat); `bolla=False` lo mostra da solo (pagina del quiz)."""
    segnaposto = st.empty()
    with segnaposto.container():
        if bolla:
            with st.chat_message("assistant"):
                st.html(html_attesa(frasi))
        else:
            st.html(html_attesa(frasi))
    return segnaposto

MSG_SENZA_CHIAVE = ("Manca la chiave OpenAI. Copia `.env.example` in `.env`, scrivi la tua `OPENAI_API_KEY` e riavvia l'app "
                    "(`streamlit run app.py`). Senza chiave il tutor non può cercare né rispondere.")


@st.cache_resource(show_spinner="Preparo l'indice dei documenti…")
def get_tutor() -> Tutor:
    """Il tutor, creato UNA volta per processo (indicizzare costa qualche secondo e frazioni di centesimo di embedding).
    Il Tutor non ha stato per utente (la memoria della chat sta in `st.session_state`), quindi si può condividere.
    Osservabilità opzionale: PHOENIX_ENDPOINT e ENABLE_METRICS nel file .env (Step 1g)."""
    try:
        metriche = observability.attiva_da_ambiente()
    except OSError:          # la porta delle metriche è già occupata (es. ricarica dell'app): si va avanti senza
        metriche = None
    return Tutor.crea(metriche=metriche)


def tutor_o_ferma() -> Tutor:
    """Il tutor, oppure un messaggio chiaro e stop della pagina se manca la chiave: l'app non deve rompersi, deve dire cosa fare."""
    if not config.OPENAI_API_KEY:
        st.error(MSG_SENZA_CHIAVE, icon=":material/key_off:")
        st.stop()
    return get_tutor()


# ---------- la risposta del tutor come messaggio ----------
def messaggio_da_risposta(r: Risposta) -> dict:
    """Una `Risposta` come dato da mostrare e conservare nella chat: testo, tipo, dettagli ("come ha lavorato") e riga di costo."""
    if r.bloccata:
        tipo = "bloccata"
    elif r.fuori_tema:
        tipo = "fuori_tema"
    else:
        tipo = "normale"
    dettagli: list[str] = []
    if tipo == "bloccata":
        dettagli.append(f"**Guardrail di input:** domanda fermata prima del modello ({r.bloccata}). Costo zero.")
    else:
        rami = ", ".join(r.rami) or "nessuno (fuori tema: non ho cercato nei documenti)"
        dettagli.append(f"**Rami scelti dal router:** {rami}" + (" (ripiego: ha cercato in tutti)" if r.ripiego_router else ""))
        dettagli.append(f"**Strumenti usati:** {', '.join(r.tool_usati) or '—'}")
        if r.fonti:
            dettagli.append("**Fonti trovate:**\n" + "\n".join(f"- `{f}`" for f in r.fonti))
    dettagli.append(f"**Guardrail:** {'; '.join(r.note) if r.note else 'nessun intervento'}")
    return {"ruolo": "assistant", "testo": r.testo, "tipo": tipo, "dettagli": dettagli,
            "costo": f"{r.latenza_s:.1f} s · {r.token_prompt + r.token_completati} token · ${r.costo_usd:.5f}",
            "senza_fonti": tipo == "normale" and not r.fonti}


def messaggio_utente(testo: str) -> dict:
    return {"ruolo": "user", "testo": testo, "tipo": "normale", "dettagli": [], "costo": "", "senza_fonti": False}


def mostra_messaggio(m: dict) -> None:
    """Disegna un messaggio della chat (il tipo decide il riquadro: la domanda bloccata e quella fuori tema si vedono subito)."""
    with st.chat_message(m["ruolo"]):
        if m["tipo"] == "bloccata":
            st.warning(m["testo"], icon=":material/shield:")
        elif m["tipo"] == "fuori_tema":
            st.info(m["testo"], icon=":material/info:")
        else:
            st.markdown(m["testo"])
        if m.get("senza_fonti"):
            st.caption(":material/warning: Questa risposta non cita nessun documento: non fidarti.")
        if m["dettagli"]:
            with st.expander("Come ha lavorato"):
                for riga in m["dettagli"]:
                    st.markdown(riga)
        if m["costo"]:
            st.caption(m["costo"])


# ---------- il quiz ----------
def mostra_esito(esito: str, feedback: str) -> None:
    """corretta = verde, parziale = giallo, errata = rosso, non verificabile = blu."""
    testo = f"**{esito.replace('_', ' ')}** — {feedback}"
    if esito == "corretta":
        st.success(testo, icon=":material/check_circle:")
    elif esito == "parziale":
        st.warning(testo, icon=":material/rule:")
    elif esito == "errata":
        st.error(testo, icon=":material/cancel:")
    else:
        st.info(testo, icon=":material/help:")


def riepilogo_quiz(esiti: dict) -> str:
    """"2 corrette, 1 parziale, 0 errate" sulle domande verificate."""
    conteggi = {k: sum(1 for g, _ in esiti.values() if g.esito == k) for k in ("corretta", "parziale", "errata", "non_verificabile")}
    nomi = {"corretta": ("corretta", "corrette"), "parziale": ("parziale", "parziali"), "errata": ("errata", "errate"),
            "non_verificabile": ("non verificabile", "non verificabili")}
    return ", ".join(f"{n} {nomi[k][0 if n == 1 else 1]}" for k, n in conteggi.items() if n)
