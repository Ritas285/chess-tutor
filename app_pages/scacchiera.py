import chess
import streamlit as st

from chess_tutor import chess_tools as ct
from chess_tutor import lezioni

st.title("♞ Scacchiera")

LEZIONI, PROVA = "Lezioni", "Prova una mossa"
modo = st.segmented_control("Cosa vuoi fare?", [LEZIONI, PROVA], default=LEZIONI, key="modo", label_visibility="collapsed") or LEZIONI

if modo == LEZIONI:
    st.caption("Come funzionano l'arrocco, le aperture e i matti rapidi, **una mossa alla volta**. Le mosse di ogni lezione sono controllate "
               "da `python-chess`; le spiegazioni vengono dai documenti del tutor.")
    gruppo = st.segmented_control("Argomento", lezioni.GRUPPI, default=lezioni.GRUPPI[0], key="gruppo") or lezioni.GRUPPI[0]
    elenco = lezioni.del_gruppo(gruppo)
    titoli = {lez.chiave: lez.titolo for lez in elenco}
    chiave = st.pills("Lezione", list(titoli), format_func=titoli.get, default=elenco[0].chiave, selection_mode="single",
                      key=f"lezione_{gruppo}", label_visibility="collapsed") or elenco[0].chiave
    lez = lezioni.cerca(chiave)

    st.subheader(lez.titolo)
    st.write(lez.spiegazione)

    sequenza = ct.gioca_sequenza(lez.fen, lezioni.mosse_della_lezione(lez))
    esiti = sequenza.legali                                   # una lezione con una mossa non legale la scopre il test, non l'utente
    if sequenza.errore:
        st.error(f"La mossa {sequenza.errore[0]} di questa lezione non è legale: {sequenza.errore[2].messaggio}", icon=":material/error:")
        st.stop()

    def etichetta(i: int) -> str:
        """0 = posizione di partenza; poi "1. e4", "1... e5", "2. Cf3"..."""
        return "Inizio" if i == 0 else f"{(i + 1) // 2}{'.' if i % 2 else '...'} {esiti[i - 1].mossa}"

    passo = st.select_slider("Mossa da vedere", options=list(range(len(esiti) + 1)), value=0, format_func=etichetta,
                             key=f"passo_{lez.chiave}")
    st.info("Questa è la posizione di partenza. **Trascina la pedina** qui sopra verso destra per vedere le mosse una alla volta.",
            icon=":material/touch_app:")       # sta sotto la pedina e resta sempre visibile
    scacchiera = ct.scacchiera(lez.fen) if passo == 0 else chess.Board(esiti[passo - 1].fen_dopo)
    freccia = None if passo == 0 else esiti[passo - 1].da_a

    sinistra, destra = st.columns(2)
    with sinistra:
        st.image(ct.disegna(scacchiera, freccia, dimensione=420), width=420,
                 alt=f"Scacchiera, {etichetta(passo)}: {ct.descrivi_posizione(scacchiera.fen())}")
    with destra:
        st.markdown(f"#### {etichetta(passo)}")
        if passo > 0:
            commento = lez.passi[passo - 1].commento
            if scacchiera.is_checkmate():
                st.success("**Scacco matto!** " + commento, icon=":material/emoji_events:")
            else:
                st.info(commento, icon=":material/lightbulb:")
        giocate = [f"**{etichetta(i + 1)}**" if i + 1 == passo else etichetta(i + 1) for i in range(len(esiti))]
        st.caption("Mosse: " + "  ·  ".join(giocate))
        st.caption(f"Fonte della spiegazione: `{lez.fonte}`")
else:
    st.caption("Verifica una mossa, o più mosse separate da virgola (e4, e5, Cf3), su una posizione. A controllare è `python-chess`, non il "
               "modello: stessa posizione e stesse mosse, sempre la stessa risposta. Le lettere dei pezzi sono maiuscole: C cavallo, A alfiere, "
               "T torre, D donna, R re (anche le coordinate, e2e4).")

    st.session_state.setdefault("fen", ct.START)
    st.session_state.setdefault("mossa", "")

    fen = st.text_input("Posizione (FEN, oppure «start» per quella iniziale)", key="fen")
    mossa = st.text_input("Mossa, o più mosse separate da virgola", key="mossa", placeholder="Cf3   oppure   e4, e5, Cf3, Cc6")

    try:
        scacchiera = ct.scacchiera(fen)
    except ValueError as errore:
        st.error(str(errore), icon=":material/error:")
        st.stop()

    sequenza = ct.gioca_sequenza(fen, mossa)
    legali = sequenza.legali
    scelta, fen_prima = None, fen
    if legali:
        numero = 1
        if len(legali) > 1:             # più mosse: un cursore per vederle una alla volta (all'inizio mostra l'ultima)
            numero = st.slider("Mossa da mostrare", 1, len(legali), len(legali), key=f"passo_{abs(hash((fen, mossa)))}")
            giocate = [f"**{e.mossa}**" if i == numero - 1 else e.mossa for i, e in enumerate(legali)]
            st.caption("Giocate: " + ", ".join(giocate))
        scelta = legali[numero - 1]
        fen_prima = fen if numero == 1 else legali[numero - 2].fen_dopo

    prima, dopo = st.columns(2)
    with prima:
        st.subheader("Prima della mossa" if scelta else "Posizione")
        st.image(ct.disegna(ct.scacchiera(fen_prima)), width=380, alt=f"Scacchiera: {ct.descrivi_posizione(fen_prima)}")
        st.caption(ct.descrivi_posizione(fen_prima))
    with dopo:
        if scelta:
            st.subheader(f"Dopo {scelta.mossa}")
            st.image(ct.disegna(chess.Board(scelta.fen_dopo), scelta.da_a), width=380, alt=f"Scacchiera dopo la mossa {scelta.mossa}")
            st.caption(ct.descrivi_posizione(scelta.fen_dopo))

    if scelta:
        st.success((f"Mossa {numero}: " if len(legali) > 1 else "") + scelta.messaggio, icon=":material/check_circle:")
    if sequenza.errore:
        quale, testo, esito = sequenza.errore
        if len(sequenza.mosse) > 1:
            st.error(f"Mossa {quale} «{testo}»: " + esito.messaggio.replace("Mossa NON legale: ", "NON legale: "), icon=":material/cancel:")
        else:
            st.error(esito.messaggio, icon=":material/cancel:")

    with st.expander("Mosse legali in questa posizione"):
        st.write(ct.mosse_legali(fen_prima))
