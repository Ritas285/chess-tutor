"""Step 1b: ricerca per significato, per parole e ibrida. Offline, con un embedder finto."""
import pytest
from fakes import HashEmbedder

from chess_tutor import config, ingest, retrieval


@pytest.fixture(scope="module")
def ricerca():
    vs, emb = ingest.crea_vector_store(), HashEmbedder()
    ingest.indicizza_ramo(vs, emb, "rules", verbose=False)
    return retrieval.Ricerca(vs, emb, "rules")


def fonti(chunks):
    return [c.metadata["source_file"] for c in chunks]


# ---------- RRF: la formula del corso, con numeri facili ----------
def test_rrf_chi_sta_in_alto_in_entrambe_vince():
    assert retrieval.rrf([[1, 2, 3], [1, 3, 2]])[0] == 1


def test_rrf_chi_compare_in_due_classifiche_batte_chi_compare_in_una():
    # 9 è primo in una sola classifica; 5 è secondo in entrambe: 2 * 1/(60+1) > 1/(60+0)
    assert retrieval.rrf([[9, 5], [7, 5]])[0] == 5


def test_rrf_con_una_classifica_vuota_tiene_l_altra():
    assert retrieval.rrf([[4, 2], []]) == [4, 2]


# ---------- tokenizzatore ----------
def test_il_tokenizzatore_tiene_insieme_i_simboli_della_notazione():
    assert "o-o-o" in retrieval.tokenizza("Cosa vuol dire O-O-O?")
    assert "e8=d" in retrieval.tokenizza("la promozione (e8=D) è")
    assert "#" in retrieval.tokenizza("# indica scacco matto")


def test_il_tokenizzatore_toglie_accenti_e_punteggiatura_finale():
    assert retrieval.tokenizza("Perché l'arrocco.") == ["perche", "l", "arrocco"]


def test_il_tokenizzatore_del_corso_lascia_il_punto_attaccato_alle_parole():
    """Difetto misurato sul nostro corpus: 48 token su 1028 (4,7%) avevano il punto attaccato ("pedone." != "pedone")."""
    assert retrieval.tokenizza_corso("il pedone. Poi") == ["il", "pedone.", "poi"]
    assert retrieval.tokenizza("il pedone. Poi") == ["il", "pedone", "poi"]


def test_il_tokenizzatore_adattato_trova_piu_chunk_di_quello_del_corso(ricerca):
    """Per la parola "pedone" il tokenizzatore del corso trovava 5 chunk, quello adattato 7."""
    def n_chunk(tok):
        return sum("pedone" in set(tok(c.text)) for c in ricerca.chunks)
    assert n_chunk(retrieval.tokenizza) > n_chunk(retrieval.tokenizza_corso)


# ---------- BM25 e ibrido ----------
def test_bm25_trova_la_parola_esatta(ricerca):
    assert fonti(ricerca.cerca("Tad1", k=1, modo="bm25")) == ["04_valore_pezzi_e_notazione.md"]


def test_bm25_senza_parole_in_comune_non_restituisce_nulla(ricerca):
    assert ricerca.cerca("zzzqqq", k=3, modo="bm25") == []


def test_ibrido_trova_la_parola_esatta(ricerca):
    assert "04_valore_pezzi_e_notazione.md" in fonti(ricerca.cerca("Tad1", k=3, modo="ibrido"))


def test_tutti_i_modi_restituiscono_chunk_con_la_fonte(ricerca):
    for modo in retrieval.MODI:
        for c in ricerca.cerca("arrocco corto", k=3, modo=modo):
            assert c.metadata["source_file"].endswith(".md") and c.metadata["ramo"] == "rules"


def test_modo_sconosciuto(ricerca):
    with pytest.raises(ValueError):
        ricerca.cerca("arrocco", modo="magia")


@pytest.mark.skipif(not config.OPENAI_API_KEY, reason="serve OPENAI_API_KEY (costo: frazioni di centesimo)")
def test_con_embedding_veri_l_ibrido_trova_o_o_o():
    emb, vs = ingest.crea_embedder(), ingest.crea_vector_store()
    ingest.indicizza_ramo(vs, emb, "rules", verbose=False)
    top3 = fonti(retrieval.Ricerca(vs, emb, "rules").cerca("Cosa vuol dire O-O-O?", k=3, modo="ibrido"))
    assert "03_mosse_speciali.md" in top3 or "04_valore_pezzi_e_notazione.md" in top3
