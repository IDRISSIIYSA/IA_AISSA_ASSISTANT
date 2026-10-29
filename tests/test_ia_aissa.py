import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import connaissances as K  # noqa: E402
from ia_aissa.ecole import MATIERES, PAR_CLE, charger, examen, precision, repondre  # noqa: E402
from ia_aissa.voix import bouton_ecouter, js  # noqa: E402


@pytest.mark.parametrize("revenu,ir", [(40_000, 0), (60_000, 2_000), (80_000, 6_000), (100_000, 12_000),
                                       (180_000, 39_200), (200_000, 46_600)])
def test_bareme_ir_continu(revenu, ir):
    assert K.calculer_ir(revenu)["ir_annuel"] == ir


def test_is_et_tva():
    assert K.calculer_is(1_000_000)["is"] == 200_000
    assert K.calculer_is(200_000_000)["taux"] == 0.35
    assert K.calculer_is(-5)["is"] == 0
    assert K.calculer_tva(120, 0.2, montant_est_ttc=True) == {"ht": 100.0, "taux": 0.2, "tva": 20.0, "ttc": 120.0}


def test_paie_plafond_cnss():
    p = K.calculer_paie(10_000)
    assert p["cnss_salarie"] == round(6_000 * 0.0448, 2) and p["amo_salarie"] == 226.0
    assert p["salaire_net"] < 10_000


def test_chaque_matiere_genere_des_exercices_valides():
    rng = np.random.default_rng(0)
    for m in MATIERES:
        x, y, enonce = m.generer(rng)
        assert x.shape == (m.dim,) and 0 <= y < len(m.actions) and enonce


@pytest.mark.parametrize("cle", [m.cle for m in MATIERES])
def test_cerveaux_fournis_reussissent_leur_examen(cle):
    cerveau, _ = charger(cle)
    assert cerveau is not None, f"cerveau manquant : python -m ia_aissa.entrainer {cle}"
    assert precision(cerveau, examen(PAR_CLE[cle])) >= 0.9


def test_reconnaissance_des_langues():
    assert repondre("langues", "wach kayn chi mochkil")[0]["reponse"] == "Darija"
    assert repondre("langues", "where is the invoice")[0]["reponse"] == "English"


def test_texte_ia_echappe_dans_le_html():
    h = bouton_ecouter("l'année </script><img src=x onerror=alert(1)>", "fr-FR")
    assert "</script><img" not in h and js("<") == '"\\u003c"'
