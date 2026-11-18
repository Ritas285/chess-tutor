"""Step 3: le mosse scritte nei documenti sono legali (chess_tutor/contenuti.py). Nessuna chiave, nessuna rete."""
from chess_tutor import config, contenuti


def sequenze(testo: str) -> list[list[str]]:
    return [s.mosse for s in contenuti.estrai_sequenze(testo)]


# ---------- l'estrazione ----------
def test_estrae_una_sequenza_con_numeri_e_segni():
    assert sequenze("Il matto: 1.e4 e5 2.Ac4 Cc6 3.Dh5 Cf6?? 4.Dxf7#. Il Bianco attacca f7.") == [["e4", "e5", "Ac4", "Cc6", "Dh5", "Cf6", "Dxf7#"]]


def test_si_ferma_alla_prima_parola_che_non_e_una_mossa_o_al_punto_finale():
    assert sequenze("Esempio: 1.e4 e5 2.Cf3 Cc6 3.Ac4 vuol dire: il Bianco muove") == [["e4", "e5", "Cf3", "Cc6", "Ac4"]]
    assert sequenze("Come Bianco, 1.e4 porta partite aperte.") == [["e4"]]
    assert sequenze("1.e4 c5. Il Nero non copia il Bianco.") == [["e4", "c5"]]


def test_numeri_di_mossa_staccati_e_segni_dopo_la_mossa():
    assert sequenze("1.e4 e5 2. Cf3 Cc6 3.Ab5 a6 4.Axc6 dxc6 5.Cxe5? Dd4 il Nero recupera") == \
        [["e4", "e5", "Cf3", "Cc6", "Ab5", "a6", "Axc6", "dxc6", "Cxe5", "Dd4"]]


def test_le_sequenze_che_non_iniziano_con_1_si_ignorano():
    assert sequenze("Il Nero risponde 3...Ac5 (Giuoco Piano) oppure 2.Cf3. Poi 5.d4") == []


def test_piu_sequenze_nella_stessa_riga_e_numero_di_riga():
    s = contenuti.estrai_sequenze("riga uno\nDopo 1.e4 e5 oppure 1.d4 d5 si gioca.", "x.md")
    assert [(q.file, q.riga, q.mosse) for q in s] == [("x.md", 2, ["e4", "e5"]), ("x.md", 2, ["d4", "d5"])]


def test_parole_che_assomigliano_a_mosse_non_ingannano():
    assert sequenze("1.e4 Come funziona il resto") == [["e4"]]          # "Come" non è una mossa


# ---------- il controllo ----------
def test_una_sequenza_con_una_mossa_impossibile_e_segnalata_con_il_numero():
    """L'alfiere in f1 non può arrivare in c5: è proprio il tipo di errore che il controllo deve prendere."""
    problemi = contenuti.controlla_sequenze(contenuti.estrai_sequenze("1.e4 e5 2.Cf3 Cc6 3.Ac5 Cf6", "falso.md"))
    assert len(problemi) == 1
    p = problemi[0]
    assert p.sequenza.file == "falso.md" and p.mossa_numero == 5 and p.mossa == "Ac5" and "NON legale" in p.messaggio


def test_le_sequenze_legali_non_danno_problemi():
    assert contenuti.controlla_sequenze(contenuti.estrai_sequenze("1.e4 e5 2.Cf3 Cc6 3.Ac4 Ac5")) == []


def test_un_documento_su_disco_si_controlla(tmp_path):
    (tmp_path / "r").mkdir()
    (tmp_path / "r" / "ok.md").write_text("# Ok\n1.d4 d5 2.c4", encoding="utf-8")
    (tmp_path / "r" / "ko.md").write_text("# Ko\nPoi 1.e4 e4 e5", encoding="utf-8")        # il Nero non può muovere un pedone in e4
    trovate, problemi = contenuti.controlla_documenti(tmp_path)
    assert len(trovate) == 2 and [p.sequenza.file.replace("\\", "/") for p in problemi] == ["r/ko.md"]


# ---------- il corpus vero ----------
def test_tutte_le_mosse_scritte_nei_documenti_del_corpus_sono_legali():
    trovate, problemi = contenuti.controlla_documenti()
    assert len(trovate) >= 15, "il controllo non vede abbastanza sequenze: l'estrazione è rotta?"       # un test che non può fallire non vale
    assert not problemi, "\n".join(f"{p.sequenza.file}:{p.sequenza.riga} mossa {p.mossa_numero} «{p.mossa}»: {p.messaggio}" for p in problemi)


def test_il_corpus_contiene_le_sequenze_note():
    tutte = {" ".join(s.mosse) for s in contenuti.controlla_documenti()[0]}
    assert "e4 e5 Ac4 Cc6 Dh5 Cf6 Dxf7#" in tutte                          # il matto del barbiere
    assert "f3 e5 g4 Dh4#" in tutte                                         # il matto del pazzo
    assert config.DATA_DIR.exists()
