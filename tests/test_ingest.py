"""Step 1a: corpus e ingestione. Tutto offline, con un embedder finto."""
import pytest
from fakes import HashEmbedder

from chess_tutor import config, ingest


@pytest.fixture
def indice():
    vs = ingest.crea_vector_store()
    n = ingest.indicizza_ramo(vs, HashEmbedder(), "rules", verbose=False)
    return vs, n


def test_ogni_ramo_ha_una_cartella_con_documenti():
    for ramo in config.BRANCHES:
        assert ingest.documenti_del_ramo(ramo), f"nessun documento .md in data/{ramo}/"


def test_documenti_ben_formati():
    """Titolo (#) e almeno una sezione (##): è la struttura che il parser Markdown sfrutta."""
    for ramo in config.BRANCHES:
        for f in ingest.documenti_del_ramo(ramo):
            testo = f.read_text(encoding="utf-8")
            assert testo.startswith("# "), f"{f.name}: manca il titolo"
            assert "\n## " in testo, f"{f.name}: manca almeno una sezione"


def test_ingestione_crea_chunk_con_la_fonte(indice):
    vs, n_documenti = indice
    chunk = ingest.chunk_del_ramo(vs, "rules")
    assert n_documenti == 4 and len(chunk) >= n_documenti
    nomi = {f.name for f in ingest.documenti_del_ramo("rules")}
    for c in chunk:
        assert c.metadata["source_file"] in nomi          # senza questo non si potrebbero citare le fonti
        assert c.metadata["ramo"] == "rules"


def test_reindicizzare_non_duplica_i_chunk():
    vs, emb = ingest.crea_vector_store(), HashEmbedder()
    ingest.indicizza_ramo(vs, emb, "rules", verbose=False)
    primo = len(ingest.chunk_del_ramo(vs, "rules"))
    ingest.indicizza_ramo(vs, emb, "rules", verbose=False)
    assert len(ingest.chunk_del_ramo(vs, "rules")) == primo


def test_la_ricerca_restituisce_k_chunk_con_la_fonte(indice):
    """Con l'embedder finto si controlla il COLLEGAMENTO (non la pertinenza: l'hash non capisce il significato)."""
    vs, _ = indice
    top = ingest.cerca(vs, HashEmbedder(), "rules", "arrocco corto e lungo", k=3)
    assert len(top) == 3 and all(h.metadata["source_file"].endswith(".md") for h in top)


@pytest.mark.skipif(not config.OPENAI_API_KEY, reason="serve OPENAI_API_KEY (costo: frazioni di centesimo)")
def test_con_embedding_veri_la_ricerca_trova_il_documento_giusto():
    emb, vs = ingest.crea_embedder(), ingest.crea_vector_store()
    ingest.indicizza_ramo(vs, emb, "rules", verbose=False)
    fonti = [h.metadata["source_file"] for h in ingest.cerca(vs, emb, "rules", "Come funziona l'arrocco?", k=3)]
    assert "03_mosse_speciali.md" in fonti


def test_statistiche_dei_chunk(indice):
    vs, _ = indice
    s = ingest.statistiche(vs, "rules")
    assert s["chunk"] > 0 and 0 < s["media"] <= s["max"]
