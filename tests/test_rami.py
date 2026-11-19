"""Rami della conoscenza: ogni ramo ha i suoi documenti e la sua collection, e i rami non si mescolano."""
import pytest
from fakes import HashEmbedder

from chess_tutor import config, ingest, retrieval

FILE_APERTURE = {"01_principi_di_apertura.md", "02_aperture_di_pedone_di_re.md",
                 "03_aperture_di_pedone_di_donna.md", "04_trappole_e_matti_rapidi.md"}


@pytest.fixture(scope="module")
def ricerche():
    vs, emb = ingest.crea_vector_store(), HashEmbedder()
    for ramo in ("rules", "openings", "tactics"):
        ingest.indicizza_ramo(vs, emb, ramo, verbose=False)
    return {ramo: retrieval.Ricerca(vs, emb, ramo) for ramo in ("rules", "openings", "tactics")}


def test_i_rami_configurati():
    assert set(config.BRANCHES) == {"rules", "openings", "tactics"}


def test_il_ramo_tattiche_trova_la_forchetta_e_la_scoperta(ricerche):
    """La dispensa sulle tattiche è nel corpus: la forchetta si trova nel ramo tattiche e non in quelli delle regole o delle aperture."""
    primi = {(c.metadata["source_file"], c.metadata["sezione"]) for c in ricerche["tactics"].cerca("forchetta", k=3, modo="bm25")}
    assert ("01_forchetta_inchiodatura_infilata.md", "La forchetta") in primi
    assert ricerche["tactics"].cerca("scacco di scoperta", k=1, modo="bm25")[0].metadata["source_file"] == "02_scoperta_e_pezzi_indifesi.md"
    assert {c.metadata["ramo"] for c in ricerche["tactics"].cerca("forchetta", k=3, modo="dense")} == {"tactics"}
    assert not ricerche["rules"].cerca("forchetta", k=3, modo="bm25") and not ricerche["openings"].cerca("forchetta", k=3, modo="bm25")


def test_il_ramo_aperture_trova_la_difesa_siciliana(ricerche):
    top = ricerche["openings"].cerca("difesa siciliana", k=1, modo="bm25")[0]
    assert top.metadata["source_file"] == "02_aperture_di_pedone_di_re.md"
    assert top.metadata["sezione"] == "Difesa Siciliana"


def test_i_rami_non_si_mescolano(ricerche):
    """Cercare "siciliana" nel ramo regole non deve restituire documenti delle aperture (e viceversa)."""
    for modo in retrieval.MODI:     # "<=": la ricerca per parole può non trovare nulla, ma mai nulla di un altro ramo
        assert {c.metadata["ramo"] for c in ricerche["rules"].cerca("difesa siciliana", k=3, modo=modo)} <= {"rules"}
        assert {c.metadata["ramo"] for c in ricerche["openings"].cerca("arrocco", k=3, modo=modo)} <= {"openings"}
    assert {c.metadata["ramo"] for c in ricerche["rules"].cerca("difesa siciliana", k=3, modo="dense")} == {"rules"}


def test_i_documenti_delle_aperture_sono_quelli_attesi():
    assert {f.name for f in ingest.documenti_del_ramo("openings")} == FILE_APERTURE


def test_i_due_errori_corretti_nei_documenti_delle_aperture():
    """Controllati a mano: c1 è una casa scura (alfiere di Londra); nel matto del barbiere la donna è protetta dall'alfiere."""
    londra = (config.DATA_DIR / "openings" / "03_aperture_di_pedone_di_donna.md").read_text(encoding="utf-8")
    barbiere = (config.DATA_DIR / "openings" / "04_trappole_e_matti_rapidi.md").read_text(encoding="utf-8")
    assert "casa scura" in londra and "casa chiara" not in londra
    assert "la donna è protetta dall'alfiere in c4" in barbiere
