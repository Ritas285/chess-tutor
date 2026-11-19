"""Il gold dei sinonimi (evals/gold_sinonimi.json) è ben formato: serve a misurare il giudice, quindi non deve avere buchi."""
import json
from pathlib import Path

CASI = json.loads((Path(__file__).parent.parent / "evals" / "gold_sinonimi.json").read_text(encoding="utf-8"))["casi"]


def test_gold_sinonimi_equilibrato_e_completo():
    assert len({c["id"] for c in CASI}) == len(CASI)
    gruppi = {g: [c for c in CASI if c["gruppo"] == g] for g in ("sinonimo", "trabocchetto")}
    assert len(gruppi["sinonimo"]) == len(gruppi["trabocchetto"]) == 8
    assert all(c["atteso"] == "corretta" for c in gruppi["sinonimo"])
    assert all(c["atteso"] == "errata" for c in gruppi["trabocchetto"])
    for c in CASI:
        assert c["domanda"].strip() and c["risposta"].strip() and "Dal documento" in c["riferimento"]


def test_ogni_sinonimo_ha_il_suo_trabocchetto_sulla_stessa_domanda():
    """Un sinonimo accettato è credibile solo se la stessa domanda ha anche una risposta simile ma sbagliata da respingere."""
    sin = {c["domanda"] for c in CASI if c["gruppo"] == "sinonimo"}
    tra = {c["domanda"] for c in CASI if c["gruppo"] == "trabocchetto"}
    assert sin == tra
