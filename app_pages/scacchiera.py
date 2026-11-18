import chess
import streamlit as st

from chess_tutor import chess_tools as ct

st.title("♞ Scacchiera")
st.caption("Verifica una mossa su una posizione. A controllare è `python-chess`, non il modello: stessa posizione e stessa mossa, "
           "sempre la stessa risposta. Notazione italiana: C cavallo, A alfiere, T torre, D donna, R re (anche le coordinate, e2e4).")

st.session_state.setdefault("fen", ct.START)
st.session_state.setdefault("mossa", "")


def carica_esempio():
    st.session_state.fen = ct.ESEMPI[st.session_state.esempio]
    st.session_state.mossa = ""


st.selectbox("Posizioni di esempio", list(ct.ESEMPI), key="esempio", on_change=carica_esempio)
fen = st.text_input("Posizione (FEN, oppure «start» per quella iniziale)", key="fen")
mossa = st.text_input("Mossa da verificare", key="mossa", placeholder="Cf3, Axc6, Dxf7, O-O, e2e4")

try:
    scacchiera = ct.scacchiera(fen)
except ValueError as errore:
    st.error(str(errore), icon=":material/error:")
    st.stop()

esito = ct.controlla_mossa(fen, mossa) if mossa.strip() else None

prima, dopo = st.columns(2)
with prima:
    st.subheader("Posizione")
    st.image(ct.disegna(scacchiera), width=380, alt=f"Scacchiera: {ct.descrivi_posizione(fen)}")
    st.caption(ct.descrivi_posizione(fen))
with dopo:
    if esito and esito.legale:
        st.subheader("Dopo la mossa")
        st.image(ct.disegna(chess.Board(esito.fen_dopo), esito.da_a), width=380, alt=f"Scacchiera dopo la mossa {esito.mossa}")

if esito:
    if esito.legale:
        st.success(esito.messaggio, icon=":material/check_circle:")
    else:
        st.error(esito.messaggio, icon=":material/cancel:")

with st.expander("Mosse legali in questa posizione"):
    st.write(ct.mosse_legali(fen))

