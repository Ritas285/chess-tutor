"""Interfaccia di Chess Tutor (Step 1h):   streamlit run app.py

Due pagine (script in `app_pages/`): la chat col tutor, con fonti e costo di ogni risposta, e il quiz su un documento allegato.
Gli aiuti (creazione del tutor, formato dei messaggi) sono in `chess_tutor/webapp.py`.
"""
import streamlit as st

st.set_page_config(page_title="Chess Tutor", page_icon=":material/chess:", layout="centered")

pagina = st.navigation([
    st.Page("app_pages/chat.py", title="Chiedi al tutor", icon=":material/chat:", default=True),
    st.Page("app_pages/quiz.py", title="Quiz da un tuo documento", icon=":material/quiz:"),
])
pagina.run()
