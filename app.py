"""Interfaccia di Chess Tutor (Step 1h):   streamlit run app.py

Pagina larga con le schede in alto (script in `app_pages/`): la chat col tutor, con fonti e costo di ogni risposta, e il quiz su
un documento allegato. I colori stanno in `.streamlit/config.toml` (tema "scacchiera"). Gli aiuti sono in `chess_tutor/webapp.py`.
"""
import streamlit as st

st.set_page_config(page_title="Chess Tutor", page_icon="♟️", layout="wide")

pagina = st.navigation([
    st.Page("app_pages/chat.py", title="Chiedi al tutor", icon="💬", default=True),
    st.Page("app_pages/quiz.py", title="Quiz da un documento", icon="📝"),
], position="top")
pagina.run()
