"""Le lezioni della scheda Scacchiera: ogni mossa è legale e arriva dove la lezione dice (controllato con python-chess, non a occhio)."""
import chess
import pytest

from chess_tutor import chess_tools as ct
from chess_tutor import config, lezioni


def partita(lez):
    """La posizione finale della lezione, giocando tutte le sue mosse con python-chess."""
    seq = ct.gioca_sequenza(lez.fen, lezioni.mosse_della_lezione(lez))
    assert seq.errore is None, f"{lez.chiave}: mossa {seq.errore[0]} «{seq.errore[1]}» non legale: {seq.errore[2].messaggio}"
    assert len(seq.legali) == len(lez.passi)
    return chess.Board(seq.legali[-1].fen_dopo), seq


@pytest.mark.parametrize("lez", lezioni.LEZIONI, ids=lambda lez: lez.chiave)
def test_ogni_mossa_di_ogni_lezione_e_legale(lez):
    partita(lez)


def test_le_lezioni_hanno_chiavi_uniche_gruppi_noti_e_un_commento_per_mossa():
    chiavi = [lez.chiave for lez in lezioni.LEZIONI]
    assert len(set(chiavi)) == len(chiavi) >= 10
    for lez in lezioni.LEZIONI:
        assert lez.gruppo in lezioni.GRUPPI and lez.titolo and lez.spiegazione
        assert all(p.mossa and len(p.commento) > 10 for p in lez.passi)
    assert {lez.gruppo for lez in lezioni.LEZIONI} == set(lezioni.GRUPPI)               # ogni gruppo ha almeno una lezione


def test_ogni_lezione_cita_un_documento_che_esiste():
    for lez in lezioni.LEZIONI:
        assert (config.DATA_DIR / lez.fonte).exists(), f"{lez.chiave}: manca {lez.fonte}"


def test_l_arrocco_corto_porta_il_re_in_g1_e_la_torre_in_f1():
    b, _ = partita(lezioni.cerca("arrocco_corto"))
    assert b.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE) and b.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)
    assert b.piece_at(chess.E1) is None and b.piece_at(chess.H1) is None


def test_l_arrocco_lungo_porta_il_re_in_c1_e_la_torre_in_d1():
    b, _ = partita(lezioni.cerca("arrocco_lungo"))
    assert b.piece_at(chess.C1) == chess.Piece(chess.KING, chess.WHITE) and b.piece_at(chess.D1) == chess.Piece(chess.ROOK, chess.WHITE)
    assert b.piece_at(chess.A1) is None and b.piece_at(chess.E1) is None


def test_l_en_passant_mette_il_pedone_in_d6_e_toglie_quello_nero_di_d5():
    b, _ = partita(lezioni.cerca("en_passant"))
    assert b.piece_at(chess.D6) == chess.Piece(chess.PAWN, chess.WHITE) and b.piece_at(chess.D5) is None


def test_la_promozione_fa_una_donna_in_d8():
    b, _ = partita(lezioni.cerca("promozione"))
    assert b.piece_at(chess.D8) == chess.Piece(chess.QUEEN, chess.WHITE)


@pytest.mark.parametrize("chiave", ["matto_barbiere", "matto_pazzo"])
def test_i_matti_rapidi_finiscono_davvero_con_scacco_matto(chiave):
    b, _ = partita(lezioni.cerca(chiave))
    assert b.is_checkmate()


def test_le_lezioni_di_apertura_partono_dalla_posizione_iniziale_e_non_finiscono_in_matto():
    for lez in lezioni.LEZIONI:
        if lez.gruppo in (lezioni.APERTURE_E4, lezioni.APERTURE_D4):
            b, _ = partita(lez)
            assert lez.fen == "start" and not b.is_game_over()


def test_una_mossa_sbagliata_in_una_lezione_verrebbe_scoperta():
    """Il controllo ha davvero denti: la stessa lezione con una mossa impossibile (il cavallo in diagonale) NON passa."""
    lez = lezioni.cerca("italiana")
    seq = ct.gioca_sequenza(lez.fen, "e4, e5, Ce3")
    assert seq.errore is not None
