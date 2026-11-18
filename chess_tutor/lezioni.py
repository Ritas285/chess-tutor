"""Le lezioni della scheda Scacchiera: come funzionano l'arrocco, l'en passant, la promozione, le aperture e i matti rapidi.

Ogni lezione è una sequenza di mosse con un commento per ciascuna; la scheda le fa vedere una alla volta su una scacchiera. Le spiegazioni
riprendono i documenti del tutor (`data/`), che sono scritti per questo progetto; le mosse NON si fidano della memoria di nessuno: i test
le giocano tutte con python-chess e controllano che siano legali e che arrivino dove la lezione dice (per esempio il re in g1 dopo O-O).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Passo:
    mossa: str          # in notazione italiana (C cavallo, A alfiere, T torre, D donna, R re), come nei documenti
    commento: str       # cosa succede con questa mossa


@dataclass(frozen=True)
class Lezione:
    chiave: str
    gruppo: str
    titolo: str
    spiegazione: str
    passi: tuple[Passo, ...]
    fonte: str                  # il documento del tutor da cui riprende la spiegazione
    fen: str = "start"          # la posizione di partenza ("start" = quella iniziale)


MOSSE_SPECIALI, APERTURE_E4, APERTURE_D4, MATTI = "Mosse speciali", "Aperture dopo 1.e4", "Aperture dopo 1.d4", "Matti rapidi"
GRUPPI = (MOSSE_SPECIALI, APERTURE_E4, APERTURE_D4, MATTI)

_SPECIALI = "rules/03_mosse_speciali.md"
_E4 = "openings/02_aperture_di_pedone_di_re.md"
_D4 = "openings/03_aperture_di_pedone_di_donna.md"
_TRAPPOLE = "openings/04_trappole_e_matti_rapidi.md"

LEZIONI: tuple[Lezione, ...] = (
    Lezione(
        "arrocco_corto", MOSSE_SPECIALI, "L'arrocco corto",
        "L'arrocco è l'unica mossa in cui si muovono due pezzi insieme: il re si sposta di due case verso una torre e la torre salta dall'altra "
        "parte del re. Serve a mettere il re al sicuro e a portare la torre in gioco. Si può arroccare solo se il re e la torre non si sono mai "
        "mossi, se tra loro non ci sono altri pezzi, se il re non è sotto scacco e se non attraversa né arriva su una casa attaccata.",
        (Passo("e4", "Il Bianco occupa il centro con un pedone."),
         Passo("e5", "Il Nero risponde allo stesso modo."),
         Passo("Cf3", "Sviluppa il cavallo: libera la casa g1, dove andrà il re."),
         Passo("Cc6", "Anche il Nero sviluppa un cavallo."),
         Passo("Ac4", "L'alfiere esce e libera la casa f1: ora tra il re e la torre di re non ci sono più altri pezzi."),
         Passo("Ac5", "Il Nero sviluppa il suo alfiere."),
         Passo("O-O", "Arrocco corto (O-O): il re va da e1 a g1 e la torre salta da h1 a f1. Il re è al sicuro e la torre è in gioco.")),
        _SPECIALI),
    Lezione(
        "arrocco_lungo", MOSSE_SPECIALI, "L'arrocco lungo",
        "L'arrocco lungo si fa verso la torre di donna e si scrive O-O-O. Ci vogliono più mosse di preparazione, perché tra il re e quella torre "
        "ci sono tre case da liberare: b1, c1 e d1. Le regole sono le stesse dell'arrocco corto.",
        (Passo("d4", "Il Bianco occupa il centro."),
         Passo("d5", "Il Nero risponde allo stesso modo."),
         Passo("Cc3", "Il cavallo di donna esce e libera la casa b1."),
         Passo("Cc6", "Il Nero sviluppa un cavallo."),
         Passo("Af4", "L'alfiere di casa scura esce e libera la casa c1."),
         Passo("Af5", "Il Nero sviluppa un alfiere."),
         Passo("Dd2", "La donna si sposta e libera la casa d1: ora tra il re e la torre di donna non c'è più nessuno."),
         Passo("Dd7", "Il Nero muove la donna."),
         Passo("O-O-O", "Arrocco lungo (O-O-O): il re va da e1 a c1 e la torre salta da a1 a d1.")),
        _SPECIALI),
    Lezione(
        "en_passant", MOSSE_SPECIALI, "La presa en passant",
        "Se un pedone avversario avanza di due case dalla sua casa di partenza e finisce affiancato al tuo pedone, puoi catturarlo come se avesse "
        "avanzato di una sola casa. Il tuo pedone si sposta sulla casa che il pedone avversario ha «saltato». Devi farlo subito, alla mossa "
        "successiva: se aspetti, perdi il diritto. Vale solo per i pedoni.",
        (Passo("e4", "Il pedone bianco avanza di due case."),
         Passo("a6", "Il Nero fa una mossa d'attesa."),
         Passo("e5", "Il pedone bianco arriva sulla quinta traversa."),
         Passo("d5", "Il Nero avanza di due case con il pedone d e si ferma affiancato al pedone bianco in e5."),
         Passo("exd6", "En passant! Il pedone bianco cattura come se il pedone nero avesse avanzato di una sola casa: va in d6, la casa «saltata», "
                       "e il pedone nero in d5 sparisce. Si poteva fare solo subito.")),
        _SPECIALI),
    Lezione(
        "promozione", MOSSE_SPECIALI, "La promozione",
        "Quando un pedone raggiunge l'ultima traversa (l'ottava per il Bianco) deve essere promosso: si trasforma in donna, torre, alfiere o cavallo, "
        "a scelta del giocatore. Non può restare pedone e non può diventare re. Quasi sempre si sceglie la donna.",
        (Passo("d8=D", "Il pedone arriva in d8 e diventa una donna (D): scritto d8=D. Il Bianco ora ha una donna in più."),),
        _SPECIALI, fen="8/3P2k1/8/8/8/8/6K1/8 w - - 0 1"),

    Lezione(
        "italiana", APERTURE_E4, "Partita Italiana",
        "1.e4 e5 2.Cf3 Cc6 3.Ac4. L'alfiere bianco punta al punto debole f7, vicino al re nero. È una delle aperture più adatte ai principianti "
        "perché i piani sono chiari: sviluppare in fretta, controllare il centro con c3 e d4, arroccare.",
        (Passo("e4", "Il Bianco occupa il centro."),
         Passo("e5", "Il Nero risponde allo stesso modo."),
         Passo("Cf3", "Sviluppa il cavallo e attacca il pedone e5."),
         Passo("Cc6", "Il Nero difende il pedone sviluppando un cavallo."),
         Passo("Ac4", "L'alfiere punta al punto debole f7, vicino al re nero."),
         Passo("Ac5", "Giuoco Piano: il Nero sviluppa il suo alfiere sulla diagonale opposta.")),
        _E4),
    Lezione(
        "spagnola", APERTURE_E4, "Partita Spagnola (Ruy Lopez)",
        "1.e4 e5 2.Cf3 Cc6 3.Ab5. L'alfiere attacca il cavallo che difende il pedone e5. La minaccia non è immediata, ma crea pressione a lungo "
        "termine. È una delle aperture più giocate a ogni livello; la teoria è però molto vasta.",
        (Passo("e4", "Il Bianco occupa il centro."),
         Passo("e5", "Il Nero risponde allo stesso modo."),
         Passo("Cf3", "Sviluppa il cavallo e attacca il pedone e5."),
         Passo("Cc6", "Il Nero difende il pedone sviluppando un cavallo."),
         Passo("Ab5", "L'alfiere attacca il cavallo che difende e5: la minaccia non è immediata, ma crea pressione a lungo termine.")),
        _E4),
    Lezione(
        "siciliana", APERTURE_E4, "Difesa Siciliana",
        "1.e4 c5. Il Nero non copia il Bianco ma risponde in modo asimmetrico, combattendo per la casa d4 con il pedone laterale. Dopo 2.Cf3 e "
        "3.d4 il Bianco cambia il suo pedone centrale contro il pedone c. È molto combattiva, ma ha molta teoria per un principiante.",
        (Passo("e4", "Il Bianco occupa il centro."),
         Passo("c5", "Il Nero risponde in modo asimmetrico: il pedone c controlla la casa d4."),
         Passo("Cf3", "Il Bianco sviluppa il cavallo e prepara d4."),
         Passo("d6", "Una mossa solida: difende e5 e apre la strada all'alfiere."),
         Passo("d4", "Il Bianco offre il cambio del suo pedone centrale contro il pedone c."),
         Passo("cxd4", "Il Nero cattura."),
         Passo("Cxd4", "Il cavallo riprende: il Bianco ha un pezzo sviluppato al centro.")),
        _E4),
    Lezione(
        "francese", APERTURE_E4, "Difesa Francese",
        "1.e4 e6 2.d4 d5. Il Nero costruisce una catena di pedoni solida (e6, d5) e poi attacca il centro bianco. È solida, ma l'alfiere nero in "
        "c8 può restare chiuso dietro i propri pedoni: è il problema principale della Francese.",
        (Passo("e4", "Il Bianco occupa il centro."),
         Passo("e6", "Il Nero prepara una catena di pedoni solida."),
         Passo("d4", "Il Bianco occupa anche la casa d4."),
         Passo("d5", "Il Nero attacca il centro bianco. Ma ora l'alfiere in c8 è chiuso dietro i propri pedoni: è il problema della Francese.")),
        _E4),

    Lezione(
        "gambetto_donna", APERTURE_D4, "Gambetto di Donna",
        "1.d4 d5 2.c4. Il Bianco offre il pedone c4. Il nome è fuorviante: non è un vero gambetto, perché se il Nero cattura con 2...dxc4 il Bianco "
        "può riprendere il pedone senza difficoltà. Il Nero può rifiutare con 2...e6, molto solido. L'idea del Bianco è minare il pedone d5.",
        (Passo("d4", "Il Bianco occupa il centro con il pedone di donna."),
         Passo("d5", "Il Nero risponde allo stesso modo."),
         Passo("c4", "Il Bianco offre il pedone c4: non è un vero gambetto, perché dopo dxc4 lo può riprendere."),
         Passo("e6", "Gambetto di Donna Rifiutato: il Nero non prende il pedone e difende d5. È una scelta molto solida.")),
        _D4),
    Lezione(
        "londra", APERTURE_D4, "Sistema di Londra",
        "1.d4 seguito da Cf3, Af4, e3, c3 e Cbd2. Il Bianco gioca quasi sempre le stesse mosse, in una struttura solida, con l'alfiere di casa "
        "scura (quello di c1) sviluppato in f4, fuori dalla catena di pedoni. Richiede poca teoria e dà piani chiari.",
        (Passo("d4", "Il Bianco occupa il centro."),
         Passo("d5", "Il Nero risponde allo stesso modo."),
         Passo("Cf3", "Sviluppa il cavallo di re."),
         Passo("Cf6", "Il Nero sviluppa un cavallo."),
         Passo("Af4", "L'alfiere di casa scura esce in f4, fuori dalla catena di pedoni: è la mossa che dà il nome al sistema."),
         Passo("e6", "Il Nero prepara lo sviluppo dell'alfiere."),
         Passo("e3", "Il Bianco costruisce una struttura solida."),
         Passo("Ae7", "Il Nero sviluppa l'alfiere e si prepara ad arroccare."),
         Passo("c3", "Un altro pedone di sostegno: il Bianco gioca quasi sempre le stesse mosse."),
         Passo("O-O", "Il Nero arrocca."),
         Passo("Cbd2", "Con il cavallo di donna in d2 lo sviluppo è completo.")),
        _D4),
    Lezione(
        "indiana_re", APERTURE_D4, "Difesa Indiana di Re",
        "Dopo 1.d4 Cf6 2.c4 g6 il Nero lascia il centro al Bianco per attaccarlo dopo, sviluppando l'alfiere in g7. È un'apertura dinamica e "
        "rischiosa, più adatta a chi conosce già bene i principi dell'apertura.",
        (Passo("d4", "Il Bianco occupa il centro."),
         Passo("Cf6", "Il Nero sviluppa un cavallo e controlla la casa e4."),
         Passo("c4", "Il Bianco prende ancora più spazio al centro."),
         Passo("g6", "Il Nero prepara lo sviluppo dell'alfiere sulla lunga diagonale."),
         Passo("Cc3", "Il Bianco sviluppa un cavallo."),
         Passo("Ag7", "L'alfiere in g7 è il cuore della Indiana di Re: il Nero lascia il centro al Bianco per attaccarlo dopo."),
         Passo("e4", "Il Bianco occupa il centro con una struttura di pedoni."),
         Passo("d6", "Il Nero si prepara ad attaccare il centro bianco.")),
        _D4),

    Lezione(
        "matto_barbiere", MATTI, "Matto del barbiere",
        "1.e4 e5 2.Ac4 Cc6 3.Dh5 Cf6?? 4.Dxf7#. Il Bianco attacca il punto debole f7 con donna e alfiere. Se il Nero non se ne accorge, la donna "
        "prende in f7 con scacco matto, perché è protetta dall'alfiere in c4. Lezione: controlla sempre il punto f7 (o f2 per il Bianco).",
        (Passo("e4", "Il Bianco occupa il centro."),
         Passo("e5", "Il Nero risponde allo stesso modo."),
         Passo("Ac4", "L'alfiere punta al punto debole f7."),
         Passo("Cc6", "Il Nero sviluppa un cavallo."),
         Passo("Dh5", "La donna si affianca all'alfiere: due pezzi attaccano f7."),
         Passo("Cf6", "Errore! Il Nero non si accorge della minaccia. Si difendeva con 3...g6 o 3...Df6."),
         Passo("Dxf7", "Scacco matto! La donna prende in f7 ed è protetta dall'alfiere in c4: il re nero non ha scampo.")),
        _TRAPPOLE),
    Lezione(
        "matto_pazzo", MATTI, "Matto del pazzo",
        "1.f3 e5 2.g4 Dh4#. Il Bianco apre la diagonale al proprio re con mosse di pedone inutili e il Nero dà matto in due mosse: è il matto più "
        "rapido possibile. Lezione: non indebolire il re con mosse di pedone inutili.",
        (Passo("f3", "Una mossa di pedone inutile, che indebolisce il re."),
         Passo("e5", "Il Nero occupa il centro."),
         Passo("g4", "Un'altra mossa inutile: apre la diagonale che porta al re bianco."),
         Passo("Dh4", "Scacco matto in due mosse! La donna dà scacco dalla diagonale aperta e il re bianco non ha case libere.")),
        _TRAPPOLE),
)


def del_gruppo(gruppo: str) -> tuple[Lezione, ...]:
    return tuple(lez for lez in LEZIONI if lez.gruppo == gruppo)


def cerca(chiave: str) -> Lezione:
    for lez in LEZIONI:
        if lez.chiave == chiave:
            return lez
    raise KeyError(f"lezione sconosciuta: {chiave}")


def mosse_della_lezione(lez: Lezione) -> str:
    """Le mosse della lezione come testo "e4, e5, Cf3" (per `chess_tools.gioca_sequenza`)."""
    return ", ".join(p.mossa for p in lez.passi)
