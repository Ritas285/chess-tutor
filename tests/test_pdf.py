"""Rami con documenti PDF (Step 6): lettura pulita, pezzi per pagina, rami opzionali, misure indipendenti dal formato.
Nessun PDF vero: i test costruiscono PDF minuscoli (tests/pdf_di_prova.py). I PDF veri non stanno nel git (diritti)."""
import json
from pathlib import Path

import pytest
from fakes import HashEmbedder
from pdf_di_prova import crea_pdf

from chess_tutor import config, formati, ingest, pdf, retrieval

PAGINA_1 = ["Il cavallo si muove a forma di L. Salta sopra gli altri pezzi senza problemi.",
            "L'alfiere si muove in diagonale e resta sempre sullo stesso colore della scacchiera."]
PAGINA_2 = ["La torre si muove in linea retta, in orizzontale o in verticale, per quante case vuole."]


@pytest.fixture
def pdf_semplice(tmp_path):
    return crea_pdf(tmp_path / "Mio_manuale_di_prova.pdf", [PAGINA_1, PAGINA_2, ["x"]])


# ---------- pulizia ----------
def test_la_pulizia_toglie_testate_numeri_di_pagina_e_diagrammi_e_riunisce_le_righe():
    grezzo = "\n".join([
        "Manualetto di scacchi", "31", r"E:\documenti\Scacchi\Corso Polcenigo.doc  12 ",
        "Federazione Scacchistica Italiana – Regole di base – Pag. 3/10",
        "XABCDEFGHY", "8rsnlwqk+-tr(", "4-+R+-+-+$", "xabcdefghy",
        "Nel frat-", "tempo il pedone avanza", "di due case."])
    assert pdf.pulisci_pagina(grezzo) == "Nel frattempo il pedone avanza di due case."


def test_una_riga_normale_con_numeri_non_viene_scambiata_per_un_diagramma():
    assert pdf.pulisci_pagina("1.e4 e5 2.Cf3 Cc6") == "1.e4 e5 2.Cf3 Cc6"


def test_i_pezzi_rispettano_il_massimo_e_finiscono_a_fine_frase():
    frase = "Il pedone avanza di una casa alla volta e cattura in diagonale."
    testo = " ".join([frase] * 8)
    pezzi = pdf.spezza(testo, massimo=200)
    assert len(pezzi) > 1 and all(len(p) <= 200 for p in pezzi)
    assert all(p.endswith(".") for p in pezzi)
    assert " ".join(pezzi) == testo                                    # nessuna parola persa


def test_una_frase_piu_lunga_del_massimo_viene_tagliata_sugli_spazi():
    testo = " ".join(["parola"] * 60)
    pezzi = pdf.spezza(testo, massimo=100)
    assert all(len(p) <= 100 for p in pezzi) and " ".join(pezzi) == testo


# ---------- lettura ----------
def test_pezzi_per_pagina_con_il_numero_di_pagina_e_senza_le_pagine_vuote(pdf_semplice):
    pezzi = pdf.pezzi_del_pdf(pdf_semplice)
    assert [n for n, _ in pezzi] == [1, 2]                              # la pagina 3 ("x") ha meno di 40 caratteri: niente pezzo
    assert "cavallo" in pezzi[0][1] and "alfiere" in pezzi[0][1] and "torre" in pezzi[1][1]


def test_il_pezzo_del_pdf_porta_con_se_titolo_e_pagina(pdf_semplice):
    chunks = pdf.LeggiPdf()._run(str(pdf_semplice))
    assert chunks[0].text.startswith("[Mio manuale di prova — p. 1]\n")
    assert chunks[1].metadata == {"titolo": "Mio manuale di prova", "sezione": "p. 2", "pagina": 2}


def test_il_titolo_viene_dal_nome_del_file():
    assert pdf.titolo_da_nome(Path("FSI_regole_di_base.pdf")) == "FSI regole di base"


# ---------- indicizzazione e ricerca ----------
def test_un_ramo_con_un_pdf_si_indicizza_e_si_cita_con_la_pagina(tmp_path, pdf_semplice):
    ramo = tmp_path / "manuale"
    ramo.mkdir()
    (ramo / pdf_semplice.name).write_bytes(pdf_semplice.read_bytes())
    assert [f.name for f in ingest.documenti_del_ramo("manuale", tmp_path)] == [pdf_semplice.name]
    vs, emb = ingest.crea_vector_store(), HashEmbedder()
    assert ingest.indicizza_ramo(vs, emb, "manuale", data_dir=tmp_path, verbose=False) == 1
    ricerca = retrieval.Ricerca(vs, emb, "manuale")
    top = ricerca.cerca("come si muove la torre", k=1, modo="bm25")[0]
    assert ingest.etichetta(top) == "Mio_manuale_di_prova.pdf › p. 2"
    assert top.metadata["ramo"] == "manuale"


def test_un_ramo_puo_mescolare_md_e_pdf(tmp_path, pdf_semplice):
    ramo = tmp_path / "misto"
    ramo.mkdir()
    (ramo / pdf_semplice.name).write_bytes(pdf_semplice.read_bytes())
    (ramo / "appunti.md").write_text("# Appunti\n\n## La donna\n\nLa donna si muove come torre e alfiere insieme.\n", encoding="utf-8")
    assert [f.name for f in ingest.documenti_del_ramo("misto", tmp_path)] == ["appunti.md", "Mio_manuale_di_prova.pdf"]   # a, M: senza badare alle maiuscole
    vs, emb = ingest.crea_vector_store(), HashEmbedder()
    assert ingest.indicizza_ramo(vs, emb, "misto", data_dir=tmp_path, verbose=False) == 2
    fonti = {c.metadata["source_file"] for c in ingest.chunk_del_ramo(vs, "misto")}
    assert fonti == {"Mio_manuale_di_prova.pdf", "appunti.md"}


# ---------- rami opzionali ----------
def test_i_rami_pdf_esistono_solo_se_abilitati_e_con_dei_pdf(tmp_path):
    base = {"rules": config.BRANCHES["rules"]}
    extra = [config.Branch("manuale", "Manuale", "...")]
    (tmp_path / "manuale").mkdir()
    assert list(config.rami_attivi(base, extra, tmp_path, abilitati=True)) == ["rules"]        # cartella senza PDF
    (tmp_path / "manuale" / "a.pdf").write_bytes(b"x")
    assert list(config.rami_attivi(base, extra, tmp_path, abilitati=True)) == ["rules", "manuale"]
    assert list(config.rami_attivi(base, extra, tmp_path, abilitati=False)) == ["rules"]       # non abilitati


def test_i_test_vedono_sempre_solo_i_rami_md():
    """tests/conftest.py imposta RAMI_PDF=0: anche con i PDF in data/ e RAMI_PDF=1 nel .env i test restano gli stessi."""
    assert set(config.BRANCHES) == {"rules", "openings"}


def test_i_pdf_in_data_non_finiscono_nel_git():
    gitignore = (config.ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/*/*.pdf" in gitignore


# ---------- misure indipendenti dal formato ----------
def test_norma_toglie_accenti_maiuscole_spazi_e_punteggiatura():
    assert formati.norma("Il Re, perché… ‘scacco’!") == "ilreperchescacco"


def test_la_posizione_della_risposta_e_il_primo_pezzo_con_una_delle_frasi():
    pezzi = ["parla d'altro", "qui c'è: il matto  del barbiere.", "anche qui il matto del barbiere"]
    assert formati.posizione_della_risposta(pezzi, ["Il matto del Barbiere"]) == 2
    assert formati.posizione_della_risposta(pezzi, ["niente di simile", "il matto del barbiere"]) == 2
    assert formati.posizione_della_risposta(pezzi, ["frase che non c'è"]) is None


def test_le_metriche_primo_top3_e_mrr():
    m = formati.metriche([1, 3, 4, None])
    assert m == {"n": 4, "primo": 0.25, "top3": 0.5, "mrr": pytest.approx((1 + 1 / 3 + 1 / 4) / 4)}
    assert formati.metriche([])["n"] == 0


def test_un_pdf_semplice_diventa_markdown_con_le_sezioni(tmp_path):
    p = crea_pdf(tmp_path / "Regole_di_prova.pdf", [
        ["REGOLE DI PROVA", " ", "Un testo introduttivo che spiega a cosa servono le regole.", " ",
         "IL MOVIMENTO DEI PEZZI", " ", "Ogni pezzo ha il suo modo di muoversi.", " ", "Alfiere", "L'alfiere si muove in diagonale per quante case vuole.", " ",
         "Torre", "La torre si muove in orizzontale o in verticale per quante case vuole."]])    # " " = riga vuota come nei PDF veri
    md = formati.pdf_a_md(p)
    assert md.startswith("# Regole di prova")
    assert [r for r in md.splitlines() if r.startswith("## ")] == ["## Regole di prova", "## Il movimento dei pezzi", "## Alfiere", "## Torre"]
    assert "L'alfiere si muove in diagonale" in md


# ---------- il gold dei rami PDF ----------
GOLD = json.loads((config.ROOT / "evals" / "gold_pdf.json").read_text(encoding="utf-8"))["domande"]


def test_il_gold_pdf_e_ben_formato():
    assert len({d["id"] for d in GOLD}) == len(GOLD) == 24
    assert {d["ramo"] for d in GOLD} == {"regolamento", "corsi"}
    assert all(d["domanda"].strip() and d["frasi"] and all(f.strip() for f in d["frasi"]) for d in GOLD)


def test_il_gold_pdf_non_copia_le_domande_nei_documenti_o_nei_prompt():
    """Goodhart: le domande del gold non devono comparire nei prompt del tutor (stesso controllo di gold.json)."""
    prompt = (config.ROOT / "chess_tutor" / "tutor.py").read_text(encoding="utf-8") + (config.ROOT / "chess_tutor" / "router.py").read_text(encoding="utf-8")
    assert not [d["id"] for d in GOLD if d["domanda"] in prompt]


@pytest.mark.skipif(not list((config.DATA_DIR / "regolamento").glob("*.pdf")) or not list((config.DATA_DIR / "corsi").glob("*.pdf")),
                    reason="i PDF veri non stanno nel git: il controllo gira solo dove sono stati messi in data/")
def test_ogni_frase_del_gold_si_trova_nei_pdf_veri():
    for ramo in ("regolamento", "corsi"):
        testi = [t for f in ingest.documenti_del_ramo(ramo) for _, t in pdf.pezzi_del_pdf(f)]
        for d in (d for d in GOLD if d["ramo"] == ramo):
            assert formati.posizione_della_risposta(testi, d["frasi"]) is not None, d["id"]
