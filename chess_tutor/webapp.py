"""Aiuti dell'interfaccia Streamlit (Step 1h): tutto ciò che non è "disegnare" sta qui, così si prova senza avviare l'app.

L'app vera sono `app.py` (la navigazione) e le pagine in `app_pages/` (script diretti). Qui ci sono: la creazione unica del tutor
(indice + modello, messi in cache), la trasformazione di una `Risposta` nel messaggio da mostrare, e il disegno di esito del quiz.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from . import config, observability
from .tutor import Risposta, Tutor

# Le icone dei messaggi della chat: il pedone è chi fa la domanda, il cavallo è il tutor (stessi disegni delle icone del font di Streamlit).
AVATAR = {"user": ":material/chess_pawn:", "assistant": ":material/chess_knight:"}

# ---------- il caricamento a tema scacchi ----------
FRASI_ATTESA = ("Cerco nei documenti…", "Scelgo il ramo giusto…", "Preparo la mossa…")

# Un cavallo salta lungo una fila di otto caselle (crema e verde, come il tema). Solo CSS: niente JavaScript. Le frasi cambiano da sole.
# Con "riduci animazioni" attivo nel sistema il cavallo sta fermo e resta la prima frase. Le classi iniziano con "sc-" per non toccare altro.
_STILE_ATTESA = """
<style>
.sc-attesa{display:flex;align-items:center;gap:1rem;padding:.35rem 0}
.sc-attesa .sc-fila{position:relative;flex:none;width:256px;height:32px;border-radius:4px;
  background:repeating-linear-gradient(90deg,#F3E4BF 0 32px,#A5582D 32px 64px);box-shadow:0 0 0 1px rgba(69,65,60,.35)}
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
            with st.chat_message("assistant", avatar=AVATAR["assistant"]):
                st.html(html_attesa(frasi))
        else:
            st.html(html_attesa(frasi))
    return segnaposto

# Mentre si prepara l'indice dei documenti (solo la prima volta, qualche secondo): una pedina che gira su se stessa dentro un cerchio di legno.
# Solo CSS, niente JavaScript; con "riduci animazioni" la pedina sta ferma. I colori seguono il tema chiaro/scuro (variabili `--sc-*`).
_STILE_INDICE = """
<style>
.sc-indice{display:flex;align-items:center;gap:1rem;padding:.6rem 0}
.sc-indice .sc-pedina{flex:none;width:54px;height:54px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  background:var(--sc-pannello,#FBF4E4);border:3px solid var(--sc-cornice,#A5582D);box-shadow:0 0 0 1px rgba(69,65,60,.2)}
.sc-indice .sc-pedina span{display:inline-block;font-size:30px;line-height:1;color:var(--sc-nome,#2B2433);animation:sc-gira 1.6s linear infinite}
@keyframes sc-gira{from{transform:rotateY(0deg)} to{transform:rotateY(360deg)}}
@media (prefers-reduced-motion:reduce){.sc-indice .sc-pedina span{animation:none}}
</style>
"""


def html_indice(testo: str = "Preparo l'indice dei documenti…") -> str:
    """Il caricamento dell'indice come HTML: una pedina che gira e la frase (si prova senza avviare l'app)."""
    return (f'{_STILE_INDICE}<div class="sc-indice" role="status" aria-live="polite" aria-label="{escape(testo)}">'
            f'<div class="sc-pedina" aria-hidden="true"><span>♟︎</span></div><div class="sc-testo-indice">{escape(testo)}</div></div>')


def attesa_indice():
    """Mostra la pedina che gira e restituisce il segnaposto: a fine attesa si chiama `.empty()` (meglio dentro un try/finally)."""
    segnaposto = st.empty()
    with segnaposto.container():
        st.html(html_indice())
    return segnaposto


# ---------- l'aspetto: intestazione e sfondo a scacchiera ----------
# Su richiesta di Rita: titolo e sfondo più curati, a tema legno (come la seconda versione delle slide), con la stessa illustrazione
# della prima slide e un pulsante chiaro/scuro. Le classi iniziano con "sc-" per non toccare altro. I colori cambiano con il tema
# tramite variabili CSS: un piccolo script (vedi `_JS_TEMA`) legge se la pagina è chiara o scura e scrive `data-sc-modo` sulla pagina.
# Senza JavaScript resta il tema chiaro. Gli stessi colori stanno in .streamlit/config.toml.
RADICE = Path(__file__).resolve().parent.parent
IMMAGINE_PEZZI = RADICE / "app_assets" / "pezzi_intestazione.png"     # pngegg, uso didattico: NON è su GitHub (vedi .gitignore)

_STILE_PAGINA = """
<style>
:root{--sc-quadri:rgba(165,88,45,.07);--sc-cornice:#A5582D;--sc-pannello:#FBF4E4;--sc-nome:#2B2433;--sc-pezzi:#A5582D;
  --sc-motto:#5E5560;--sc-c1:#E3A66E;--sc-c2:#2B2433;--sc-alone:rgba(165,88,45,.14);--sc-bordo:rgba(165,88,45,.28);
  --sc-av-u:#4A4A6A;--sc-av-a:#A5582D;--sc-av-i:#F3E4BF;--sc-av-iu:#F3E4BF;--sc-pista:rgba(43,36,51,.22)}
:root[data-sc-modo="dark"]{--sc-quadri:rgba(227,166,110,.07);--sc-cornice:#E3A66E;--sc-pannello:#2B2433;--sc-nome:#F3E4BF;
  --sc-pezzi:#E3A66E;--sc-motto:#C9BBA0;--sc-c1:#E3A66E;--sc-c2:#4A4A6A;--sc-alone:rgba(243,228,191,.16);--sc-bordo:rgba(227,166,110,.3);
  --sc-av-u:#4A4A6A;--sc-av-a:#E3A66E;--sc-av-i:#231D2B;--sc-av-iu:#F3E4BF;--sc-pista:rgba(35,29,43,.45)}
.stApp{background-image:conic-gradient(var(--sc-quadri) 25%,transparent 0 50%,var(--sc-quadri) 0 75%,transparent 0);
  background-size:104px 104px;background-attachment:fixed}
.sc-marchio{position:relative;overflow:hidden;border-radius:14px;border:3px solid var(--sc-cornice);background:var(--sc-pannello);margin:0 0 .8rem}
.sc-marchio .sc-pannello{position:relative;display:flex;flex-direction:column;justify-content:center;text-align:center;
  padding:1.3rem 21rem 2rem 2rem;min-height:15.3rem}
.sc-marchio .sc-fila{position:absolute;z-index:5;left:0;right:0;bottom:0;height:7px;
  background:repeating-linear-gradient(90deg,var(--sc-c1) 0 7px,var(--sc-c2) 7px 14px)}
.sc-marchio .sc-testo{position:relative;z-index:3}
.sc-marchio .sc-nome{font-family:Cambria,Georgia,'Times New Roman',serif;font-weight:700;font-size:3.4rem;line-height:1.1;color:var(--sc-nome)}
.sc-marchio .sc-pezzi-fila{margin:.1rem 0;font-size:1.3rem;letter-spacing:.45rem;color:var(--sc-pezzi)}
.sc-marchio .sc-motto{margin:.1rem auto 0;max-width:26rem;font-size:.95rem;color:var(--sc-motto)}
.sc-marchio .sc-alone{position:absolute;z-index:3;right:1.2rem;bottom:0;width:20rem;height:11.9rem;border-radius:50%;background:var(--sc-alone)}
.sc-marchio .sc-img{position:absolute;z-index:4;right:2.1rem;bottom:-.25rem;height:14.9rem;width:auto}
.sc-tema{position:fixed;z-index:1000;right:1.1rem;bottom:1.1rem;width:3.1rem;height:3.1rem;border-radius:50%;cursor:pointer;padding:0;
  border:2px solid var(--sc-pannello);background:var(--sc-cornice);color:var(--sc-pannello);
  display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,.25)}
.sc-tema:hover{filter:brightness(1.12)}
:root.sc-cambio [data-testid="stMainMenuPopover"]{opacity:0!important;pointer-events:none}
.sc-tema img{width:2.3rem;height:2.3rem;display:block}
.sc-tema .sc-sole{display:none}
:root[data-sc-modo="dark"] .sc-tema .sc-luna{display:none}
:root[data-sc-modo="dark"] .sc-tema .sc-sole{display:block}
/* le icone tonde dei messaggi: pedone (chi domanda) e cavallo (il tutor), nei colori del legno */
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageAvatarCustom"]{
  background:var(--sc-av-u)!important;color:var(--sc-av-iu)!important}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageAvatarCustom"] *{color:var(--sc-av-iu)!important}
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageAvatarCustom"]{
  background:var(--sc-av-a)!important;color:var(--sc-av-i)!important}
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid="stChatMessageAvatarCustom"] *{color:var(--sc-av-i)!important}
/* il cursore della scacchiera (mossa da vedere): al posto del pallino, una pedina; più spazio sopra, perché il valore ("Inizio", "1. e4") non tocchi il nome */
[data-testid="stSlider"] [role="group"],[data-testid="stSelectSlider"] [role="group"]{margin-top:1.6rem}
[data-testid="stSlider"] div[style*="position: absolute"][style*="touch-action"],
[data-testid="stSelectSlider"] div[style*="position: absolute"][style*="touch-action"]{background:transparent!important;border:none!important;
  box-shadow:none!important;outline:none!important;width:30px!important;height:30px!important;display:flex;align-items:center;justify-content:center}
[data-testid="stSlider"] div[style*="position: absolute"][style*="touch-action"]::after,
[data-testid="stSelectSlider"] div[style*="position: absolute"][style*="touch-action"]::after{content:"♟︎";font-size:30px;line-height:1;
  color:var(--sc-cornice)}
/* la linea di tutti i cursori è sottile (4 px) e a scacchi: sopra la linea già colorata dal tema, quadretti alterni da 4 px */
[data-testid="stSlider"] div[style*="touch-action"][style*="relative"] > div:first-child{position:relative}
[data-testid="stSlider"] div[style*="touch-action"][style*="relative"] > div:first-child::after{content:"";position:absolute;inset:0;
  background:repeating-linear-gradient(90deg,transparent 0 4px,var(--sc-pista) 4px 8px)}
@media (max-width:900px){.sc-marchio .sc-pannello{padding-right:12rem;min-height:11rem}.sc-marchio .sc-img{height:10rem}
  .sc-marchio .sc-alone{width:13rem;height:8rem}.sc-marchio .sc-nome{font-size:2.6rem}}
@media (max-width:600px){.sc-marchio .sc-img,.sc-marchio .sc-alone{display:none}.sc-marchio .sc-pannello{padding-right:1.5rem;min-height:9rem}
  .sc-marchio .sc-nome{font-size:2.3rem}}
</style>
"""

# Lo script fa solo due cose: (1) ogni mezzo secondo guarda se la pagina è scura e lo scrive su `data-sc-modo` (così i colori seguono
# anche il menu delle impostazioni); (2) al clic sul pulsante scrive "Light" o "Dark" dove Streamlit conserva la scelta del tema nel
# browser, per ogni pagina dell'app, e ricarica. Non contatta nessun server. Se in futuro Streamlit cambia questo meccanismo il
# pulsante smette di funzionare, ma il tema si cambia sempre dal menu ⋮ → Impostazioni.
_JS_TEMA = """
<script>
(function(){
  if(window.__scTema) return; window.__scTema = 1;
  function modo(){
    var a = document.querySelector('.stApp'); if(!a) return 'light';
    var m = getComputedStyle(a).backgroundColor.match(/\\d+(\\.\\d+)?/g); if(!m) return 'light';
    return (0.2126*m[0] + 0.7152*m[1] + 0.0722*m[2]) / 255 < 0.5 ? 'dark' : 'light';
  }
  function aggiorna(){
    var d = modo(), r = document.documentElement;
    if(r.dataset.scModo !== d) r.dataset.scModo = d;
  }
  setInterval(aggiorna, 500); aggiorna();
  document.addEventListener('click', function(e){
    var b = e.target.closest && e.target.closest('.sc-tema'); if(!b) return;
    var nuovo = document.documentElement.dataset.scModo === 'dark' ? 'Light' : 'Dark';
    // Via normale: preme per noi la voce del tema nel menu ⋮ di Streamlit (il cambio è immediato e NON ricarica la pagina,
    // quindi la lezione, il cursore e la chat restano dove sono). Il menu resta invisibile mentre lo usiamo.
    var apri = document.querySelector('[data-testid="stMainMenu"] button') || document.querySelector('[data-testid="stMainMenu"]');
    if(apri){
      document.documentElement.classList.add('sc-cambio');
      apri.click();
      var tentativi = 0, attesa = setInterval(function(){
        var voce = document.querySelector('[data-testid="stMainMenuItem-theme-' + nuovo + '"]');
        if(voce){
          clearInterval(attesa); voce.click();
          setTimeout(function(){      // chiude il menu con Esc (inviato all'elemento attivo, dentro al menu) e lo rende di nuovo visibile
            var esc = function(){ (document.activeElement || voce).dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', code:'Escape', keyCode:27, bubbles:true})); };
            esc();
            setTimeout(function(){ if(document.querySelector('[data-testid="stMainMenuPopover"]')) esc(); document.documentElement.classList.remove('sc-cambio'); }, 300);
          }, 150);
        } else if(++tentativi > 20){ clearInterval(attesa); document.documentElement.classList.remove('sc-cambio'); ricarica(nuovo); }
      }, 50);
      return;
    }
    ricarica(nuovo);
  });
  // Piano B (se il menu non c'è): scrive la scelta dove Streamlit la conserva e ricarica la pagina (qui la sessione riparte da capo).
  function ricarica(nuovo){
    var percorsi = {}; percorsi[location.pathname] = 1;
    document.querySelectorAll('a[href]').forEach(function(a){
      try{ var u = new URL(a.href); if(u.origin === location.origin) percorsi[u.pathname] = 1; }catch(err){}
    });
    try{ Object.keys(percorsi).forEach(function(p){ localStorage.setItem('stActiveTheme-' + p + '-v2', JSON.stringify(nuovo)); }); }catch(err){}
    location.reload();
  }
})();
</script>
"""


# Il pulsante del tema: una pedina la cui testa è la luna (tema chiaro: tocca per passare allo scuro) o il sole (tema scuro: tocca per
# tornare al chiaro). Due disegni SVG, il CSS mostra quello giusto in base a `data-sc-modo`: nessun codice, solo forme.
_CORPO_PEDINA = ('<path d="M11.2 15.4h9.6a1.1 1.1 0 0 1 0 2.2h-9.6a1.1 1.1 0 0 1 0-2.2z"/>'
                 '<path d="M12.9 17.6h6.2c.3 2.9 1.5 5.1 3.6 7.1H9.3c2.1-2 3.3-4.2 3.6-7.1z"/>'
                 '<rect x="7.8" y="24.6" width="16.4" height="3.4" rx="1.3"/>')
_TESTA_LUNA = ('<mask id="m"><rect width="32" height="32" fill="#fff"/><circle cx="19.4" cy="6.6" r="4.3" fill="#000"/></mask>'
               '<circle cx="16" cy="8.6" r="5.4" mask="url(#m)"/>')
_TESTA_SOLE = ('<circle cx="16" cy="8.4" r="3.1"/><path fill="none" stroke="#COL" stroke-width="1.3" stroke-linecap="round" '
               'd="M20.7 8.4h1.6M19.3 5.1l1.1-1.1M16 3.7V2.1M12.7 5.1L11.6 4M11.3 8.4H9.7M12.7 11.7l-1.1 1.1M16 13.1v1.6M19.3 11.7l1.1 1.1"/>')


def _pedina_come_immagine(testa: str, colore: str, classe: str) -> str:
    """Una pedina in SVG come immagine incorporata (data URI): Streamlit toglie gli SVG scritti dentro la pagina, ma lascia le immagini."""
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="#{colore}">{testa.replace("#COL", "#" + colore)}{_CORPO_PEDINA}</svg>'
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img class="{classe}" src="{uri}" alt="" aria-hidden="true">'


# Tema chiaro: sfondo del pulsante marrone, pedina crema con la luna. Tema scuro: sfondo ocra, pedina scura con il sole.
_PEDINE_TEMA = _pedina_come_immagine(_TESTA_LUNA, "FBF4E4", "sc-luna") + _pedina_come_immagine(_TESTA_SOLE, "2B2433", "sc-sole")


@lru_cache(maxsize=1)
def immagine_pezzi_uri() -> str:
    """L'illustrazione dell'intestazione come "data URI" (incorporata nell'HTML), oppure stringa vuota se il file non c'è."""
    try:
        return "data:image/png;base64," + base64.b64encode(IMMAGINE_PEZZI.read_bytes()).decode("ascii")
    except OSError:
        return ""


def html_intestazione(immagine: str | None = None) -> str:
    """L'intestazione del sito (marchio, pezzi, motto, riga a scacchi in basso, pulsante del tema) come HTML, senza script: si prova senza
    avviare l'app. `immagine` = data URI dell'illustrazione (di norma quella in app_assets/); vuota o assente = intestazione senza."""
    uri = immagine_pezzi_uri() if immagine is None else immagine
    img = ('<div class="sc-alone" aria-hidden="true"></div>'
           f'<img class="sc-img" src="{uri}" alt="" aria-hidden="true">') if uri else ""
    return (f'{_STILE_PAGINA}<div class="sc-marchio"><div class="sc-pannello">'
            '<div class="sc-testo"><div class="sc-nome">Chess Tutor</div>'
            '<div class="sc-pezzi-fila" aria-hidden="true">♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜</div>'
            '<p class="sc-motto">Il tutor di scacchi per principianti: risponde dai suoi documenti e cita sempre la fonte.</p></div>'
            f'{img}</div><div class="sc-fila" aria-hidden="true"></div></div>'
            f'<button class="sc-tema" type="button" aria-label="Cambia tema chiaro o scuro" title="Cambia tema chiaro o scuro">{_PEDINE_TEMA}</button>')


def mostra_intestazione() -> None:
    """Sfondo e intestazione, uguali in tutte le pagine: si chiama una volta sola, da app.py."""
    st.html(html_intestazione() + _JS_TEMA, unsafe_allow_javascript=True)


MSG_SENZA_CHIAVE = ("Manca la chiave OpenAI. Copia `.env.example` in `.env`, scrivi la tua `OPENAI_API_KEY` e riavvia l'app "
                    "(`streamlit run app.py`). Senza chiave il tutor non può cercare né rispondere.")


@st.cache_resource(show_spinner=False)        # il caricamento lo mostra `tutor_o_ferma` (la pedina che gira)
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
    if st.session_state.get("tutor_pronto"):          # già preparato in questa sessione: niente caricamento ad ogni ricarica
        return get_tutor()
    attesa = attesa_indice()
    try:
        tutor = get_tutor()
    finally:
        attesa.empty()
    st.session_state["tutor_pronto"] = True
    return tutor


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
            "costo": f"{r.latenza_s:.1f} s · {r.token_prompt + r.token_completati} token · €{r.costo_eur:.5f}",
            "senza_fonti": tipo == "normale" and not r.fonti}


def messaggio_utente(testo: str) -> dict:
    return {"ruolo": "user", "testo": testo, "tipo": "normale", "dettagli": [], "costo": "", "senza_fonti": False}


def mostra_messaggio(m: dict) -> None:
    """Disegna un messaggio della chat (il tipo decide il riquadro: la domanda bloccata e quella fuori tema si vedono subito)."""
    with st.chat_message(m["ruolo"], avatar=AVATAR.get(m["ruolo"])):
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
