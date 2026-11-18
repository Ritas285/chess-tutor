"""Strumenti scacchistici DETERMINISTICI con python-chess (Step 1i). Nessun modello, nessuna rete: stessa domanda, stessa risposta.

Regola del progetto (AGENTS.md): ogni mossa su una posizione concreta passa da qui, mai dalla memoria del modello. Un modello può
inventare una posizione o una mossa "legale": python-chess no. (`python-chess` è l'unica libreria fuori dal corso, scelta apposta.)

Notazione ITALIANA come nei documenti del tutor: R re, D donna, T torre, A alfiere, C cavallo, pedone senza lettera
(Cf3, Axc6, Dxf7#, e8=D, Tad1, O-O, O-O-O). Si accettano anche le coordinate (e2e4) e, se la lettura italiana fallisce, la
notazione inglese (Nf3, Bxc6, Qxf7). Attenzione: con "R" si intende il RE; per una torre inglese ("Rd1") usa "T" o le coordinate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import chess
import chess.svg

START = "start"
_IT_A_EN = {"R": "K", "D": "Q", "T": "R", "A": "B", "C": "N"}      # lettera italiana -> inglese
_EN_A_IT = {"K": "R", "Q": "D", "R": "T", "B": "A", "N": "C"}      # lettera inglese -> italiana
_NOMI = {chess.PAWN: "pedone", chess.KNIGHT: "cavallo", chess.BISHOP: "alfiere", chess.ROOK: "torre",
         chess.QUEEN: "donna", chess.KING: "re"}
_VALORI = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
_RE_UCI = re.compile(r"^[a-h][1-8][a-h][1-8][qrbn]?$")
_RE_CASA = re.compile(r"[a-h][1-8]")


def _colore(b: chess.Board) -> str:
    return "Bianco" if b.turn == chess.WHITE else "Nero"


# ---------- la posizione ----------
def scacchiera(fen: str = START) -> chess.Board:
    """La scacchiera da una FEN ("start" = posizione iniziale). Solleva ValueError con un messaggio chiaro se la FEN non si legge
    o se la posizione è impossibile (per esempio senza un re)."""
    testo = (fen or "").strip()
    if testo.lower() in ("", START, "startpos", "iniziale"):
        return chess.Board()
    try:
        b = chess.Board(testo)
    except ValueError as errore:
        raise ValueError(f"FEN non valida: {errore}") from errore
    stato = b.status()
    if stato != chess.STATUS_VALID:
        motivi = ", ".join(s.name.lower().replace("_", " ") for s in chess.Status if s and stato & s)
        raise ValueError(f"posizione impossibile ({motivi})")
    return b


def san_in_italiano(san: str) -> str:
    """"Nf3" -> "Cf3", "Bxc6" -> "Axc6", "e8=Q" -> "e8=D". L'arrocco e le mosse di pedone restano uguali."""
    if san and san[0] in "KQRBN":
        san = _EN_A_IT[san[0]] + san[1:]
    return re.sub(r"=([QRBN])", lambda m: "=" + _EN_A_IT[m.group(1)], san)


def _italiano_in_inglese(mossa: str) -> str:
    """"Cf3" -> "Nf3", "Axc6" -> "Bxc6", "e8=D" -> "e8=Q". Toglie spazi e segni (+ # ! ?) e normalizza l'arrocco."""
    m = re.sub(r"[+#!?\s]|e\.p\.", "", mossa.strip())
    if re.fullmatch(r"[Oo0]-[Oo0]-[Oo0]", m):
        return "O-O-O"
    if re.fullmatch(r"[Oo0]-[Oo0]", m):
        return "O-O"
    if m and m[0] in _IT_A_EN:
        m = _IT_A_EN[m[0]] + m[1:]
    return re.sub(r"=([DTAC])", lambda x: "=" + _IT_A_EN[x.group(1)], m)


def _inglese(mossa: str) -> str:
    """La stessa mossa letta come notazione inglese (solo segni tolti, lettere invariate)."""
    m = re.sub(r"[+#!?\s]|e\.p\.", "", mossa.strip())
    return {"0-0": "O-O", "0-0-0": "O-O-O", "o-o": "O-O", "o-o-o": "O-O-O"}.get(m, m)


# ---------- verifica di una mossa ----------
@dataclass
class EsitoMossa:
    legale: bool
    messaggio: str
    mossa: str = ""                      # la mossa in notazione italiana normalizzata (se legale)
    fen_dopo: str = ""                   # la posizione dopo la mossa (se legale)
    da_a: tuple[int, int] | None = None  # case di partenza e di arrivo (per disegnare la freccia)


def _forma_impossibile_da_pedone(lettura: str) -> bool:
    """"cf3": un pedone cattura solo sulla colonna accanto, quindi da c a f non è una mossa di pedone."""
    m = re.fullmatch(r"([a-h])x?([a-h])[1-8]", lettura)
    return bool(m) and abs(ord(m.group(1)) - ord(m.group(2))) > 1


def _suggerimento_maiuscola(mossa: str) -> str:
    """Se la mossa inizia con una lettera minuscola che di solito è un pezzo ("cf3", "tf4"), ricorda che i pezzi vanno MAIUSCOLI.
    Non si corregge in silenzio: nella notazione la minuscola è una colonna, e una lettura "furba" crea confusione."""
    testo = mossa.strip()
    if len(testo) >= 3 and testo[0] in "rdtacbnkq":
        return (f" Le lettere dei pezzi si scrivono MAIUSCOLE (C cavallo, A alfiere, T torre, D donna, R re): "
                f"forse intendevi «{testo[0].upper() + testo[1:]}»? Una lettera minuscola indica una colonna.")
    return ""


def _provare(b: chess.Board, mossa: str) -> tuple[chess.Move | None, str]:
    """Prova le letture possibili della mossa: -> (mossa legale o None, errore più informativo)."""
    testo = mossa.strip()
    candidati: list[tuple[str, str]] = []                  # (testo, etichetta di come è stato letto)
    if _RE_UCI.match(testo.lower()):
        candidati.append((testo.lower(), "coordinate"))
    candidati.append((_italiano_in_inglese(testo), "italiano"))
    if _inglese(testo) != _italiano_in_inglese(testo):
        candidati.append((_inglese(testo), "inglese"))
    illegale = ""
    for lettura, etichetta in candidati:
        try:
            return (b.parse_uci(lettura) if etichetta == "coordinate" else b.parse_san(lettura)), ""
        except chess.AmbiguousMoveError:
            return None, "ambigua"
        except chess.IllegalMoveError:
            illegale = illegale or lettura
        except (chess.InvalidMoveError, ValueError):
            pass
    return (None, f"illegale:{illegale}") if illegale else (None, "illeggibile")

def _motivo_illegale(b: chess.Board, lettura: str) -> str:
    """Perché una mossa ben scritta non si può fare: l'arrocco, il re sotto scacco, nessun pezzo che arrivi lì."""
    if lettura in ("O-O", "O-O-O"):
        return ("non puoi arroccare ora: il re o la torre si sono già mossi, ci sono pezzi in mezzo, il re è sotto scacco o "
                "attraverserebbe una casa attaccata")
    casa = _RE_CASA.findall(lettura)
    pezzo = {"K": chess.KING, "Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}.get(lettura[:1], chess.PAWN)
    if not casa:
        return "la mossa non è possibile in questa posizione"
    arrivo = chess.parse_square(casa[-1])
    if b.color_at(arrivo) == b.turn:
        return f"in {casa[-1]} c'è già un pezzo tuo: non puoi andarci"
    colonna = None                       # "exd5": il pedone deve partire dalla colonna e, non da un'altra
    if pezzo == chess.PAWN:
        da_colonna = re.match(r"^([a-h])x?[a-h][1-8]", lettura)
        colonna = ord(da_colonna.group(1)) - ord("a") if da_colonna else None
    possibili = [m for m in b.pseudo_legal_moves if m.to_square == arrivo and b.piece_type_at(m.from_square) == pezzo
                 and (colonna is None or chess.square_file(m.from_square) == colonna)]
    if possibili:        # un pezzo ci arriverebbe, ma qualcosa lo impedisce: il re finirebbe (o resterebbe) sotto scacco
        if b.is_check():
            return f"il tuo re è sotto scacco e questa mossa non lo risolve ({casa[-1]})"
        return "lascerebbe il tuo re sotto scacco (il pezzo è inchiodato o il re andrebbe su una casa attaccata)"
    if pezzo == chess.PAWN:
        if colonna is not None:
            return f"nessun pedone della colonna {chr(ord('a') + colonna)} può andare in {casa[-1]} in questa posizione"
        return f"nessun pedone del {_colore(b)} può andare in {casa[-1]} in questa posizione"
    mie = list(b.pieces(pezzo, b.turn))
    if not mie:
        return f"il {_colore(b)} non ha {_NESSUNO[pezzo]}"
    if not any(_raggiungibile_in_teoria(pezzo, da, arrivo) for da in mie):
        return f"{_ARTICOLO[pezzo]} non si muove così: si muove {_COME_SI_MUOVE[pezzo]}"
    return f"{_ARTICOLO[pezzo]} ci arriverebbe in linea, ma c'è un pezzo in mezzo"


_ARTICOLO = {chess.PAWN: "il pedone", chess.KNIGHT: "il cavallo", chess.BISHOP: "l'alfiere", chess.ROOK: "la torre", chess.QUEEN: "la donna", chess.KING: "il re"}
_NESSUNO = {chess.PAWN: "nessun pedone", chess.KNIGHT: "nessun cavallo", chess.BISHOP: "nessun alfiere", chess.ROOK: "nessuna torre", chess.QUEEN: "nessuna donna", chess.KING: "nessun re"}
_COME_SI_MUOVE = {chess.KNIGHT: "a L (due case in una direzione e una di lato)", chess.BISHOP: "in diagonale",
                  chess.ROOK: "in linea retta, su colonna o traversa", chess.QUEEN: "in linea retta o in diagonale",
                  chess.KING: "di una sola casa in ogni direzione"}


def _raggiungibile_in_teoria(pezzo: int, da: int, a: int) -> bool:
    """Il pezzo, su una scacchiera VUOTA, arriverebbe da `da` ad `a`? (serve a distinguere "non si muove così" da "c'è un pezzo in mezzo")"""
    dx, dy = abs(chess.square_file(da) - chess.square_file(a)), abs(chess.square_rank(da) - chess.square_rank(a))
    if pezzo == chess.KNIGHT:
        return {dx, dy} == {1, 2}
    if pezzo == chess.KING:
        return max(dx, dy) == 1
    diagonale, retta = dx == dy and dx > 0, (dx == 0) != (dy == 0)
    return {chess.BISHOP: diagonale, chess.ROOK: retta, chess.QUEEN: diagonale or retta}[pezzo]


def controlla_mossa(fen: str, mossa: str) -> EsitoMossa:
    """La mossa è legale nella posizione? Se sì dice cosa fa (cattura, scacco, matto…), se no PERCHÉ. Mai eccezioni per input sbagliati."""
    try:
        b = scacchiera(fen)
    except ValueError as errore:
        return EsitoMossa(False, str(errore))
    if not mossa.strip():
        return EsitoMossa(False, "Scrivi una mossa, per esempio Cf3, Axc6, O-O oppure e2e4.")
    if b.is_game_over():
        return EsitoMossa(False, "La partita è già finita in questa posizione: " + _fine_partita(b) + ".")
    m, errore = _provare(b, mossa)
    if m is None:
        if errore == "ambigua":
            return EsitoMossa(False, f"«{mossa}» è ambigua: più pezzi possono farla. Indica la colonna o la traversa di partenza (per esempio Tad1).")
        if errore.startswith("illegale:"):
            lettura = errore.split(':', 1)[1]
            if _forma_impossibile_da_pedone(lettura):          # "cf3": non è una mossa di pedone, e il motivo non è "il re sotto scacco"
                return EsitoMossa(False, f"«{mossa.strip()}» non è una mossa valida: così si scrive un pedone, e un pedone non va da {lettura[0]} a {lettura[-2:]}."
                                  + (_suggerimento_maiuscola(mossa) or ""))
            return EsitoMossa(False, f"Mossa NON legale: {_motivo_illegale(b, lettura)}.")
        return EsitoMossa(False, f"Non riesco a leggere «{mossa}». Usa la notazione italiana (Cf3, Axc6, Dxf7, e8=D, O-O) o le coordinate (e2e4)."
                          + _suggerimento_maiuscola(mossa))
    cattura = b.is_capture(m)
    en_passant = b.is_en_passant(m)
    arrocco = b.is_castling(m)
    nome = _NOMI[b.piece_type_at(m.from_square)]
    san = san_in_italiano(b.san(m))
    chi = _colore(b)
    b.push(m)
    note = []
    if arrocco:
        note.append("è un arrocco")
    if en_passant:
        note.append("cattura en passant")
    elif cattura:
        note.append("cattura un pezzo")
    if m.promotion:
        note.append(f"il pedone si promuove a {_NOMI[m.promotion]}")
    if b.is_checkmate():
        note.append("SCACCO MATTO")
    elif b.is_check():
        note.append("dà scacco")
    elif b.is_stalemate():
        note.append("STALLO: patta")
    dettaglio = f" ({', '.join(note)})" if note else ""
    return EsitoMossa(True, f"Mossa legale: {san} — {nome} del {chi}{dettaglio}.", san, b.fen(), (m.from_square, m.to_square))


@dataclass
class Sequenza:
    """Più mosse una dopo l'altra (separate da virgole), giocate in ordine a partire da una posizione. Si ferma alla prima non legale."""
    mosse: list[str]                      # le mosse lette dal testo, nell'ordine
    esiti: list[EsitoMossa]               # un esito per ogni mossa PROVATA (l'ultimo è quello non legale, se c'è)

    @property
    def legali(self) -> list[EsitoMossa]:
        return [e for e in self.esiti if e.legale]

    @property
    def errore(self) -> tuple[int, str, EsitoMossa] | None:
        """(numero della mossa da 1, testo scritto, esito) della prima mossa non legale; None se sono tutte legali."""
        if self.esiti and not self.esiti[-1].legale:
            return len(self.esiti), self.mosse[len(self.esiti) - 1], self.esiti[-1]
        return None


def gioca_sequenza(fen: str, mosse: str) -> Sequenza:
    """"e4, e5, Cf3" -> le tre mosse giocate in ordine. Si accettano virgole, punti e virgola o a capo, e la numerazione ("1.e4, e5, 2.Cf3").
    Ogni mossa è controllata sulla posizione lasciata dalla precedente; alla prima non legale ci si ferma e si dice perché."""
    parti = [re.sub(r"^\d+\.+\s*", "", p.strip()) for p in re.split(r"[,;\n]+", mosse or "")]
    parti = [p for p in parti if p]
    esiti: list[EsitoMossa] = []
    corrente = fen
    for parte in parti:
        esito = controlla_mossa(corrente, parte)
        esiti.append(esito)
        if not esito.legale:
            break
        corrente = esito.fen_dopo
    return Sequenza(parti, esiti)

def verifica_mossa(fen: str, mossa: str) -> str:
    """Come `controlla_mossa`, ma restituisce solo il testo (per l'MCP e per l'agente: un errore diventa un messaggio, non un'eccezione)."""
    return controlla_mossa(fen, mossa).messaggio


# ---------- altri strumenti ----------
def _fine_partita(b: chess.Board) -> str:
    if b.is_checkmate():
        return f"scacco matto, ha vinto il {'Nero' if b.turn == chess.WHITE else 'Bianco'}"
    if b.is_stalemate():
        return "stallo (patta)"
    if b.is_insufficient_material():
        return "materiale insufficiente (patta)"
    return "partita conclusa"


def mosse_legali(fen: str) -> str:
    """Elenca le mosse legali in notazione italiana."""
    try:
        b = scacchiera(fen)
    except ValueError as errore:
        return str(errore)
    mosse = sorted(san_in_italiano(b.san(m)) for m in b.legal_moves)
    if not mosse:
        return f"Nessuna mossa legale: {_fine_partita(b)}."
    return f"Tocca al {_colore(b)}. {len(mosse)} mosse legali: " + ", ".join(mosse)


def descrivi_posizione(fen: str) -> str:
    """Chi muove, materiale, scacco/matto/stallo e quante mosse ci sono."""
    try:
        b = scacchiera(fen)
    except ValueError as errore:
        return str(errore)
    materiale = {c: sum(_VALORI[p.piece_type] for p in b.piece_map().values() if p.color == c and p.piece_type in _VALORI)
                 for c in (chess.WHITE, chess.BLACK)}
    differenza = materiale[chess.WHITE] - materiale[chess.BLACK]
    punti = f"{abs(differenza)} " + ("punto" if abs(differenza) == 1 else "punti")
    saldo = "parità di materiale" if differenza == 0 else f"{'Bianco' if differenza > 0 else 'Nero'} in vantaggio di {punti}"
    if b.is_game_over():
        stato = _fine_partita(b)
    else:
        stato = ("il re del " + _colore(b) + " è sotto scacco") if b.is_check() else "nessuno scacco"
    return (f"Tocca al {_colore(b)}. Materiale: Bianco {materiale[chess.WHITE]}, Nero {materiale[chess.BLACK]} ({saldo}). "
            f"{stato[0].upper() + stato[1:]}. Mosse legali: {b.legal_moves.count()}.")


def disegna(b: chess.Board, da_a: tuple[int, int] | None = None, dimensione: int = 380) -> str:
    """La scacchiera come immagine SVG (testo), con una freccia sull'ultima mossa se indicata."""
    frecce = [chess.svg.Arrow(da_a[0], da_a[1], color="#4F7A39cc")] if da_a else []
    return chess.svg.board(b, size=dimensione, arrows=frecce)


# ---------- posizioni di esempio (generate dal codice: niente FEN scritte a mano che potrebbero essere sbagliate) ----------
def _dopo(*mosse: str) -> str:
    b = chess.Board()
    for m in mosse:
        b.push_san(m)
    return b.fen()


ESEMPI: dict[str, str] = {
    "Posizione iniziale": START,
    "Dopo 1.e4 e5 2.Cf3 Cc6": _dopo("e4", "e5", "Nf3", "Nc6"),
    "Matto del barbiere: tocca al Bianco (prova Dxf7)": _dopo("e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"),
    "Spagnola: tocca al Bianco (prova Axc6)": _dopo("e4", "e5", "Nf3", "Nc6", "Bb5", "a6"),
    "En passant: tocca al Bianco (prova exd6)": _dopo("e4", "a6", "e5", "d5"),
    "Promozione: il pedone è in a7 (prova a8=D)": "8/P7/8/8/8/8/k6K/8 w - - 0 1",
    "Stallo: tocca al Nero": "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
}




