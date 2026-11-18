"""Step 1h: il tema dei colori (.streamlit/config.toml). Si controlla che i nomi siano validi e che il testo sia leggibile (WCAG)."""
import tomllib
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"
TEMA = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["theme"]
CHIAVI_VALIDE = {"primaryColor", "backgroundColor", "secondaryBackgroundColor", "textColor", "linkColor", "borderColor"}


def luminanza(esadecimale: str) -> float:
    """Luminanza relativa di un colore #RRGGBB (formula WCAG)."""
    canali = [int(esadecimale[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def contrasto(a: str, b: str) -> float:
    la, lb = sorted((luminanza(a), luminanza(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("modo", ["light", "dark"])
def test_i_colori_hanno_nomi_validi_e_formato_corretto(modo):
    colori = TEMA[modo]
    assert set(colori) == CHIAVI_VALIDE
    assert all(len(v) == 7 and v.startswith("#") for v in colori.values())


@pytest.mark.parametrize("modo", ["light", "dark"])
def test_il_testo_e_leggibile_su_sfondo_e_su_pannelli(modo):
    c = TEMA[modo]
    assert contrasto(c["textColor"], c["backgroundColor"]) >= 7          # livello AAA per il testo normale
    assert contrasto(c["textColor"], c["secondaryBackgroundColor"]) >= 7
    assert contrasto(c["linkColor"], c["backgroundColor"]) >= 4.5       # AA
    assert contrasto(c["primaryColor"], c["backgroundColor"]) >= 3      # elementi di interfaccia


def test_il_pulsante_principale_chiaro_ha_testo_bianco_leggibile():
    assert contrasto("#FFFFFF", TEMA["light"]["primaryColor"]) >= 4.5


def test_le_statistiche_d_uso_sono_spente():
    assert tomllib.loads(CONFIG.read_text(encoding="utf-8"))["browser"]["gatherUsageStats"] is False
