import streamlit as st

from chess_tutor import quiz as quizmod
from chess_tutor import webapp

st.title("📝 Quiz da un tuo documento")
st.caption("Allega appunti o una dispensa (.md, .txt, .pdf). Il tutor scrive domande **solo** dal testo e ciascuna si appoggia a "
           "una frase del documento: se la frase non si ritrova, la domanda viene scartata.")

tutor = webapp.tutor_o_ferma()
st.session_state.setdefault("quiz", None)
st.session_state.setdefault("esiti", {})

allegato = st.file_uploader("Documento", type=["md", "txt", "pdf"], key="allegato")
n = st.slider("Numero di domande", 3, quizmod.MAX_DOMANDE, 5, key="n_domande")

if st.button("Genera il quiz", icon=":material/auto_awesome:", disabled=allegato is None, type="primary", key="genera"):
    try:
        testo = quizmod.leggi_allegato(allegato.name, allegato.getvalue())
    except Exception as errore:             # PDF danneggiato o formato non leggibile: si dice, non si rompe l'app
        st.error(f"Non riesco a leggere il file: {errore}", icon=":material/error:")
        st.stop()
    if not testo.strip():
        st.error("Il file non contiene testo leggibile (forse è una scansione). Prova con un altro file.", icon=":material/error:")
        st.stop()
    with st.spinner("Scrivo le domande…"):
        domande, avvisi = quizmod.genera_quiz(tutor.client, testo, n)
    for chiave in [k for k in st.session_state if k.startswith(("risposta_", "verifica_"))]:
        del st.session_state[chiave]        # le risposte del quiz precedente non devono restare nelle nuove domande
    st.session_state.quiz = {"nome": allegato.name, "domande": domande, "avvisi": avvisi, "caratteri": len(testo),
                             "anteprima": testo[:1500]}
    st.session_state.esiti = {}

quiz = st.session_state.quiz
if quiz:
    with st.expander(f"Testo letto da «{quiz['nome']}» ({quiz['caratteri']} caratteri): controlla che sia leggibile"):
        st.text(quiz["anteprima"])
    for avviso in quiz["avvisi"]:
        st.warning(avviso, icon=":material/warning:")
    if not quiz["domande"]:
        st.info("Nessuna domanda valida da questo documento. Prova con un testo più lungo o più chiaro.", icon=":material/help:")

    for i, q in enumerate(quiz["domande"]):
        with st.container(border=True):
            st.markdown(f"**{i + 1}. {q.domanda}**")
            if q.tipo == "scelta_multipla":
                risposta = st.radio("Scegli la risposta", q.scelte, index=None, key=f"risposta_{i}", label_visibility="collapsed")
            else:
                risposta = st.text_input("La tua risposta", key=f"risposta_{i}")
            if st.button("Verifica", key=f"verifica_{i}", disabled=not risposta):
                with st.spinner("Controllo la risposta…"):
                    giudizio, _ = quizmod.verifica_domanda(q, risposta, client=tutor.client)
                st.session_state.esiti[i] = (giudizio, risposta)
            verificata = st.session_state.esiti.get(i)
            if verificata and verificata[1] == risposta:        # se cambi la risposta, l'esito vecchio non si mostra più
                webapp.mostra_esito(verificata[0].esito, verificata[0].feedback)
                st.caption(f"Nel documento: «{q.citazione}»")

    if st.session_state.esiti:
        st.divider()
        st.markdown(f"**Verificate {len(st.session_state.esiti)} su {len(quiz['domande'])}:** "
                    f"{webapp.riepilogo_quiz(st.session_state.esiti)}")
