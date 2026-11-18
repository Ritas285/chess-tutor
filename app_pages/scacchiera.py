import chess
import streamlit as st

from chess_tutor import chess_tools as ct

st.title("♞ Scacchiera")
st.caption("Verifica una mossa, o più mosse separate da virgola (e4, e5, Cf3), su una posizione. A controllare è `python-chess`, non il "
           "modello: stessa posizione e stesse mosse, sempre la stessa risposta. Le lettere dei pezzi sono maiuscole: C cavallo, A alfiere, "
           "T torre, D donna, R re (anche le coordinate, e2e4).")

st.session_state.setdefault("fen", ct.START)
st.session_state.setdefault("mossa", "")


def carica_esempio():
    st.session_state.fen = ct.ESEMPI[st.session_state.esempio]
    st.session_state.mossa = ""


st.selectbox("Posizioni di esempio", list(ct.ESEMPI), key="esempio", on_change=carica_esempio)
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
