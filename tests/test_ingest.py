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


def _pezzo(vs, file, sezione):
    trovati = [c for c in ingest.chunk_del_ramo(vs, "rules")
               if c.metadata["source_file"] == file and c.metadata.get("sezione") == sezione]
    assert len(trovati) == 1, f"atteso 1 pezzo per {file} › {sezione}, trovati {len(trovati)}"
    return trovati[0]


def test_ogni_sezione_e_un_pezzo_separato(indice):
    """Regressione: prima un pezzo partiva a metà ("Ogni alfiere resta…") e mescolava alfiere, cavallo e pedone."""
    vs, _ = indice
    cavallo = _pezzo(vs, "01_pezzi_e_movimenti.md", "Il cavallo")
    assert '"a L"' in cavallo.text
    assert "alfiere si muove" not in cavallo.text and "pedone avanza" not in cavallo.text


def test_ogni_pezzo_inizia_con_titolo_e_sezione(indice):
    """Il pezzo "sa" di cosa parla: [titolo del documento — sezione] davanti al testo (contextual retrieval, S08)."""
    vs, _ = indice
    for c in ingest.chunk_del_ramo(vs, "rules"):
        assert c.text.startswith("[") and " — " in c.text.split("\n")[0], c.text[:70]
        assert c.metadata["sezione"], f"sezione non riconosciuta in {c.metadata['source_file']}: {c.text[:70]}"
    assert _pezzo(vs, "01_pezzi_e_movimenti.md", "Il cavallo").text.startswith("[Come si muovono i pezzi — Il cavallo]\n")


def test_il_testo_prima_del_primo_titolo_si_chiama_introduzione(indice):
    vs, _ = indice
    assert "64 case" in _pezzo(vs, "01_pezzi_e_movimenti.md", "Introduzione").text


def test_l_etichetta_serve_a_citare_la_fonte(indice):
    vs, _ = indice
    assert ingest.etichetta(_pezzo(vs, "01_pezzi_e_movimenti.md", "Il cavallo")) == "01_pezzi_e_movimenti.md › Il cavallo"


def test_l_anteprima_mostra_il_testo_senza_l_intestazione(indice):
    vs, _ = indice
    anteprima = ingest.anteprima(_pezzo(vs, "01_pezzi_e_movimenti.md", "Il cavallo"), 60)
    assert anteprima.startswith("Il cavallo si muove") and not anteprima.startswith("[")


def test_statistiche_dei_chunk(indice):
    vs, _ = indice
    s = ingest.statistiche(vs, "rules")
    assert s["chunk"] > 0 and 0 < s["media"] <= s["max"]
