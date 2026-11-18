"""Step 1i: strumenti scacchistici deterministici (python-chess). Nessun modello, nessuna chiave: sempre la stessa risposta."""
import chess
import pytest

from chess_tutor import chess_tools as ct

INIZIO = ct.START
BARBIERE = ct.ESEMPI["Matto del barbiere: tocca al Bianco (prova Dxf7)"]
STALLO = ct.ESEMPI["Stallo: tocca al Nero"]
PROMOZIONE = ct.ESEMPI["Promozione: il pedone è in a7 (prova a8=D)"]
EN_PASSANT = ct.ESEMPI["En passant: tocca al Bianco (prova exd6)"]
SPAGNOLA = ct.ESEMPI["Spagnola: tocca al Bianco (prova Axc6)"]


# ---------- la notazione ----------
@pytest.mark.parametrize("italiano, inglese", [("Cf3", "Nf3"), ("Axc6", "Bxc6"), ("Dxf7", "Qxf7"), ("Tad1", "Rad1"), ("Rg1", "Kg1"),
                                               ("e8=D", "e8=Q"), ("exd5", "exd5"), ("O-O", "O-O"), ("0-0-0", "O-O-O"), ("Cf3+", "Nf3"),
                                               ("Dxf7#", "Qxf7"), (" a8=T ", "a8=R")])
def test_dall_italiano_all_inglese(italiano, inglese):
    assert ct._italiano_in_inglese(italiano) == inglese


@pytest.mark.parametrize("inglese, italiano", [("Nf3", "Cf3"), ("Bxc6", "Axc6"), ("Qxf7#", "Dxf7#"), ("Rad1", "Tad1"), ("Kg1", "Rg1"),
                                               ("e8=Q+", "e8=D+"), ("exd5", "exd5"), ("O-O-O", "O-O-O")])
def test_dall_inglese_all_italiano(inglese, italiano):
    assert ct.san_in_italiano(inglese) == italiano


# ---------- la posizione ----------
def test_la_posizione_iniziale_si_scrive_in_piu_modi():
    for scrittura in ("start", " START ", "", "iniziale", "startpos"):
        assert ct.scacchiera(scrittura).fen() == chess.STARTING_FEN


def test_fen_non_valida_o_impossibile_dice_perche():
    with pytest.raises(ValueError, match="FEN non valida"):
        ct.scacchiera("questa non è una fen")
    with pytest.raises(ValueError, match="posizione impossibile"):
        ct.scacchiera("8/8/8/8/8/8/8/8 w - - 0 1")                       # nessun re
    with pytest.raises(ValueError, match="posizione impossibile"):
        ct.scacchiera("4k3/8/8/8/8/8/8/4K2K w - - 0 1")                  # due re bianchi


# ---------- verifica di una mossa ----------
@pytest.mark.parametrize("mossa", ["Cf3", "Nf3", "g1f3", "Cf3+", " Cf3 ", "cf3".replace("c", "C")])
def test_la_stessa_mossa_in_tre_modi_e_legale(mossa):
    e = ct.controlla_mossa(INIZIO, mossa)
    assert e.legale and e.mossa == "Cf3" and "cavallo del Bianco" in e.messaggio
    assert chess.Board(e.fen_dopo).piece_at(chess.F3).piece_type == chess.KNIGHT and e.da_a == (chess.G1, chess.F3)


def test_le_mosse_di_pedone_e_l_arrocco_non_hanno_lettera():
    assert ct.controlla_mossa(INIZIO, "e4").legale
    b = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    corto, lungo = ct.controlla_mossa(b, "O-O"), ct.controlla_mossa(b, "O-O-O")
    assert corto.legale and "arrocco" in corto.messaggio and lungo.legale
    assert ct.controlla_mossa(b, "0-0").legale                            # con gli zeri

def test_una_mossa_illegale_dice_perche_e_non_cambia_la_posizione():
    casi = [("e5", "nessun pedone del Bianco può andare in e5"),
            ("Ce4", "il cavallo non si muove così: si muove a L"),           # g1 -> e4 non è una L
            ("Ce2", "in e2 c'è già un pezzo tuo"),                          # una L, ma la casa è occupata da un tuo pedone
            ("Axc6", "l'alfiere non si muove così"),                         # c1 -> c6 non è una diagonale
            ("Tf4", "la torre non si muove così: si muove in linea retta"),
            ("Ta4", "la torre ci arriverebbe in linea, ma c'è un pezzo in mezzo"),                                # a1 -> a4 è una colonna, ma c'è il pedone in a2
            ("Rf2", "in f2 c'è già un pezzo tuo")]
    for mossa, atteso in casi:
        e = ct.controlla_mossa(INIZIO, mossa)
        assert not e.legale and "NON legale" in e.messaggio and atteso in e.messaggio, (mossa, e.messaggio)
        assert e.fen_dopo == ""


def test_la_mossa_a_L_del_cavallo_non_viene_mai_dichiarata_impossibile_per_la_sua_forma():
    """Il dubbio di Rita: il cavallo SI muove a L. Le mosse a L non legali devono dire il VERO motivo (casa occupata), non la forma."""
    for mossa in ("Ce2", "Cd2"):                                             # da g1 / b1: due case e una di lato, ma occupate
        e = ct.controlla_mossa(INIZIO, "C" + mossa[1:])
        assert "non si muove così" not in e.messaggio
    assert ct.controlla_mossa(INIZIO, "Cf3").legale and ct.controlla_mossa(INIZIO, "Ch3").legale

def test_l_arrocco_impossibile_ha_il_suo_motivo():
    e = ct.controlla_mossa(INIZIO, "O-O")
    assert not e.legale and "arroccare" in e.messaggio


def test_il_re_inchiodato_o_sotto_scacco_e_spiegato():
    # La torre nera in e8 dà scacco al re bianco in e1 attraverso la colonna e: il cavallo in c3 non lo risolve.
    sotto_scacco = "4r1k1/8/8/8/8/8/8/4K1N1 w - - 0 1"
    e = ct.controlla_mossa(sotto_scacco, "Cf3")
    assert not e.legale and "sotto scacco" in e.messaggio
    # Cavallo inchiodato: muoverlo lascerebbe il re sotto scacco.
    inchiodato = "4r1k1/8/8/8/8/8/4N3/4K3 w - - 0 1"
    e = ct.controlla_mossa(inchiodato, "Cc3")
    assert not e.legale and "scacco" in e.messaggio


def test_scacco_matto_promozione_en_passant_e_stallo_sono_riconosciuti():
    matto = ct.controlla_mossa(BARBIERE, "Dxf7")
    assert matto.legale and "SCACCO MATTO" in matto.messaggio and matto.mossa == "Dxf7#"
    prom = ct.controlla_mossa(PROMOZIONE, "a8=D")
    assert prom.legale and "promuove a donna" in prom.messaggio and prom.mossa.startswith("a8=D")
    ep = ct.controlla_mossa(EN_PASSANT, "exd6")
    assert ep.legale and "en passant" in ep.messaggio
    assert "partita è già finita" in ct.controlla_mossa(STALLO, "Rg8").messaggio


def test_una_mossa_ambigua_chiede_di_specificare():
    due_torri = "4k3/8/8/8/8/4K3/8/R6R w - - 0 1"                     # entrambe le torri possono andare in d1
    e = ct.controlla_mossa(due_torri, "Td1")
    assert not e.legale and "ambigua" in e.messaggio
    assert ct.controlla_mossa(due_torri, "Tad1").legale


def test_notazione_inglese_della_torre_come_ripiego():
    """"Rd1" per un italiano è il RE; se la lettura italiana non è legale si prova quella inglese (torre)."""
    due_torri = "4k3/8/8/8/8/8/8/R3K3 w - - 0 1"
    e = ct.controlla_mossa(due_torri, "Rd1")                          # il re può andare in d1: lettura italiana legale
    assert e.legale and "re del Bianco" in e.messaggio
    solo_torre = "4k3/8/8/8/8/8/8/R6K w - - 0 1"
    e = ct.controlla_mossa(solo_torre, "Ra2")                         # il re non arriva in a2: ripiego inglese, torre
    assert e.legale and "torre del Bianco" in e.messaggio


def test_input_sbagliati_non_sollevano_eccezioni():
    assert "Scrivi una mossa" in ct.controlla_mossa(INIZIO, "  ").messaggio
    assert "Non riesco a leggere" in ct.controlla_mossa(INIZIO, "boh").messaggio
    assert "Non riesco a leggere" in ct.controlla_mossa(INIZIO, "💥").messaggio
    assert "FEN non valida" in ct.verifica_mossa("asdf", "e4")
    assert "posizione impossibile" in ct.verifica_mossa("8/8/8/8/8/8/8/8 w - - 0 1", "e4")
    assert ct.controlla_mossa(INIZIO, "e4" * 500).legale is False


def test_e_deterministico():
    assert {ct.verifica_mossa(BARBIERE, "Dxf7") for _ in range(20)} == {ct.verifica_mossa(BARBIERE, "Dxf7")}


# ---------- altri strumenti ----------
def test_mosse_legali_in_italiano():
    testo = ct.mosse_legali(INIZIO)
    assert "20 mosse legali" in testo and "Cf3" in testo and "Nf3" not in testo and "e4" in testo
    assert "Nessuna mossa legale" in ct.mosse_legali("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1") and "stallo" in ct.mosse_legali(STALLO)
    assert "FEN non valida" in ct.mosse_legali("boh")


def test_descrivi_posizione():
    assert ct.descrivi_posizione(INIZIO) == ("Tocca al Bianco. Materiale: Bianco 39, Nero 39 (parità di materiale). "
                                             "Nessuno scacco. Mosse legali: 20.")
    assert "Bianco in vantaggio di 9 punti" in ct.descrivi_posizione("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
    assert "sotto scacco" in ct.descrivi_posizione("4k3/8/8/8/8/8/8/4RK2 b - - 0 1")
    dopo_matto = ct.controlla_mossa(BARBIERE, "Dxf7").fen_dopo
    assert "Scacco matto, ha vinto il Bianco" in ct.descrivi_posizione(dopo_matto)
    assert "vantaggio di 1 punto)" in ct.descrivi_posizione(dopo_matto)                 # singolare
    assert ct.descrivi_posizione("boh").startswith("FEN non valida")


def test_gli_esempi_sono_posizioni_valide_con_la_mossa_suggerita_legale():
    for nome, fen in ct.ESEMPI.items():
        ct.scacchiera(fen)                                            # nessuna eccezione
    assert ct.controlla_mossa(BARBIERE, "Dxf7").legale and ct.controlla_mossa(EN_PASSANT, "exd6").legale
    assert ct.controlla_mossa(PROMOZIONE, "a8=D").legale
    e = ct.controlla_mossa(SPAGNOLA, "Axc6")                         # l'alfiere (A) cattura (x) il cavallo nero in c6
    assert e.legale and e.mossa == "Axc6" and "cattura un pezzo" in e.messaggio and "alfiere del Bianco" in e.messaggio


def test_il_disegno_e_un_svg_con_la_freccia():
    b = ct.scacchiera(INIZIO)
    senza, con = ct.disegna(b), ct.disegna(b, (chess.G1, chess.F3))
    assert senza.startswith("<svg") and "arrow" not in senza.lower()
    assert len(con) > len(senza)                                      # la freccia aggiunge elementi







# ---------- il difetto segnalato da Rita: "cf3" minuscolo ----------
def test_le_lettere_dei_pezzi_vanno_maiuscole_e_il_messaggio_lo_dice():
    """Regola semplice, nessuna lettura "furba": "cf3" non è una mossa di cavallo. Il messaggio dice cosa è sbagliato e come scriverla."""
    for mossa, giusta in (("cf3", "Cf3"), ("ce4", "Ce4"), ("ac4", "Ac4"), ("tf4", "Tf4"), ("dh5", "Dh5")):
        e = ct.controlla_mossa(INIZIO, mossa)
        assert not e.legale and "MAIUSCOLE" in e.messaggio and f"«{giusta}»" in e.messaggio, (mossa, e.messaggio)
        assert "scacco" not in e.messaggio.lower().replace("scacchi", "")
    assert ct.controlla_mossa(INIZIO, "Cf3").legale and "MAIUSCOLE" not in ct.controlla_mossa(INIZIO, "Cf3").messaggio


def test_le_mosse_di_pedone_in_minuscolo_restano_valide():
    """Se la lettura da pedone è legale vince quella: "cc3" è il pedone in c3, "Cc3" è il cavallo."""
    assert ct.controlla_mossa(INIZIO, "cc3").mossa == "c3" and ct.controlla_mossa(INIZIO, "dd3").mossa == "d3"
    assert ct.controlla_mossa(INIZIO, "Cc3").mossa == "Cc3"
    assert ct.controlla_mossa(INIZIO, "e4").legale and "MAIUSCOLE" not in ct.controlla_mossa(INIZIO, "e5").messaggio


def test_il_motivo_non_e_mai_quello_di_un_altro_pezzo():
    """Prima "cf3" senza il cavallo in g1 diceva "lascerebbe il re sotto scacco", guardando il PEDONE in f2 che arriva in f3."""
    senza_cavallo = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKB1R w KQkq - 0 1"
    assert "scacco" not in ct.controlla_mossa(senza_cavallo, "cf3").messaggio
    assert "il cavallo non si muove così" in ct.controlla_mossa(senza_cavallo, "Cf3").messaggio
    assert "nessun pedone della colonna e" in ct.controlla_mossa(INIZIO, "exd5").messaggio
    assert "Non riesco a leggere" in ct.controlla_mossa(INIZIO, "zz9").messaggio and "MAIUSCOLE" not in ct.controlla_mossa(INIZIO, "zz9").messaggio




# ---------- più mosse di fila, separate da virgola ----------
def test_una_sequenza_si_gioca_in_ordine():
    s = ct.gioca_sequenza(INIZIO, "e4, e5, Cf3, Cc6")
    assert s.mosse == ["e4", "e5", "Cf3", "Cc6"] and len(s.legali) == 4 and s.errore is None
    assert [e.mossa for e in s.legali] == ["e4", "e5", "Cf3", "Cc6"]
    # ogni mossa parte dalla posizione lasciata dalla precedente: il Nero muove dopo il Bianco
    assert chess.Board(s.legali[-1].fen_dopo).fen() == chess.Board().fen().replace("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                                                                                      "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")


def test_la_sequenza_si_ferma_alla_prima_mossa_non_legale_e_dice_quale():
    s = ct.gioca_sequenza(INIZIO, "e4, e4, Cf3")                           # la seconda è del Nero: un pedone nero non va in e4
    assert len(s.legali) == 1 and len(s.esiti) == 2                       # la terza non si prova
    quale, testo, esito = s.errore
    assert quale == 2 and testo == "e4" and "NON legale" in esito.messaggio


def test_la_sequenza_accetta_numerazione_spazi_e_parti_vuote():
    assert ct.gioca_sequenza(INIZIO, "1.e4, e5, 2.Cf3").mosse == ["e4", "e5", "Cf3"]
    assert ct.gioca_sequenza(INIZIO, " e4 ,, e5 ; Cf3 \n Cc6 ,").mosse == ["e4", "e5", "Cf3", "Cc6"]
    assert ct.gioca_sequenza(INIZIO, "").esiti == [] and ct.gioca_sequenza(INIZIO, " , ,").mosse == []


def test_la_sequenza_del_matto_del_barbiere_finisce_con_il_matto():
    s = ct.gioca_sequenza(INIZIO, "e4, e5, Ac4, Cc6, Dh5, Cf6, Dxf7")
    assert len(s.legali) == 7 and s.errore is None and "SCACCO MATTO" in s.legali[-1].messaggio


def test_una_sequenza_con_una_posizione_sbagliata_non_solleva_eccezioni():
    s = ct.gioca_sequenza("boh", "e4, e5")
    assert s.errore is not None and "FEN non valida" in s.errore[2].messaggio and len(s.esiti) == 1


def test_una_sequenza_con_una_mossa_sola_e_come_la_mossa_singola():
    assert ct.gioca_sequenza(INIZIO, "Cf3").legali[0].mossa == ct.controlla_mossa(INIZIO, "Cf3").mossa
