import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import corrections as C  # noqa: E402
from ia_aissa import ecole  # noqa: E402
from ia_aissa.memoire import Memoire  # noqa: E402


@pytest.fixture
def labo(tmp_path, monkeypatch):
    """Cerveaux copiés dans un dossier temporaire : les tests ne modifient jamais ceux du dépôt."""
    dossier = tmp_path / "cerveaux"
    shutil.copytree(ecole.DOSSIER_CERVEAUX, dossier)
    monkeypatch.setattr(ecole, "DOSSIER_CERVEAUX", dossier)
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    C.brancher(mem)
    yield mem, tmp_path
    ecole.STOCKAGE = None
    ecole._CACHE.clear()


def test_validation_des_reponses():
    assert C.valider_reponse("comptabilite", "2355") == "2355 Matériel informatique"
    assert C.valider_reponse("philosophie", "kant") == "Kant"
    assert C.valider_reponse("histoire", "almohades") == "Almohades (1121-1269)"
    assert C.valider_reponse("comptabilite", "n'importe quoi") is None


def test_correction_invalide_refusee(labo):
    mem, _ = labo
    with pytest.raises(ValueError, match="Réponses possibles"):
        C.corriger(mem, "Aissa", "philosophie", "cogito", "Confucius")


def test_correction_enseigne_aussi_l_aiguilleur(labo):
    mem, _ = labo
    C.corriger(mem, "Aissa", "histoire", "qui a construit la koutoubia ?", "almohades")
    assert {(x["matiere"], x["bonne_reponse"]) for x in mem.corrections_de()} == {
        ("histoire", "Almohades (1121-1269)"), ("orientation", "histoire")}


def test_revision_apprend_et_persiste(labo):
    mem, tmp = labo
    question = "paiement de la facture maroc telecom"
    assert ecole.repondre("comptabilite", question)[0]["reponse"] != "6145 Frais postaux et de télécommunications"
    C.corriger(mem, "Aissa", "comptabilite", question, "6145")
    bilan = C.reviser(mem, "comptabilite")
    assert bilan["adoptee"] and bilan["corrections_apres"] == 1.0
    assert bilan["examen_apres"] >= bilan["examen_avant"] - C.TOLERANCE_EXAMEN
    assert mem.corrections_de("comptabilite", seulement_nouvelles=True) == []
    # même sans le fichier local (redémarrage sur Streamlit Cloud), le cerveau révisé revient de la base
    (ecole.DOSSIER_CERVEAUX / "comptabilite.pt").unlink()
    C.brancher(Memoire(f"sqlite:///{tmp / 'm.db'}"))
    assert ecole.repondre("comptabilite", question)[0]["reponse"] == "6145 Frais postaux et de télécommunications"


def test_revision_qui_regresse_est_refusee(labo, monkeypatch):
    mem, _ = labo
    C.corriger(mem, "Aissa", "philosophie", "cogito ergo sum", "Descartes")
    avant = ecole.repondre("philosophie", "impératif catégorique")[0]
    mauvais = ecole.Cerveau(ecole.PAR_CLE["philosophie"].dim, len(ecole.PAR_CLE["philosophie"].actions))
    monkeypatch.setattr(C, "affiner", lambda cle, exemples: (ecole.charger(cle)[0], mauvais, []))
    bilan = C.reviser(mem, "philosophie")
    assert not bilan["adoptee"] and mem.revisions()[0]["adoptee"] is False
    assert ecole.repondre("philosophie", "impératif catégorique")[0] == avant
    assert mem.corrections_de("philosophie", seulement_nouvelles=True)      # toujours en attente


def test_outil_de_correction_de_l_assistante(labo):
    from ia_aissa.assistant import OUTILS, executer_outil
    mem, _ = labo
    assert any(o["name"] == "corriger_ia_aissa" for o in OUTILS)
    r = executer_outil("corriger_ia_aissa", {"matiere": "comptabilite", "question": "achat de laptops",
                                             "bonne_reponse": "2355"}, None,
                       lambda cle, q, rep: C.corriger(mem, "Aissa", cle, q, rep))
    assert r["bonne_reponse"] == "2355 Matériel informatique"


def test_etude_autonome_des_lacunes(labo):
    import json
    from types import SimpleNamespace as NS
    from ia_aissa import autonomie as A
    mem, _ = labo
    for q in ["paiement de la facture maroc telecom", "bonjour comment ça va", "achat de 3 ordinateurs pour le bureau"]:
        assert A.noter_si_lacune(mem, q)
    assert not A.noter_si_lacune(mem, "agadir")                       # IA AISSA est sûre d'elle : pas de lacune
    reponses = {"paiement de la facture maroc telecom": ("comptabilite", "6145"),
                "achat de 3 ordinateurs pour le bureau": ("comptabilite", "2355 Matériel informatique")}

    def moteur(**kw):
        consigne = kw["messages"][0]["content"]
        lignes = consigne.split("Questions :\n")[1].split("\n\n")[0].splitlines()
        sortie = []
        for ligne in lignes:
            i, q = ligne.split(". ", 1)
            m, r = reponses.get(q, (None, None))
            sortie.append({"id": int(i), "matiere": m, "reponse": r})
        return NS(content=[NS(type="text", text=json.dumps(sortie))])

    bilan = A.etudier_seule(mem, {"type": "anthropic", "modele": "claude-opus-5-5"}, NS(messages=NS(create=moteur)))
    assert (bilan["etudiees"], bilan["apprises"], bilan["hors_programme"]) == (3, 2, 1)
    assert mem.lacunes_ouvertes() == []
    revisions = {b["matiere"]: b["adoptee"] for b in bilan["revisions"]}
    assert revisions["comptabilite"] and "orientation" in revisions   # l'aiguilleur révise aussi (adopté ou refusé)
    assert ecole.repondre("comptabilite", "paiement de la facture maroc telecom")[0]["reponse"].startswith("6145")
    assert {c["source"] for c in mem.croissance()} == {"étude autonome"}
