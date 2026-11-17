"""Step 1c: il router. Offline, con un finto LLM."""
import pytest
from fakes import ScriptedClient

from chess_tutor import config
from chess_tutor.router import RouteOut, instrada, prompt_router


def client(branches, off_topic=False, confidence=0.9):
    return ScriptedClient(route=RouteOut(about_chess=not off_topic, branches=branches, confidence=confidence))


def test_il_prompt_elenca_i_rami_e_non_scarta_la_storia_degli_scacchi():
    """Regressione: il router scartava come "fuori tema" quasi tutte le domande di storia degli scacchi (3/18 passavano).
    Misurato: la domanda in POSITIVO + gli esempi le fa passare 18/18; nessuna delle due idee da sola bastava."""
    p = prompt_router()
    for ramo in config.BRANCHES.values():
        assert f"- {ramo.key}: {ramo.description}" in p
    assert "decidi se la domanda riguarda gli scacchi" in p                      # domanda in positivo
    assert "Garry Kasparov" in p and "about_chess=false" in p                    # esempi dei due casi
    assert "storia degli scacchi" in RouteOut.model_fields["about_chess"].description.lower()


def test_lo_schema_inviato_al_modello_ha_solo_campi_obbligatori():
    campi = RouteOut.model_fields
    assert set(campi) == {"about_chess", "branches", "confidence"} and all(f.is_required() for f in campi.values())


def test_sceglie_il_ramo():
    d = instrada("Cos'è la siciliana?", client(["openings"]))
    assert d.rami == ["openings"] and not d.fuori_tema and not d.ripiego
    assert d.token_prompt == 50 and d.token_completati == 10          # i token del router contano nel costo


def test_fuori_tema_nessun_ramo():
    d = instrada("Che ricetta per la carbonara?", client([], off_topic=True))
    assert d.fuori_tema and d.rami == []


def test_via_i_rami_inventati_e_i_doppioni_e_al_massimo_due():
    assert instrada("x", client(["openings", "poker", "openings"])).rami == ["openings"]
    assert instrada("x", client(["rules", "openings", "rules"])).rami == ["rules", "openings"]


def test_la_confidenza_resta_tra_0_e_1():
    assert instrada("x", client(["rules"], confidence=7.0)).confidenza == 1.0
    assert instrada("x", client(["rules"], confidence=-3.0)).confidenza == 0.0


def test_scelta_non_valida_ripiega_su_tutti_i_rami():
    """Il router dice "non è fuori tema" ma indica solo rami che non esistono: non si blocca l'utente."""
    d = instrada("x", client(["poker"]))
    assert d.ripiego and d.rami == list(config.BRANCHES)


def test_se_il_servizio_fallisce_ripiega_su_tutti_i_rami():
    class Rotto(ScriptedClient):
        def _structured_response(self, *a, **k):
            raise RuntimeError("servizio non raggiungibile")

    d = instrada("Come si muove la torre?", Rotto())
    assert d.ripiego and d.rami == list(config.BRANCHES) and not d.fuori_tema
