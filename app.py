"""Interfaccia di Chess Tutor (Step 1h):   streamlit run app.py

Pagina larga con le schede in alto (script in `app_pages/`): la chat col tutor, con fonti e costo di ogni risposta, il quiz su
un documento allegato e la scacchiera (lezioni su arrocco, aperture e matti; verifica delle mosse con python-chess). I colori stanno in `.streamlit/config.toml` (tema "scacchiera"). Gli aiuti sono in `chess_tutor/webapp.py`.
"""
import streamlit as st

from chess_tutor import webapp

st.set_page_config(page_title="Chess Tutor", page_icon="♟️", layout="wide")
webapp.mostra_intestazione()          # sfondo a scacchiera + marchio, uguali in tutte le pagine

pagina = st.navigation([
    st.Page("app_pages/chat.py", title="Chiedi al tutor", icon="💬", default=True),
    st.Page("app_pages/quiz.py", title="Quiz da un documento", icon="📝"),
    st.Page("app_pages/scacchiera.py", title="Scacchiera", icon=":material/chess_knight:"),
], position="top")
pagina.run()

