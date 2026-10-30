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
    # redémarrage (nouvelle connexion, cache vidé) : le cerveau révisé revient de la base, l'original est intact
    assert not (ecole.dossier_revises() / "comptabilite.pt").exists()
    C.brancher(Memoire(f"sqlite:///{tmp / 'm.db'}"))
    assert ecole.repondre("comptabilite", question)[0]["reponse"] == "6145 Frais postaux et de télécommunications"
    # nouvelle version de l'école (cerveau d'origine changé) : la révision périmée est oubliée, les corrections
    # repassent « à apprendre », puis sont réapprises sur le nouveau cerveau
    original = ecole.DOSSIER_CERVEAUX / "comptabilite.pt"
    original.write_bytes(original.read_bytes() + b" ")
    mem2 = Memoire(f"sqlite:///{tmp / 'm.db'}")
    C.brancher(mem2)
    assert mem2.matieres_revisees() == [] or "comptabilite" not in mem2.matieres_revisees()
    assert mem2.corrections_de("comptabilite", seulement_nouvelles=True)
    C.reviser_tout(mem2)
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
    for q in ["paiement de la facture maroc telecom", "bonjour comment ça va", "chrit pc jdid l charika"]:
        assert A.noter_si_lacune(mem, q)
    assert not A.noter_si_lacune(mem, "agadir")                       # IA AISSA est sûre d'elle : pas de lacune
    reponses = {"paiement de la facture maroc telecom": ("comptabilite", "6145"),
                "chrit pc jdid l charika": ("comptabilite", "2355 Matériel informatique")}

    def moteur(**kw):
        consigne = kw["messages"][0]["content"]
        lignes = consigne.split("Questions :\n")[1].split("\n\n")[0].splitlines()
        sortie = []
        for ligne in lignes:
            i, q = ligne.split(". ", 1)
            m, r = reponses.get(q, (None, None))
            sortie.append({"id": int(i), "matiere": m, "reponse": r})
        return NS(content=[NS(type="text", text=json.dumps(sortie))])

    bilan = A.etudier_seule(mem, {"type": "anthropic", "modele": "claude-opus-5-5"}, NS(messages=NS(create=moteur)),
                            explorer=False)
    assert (bilan["etudiees"], bilan["apprises"], bilan["hors_programme"]) == (3, 2, 1)
    assert mem.lacunes_ouvertes() == []
    revisions = {b["matiere"]: b["adoptee"] for b in bilan["revisions"]}
    assert revisions["comptabilite"] and "orientation" in revisions   # l'aiguilleur révise aussi (adopté ou refusé)
    assert ecole.repondre("comptabilite", "paiement de la facture maroc telecom")[0]["reponse"].startswith("6145")
    assert {c["source"] for c in mem.croissance()} == {"étude autonome"}


def test_croissance_par_famille_de_sciences(labo):
    from ia_aissa import croissance
    mem, _ = labo
    depart = croissance.serie(mem).iloc[-1]
    C.corriger(mem, "Aissa", "unites", "la force se mesure en ?", "newton")
    C.reviser_tout(mem)
    apres = croissance.serie(mem).iloc[-1]
    assert apres["Sciences naturelles"] == depart["Sciences naturelles"] + 1
    assert apres["Sciences formelles"] == depart["Sciences formelles"]          # l'aiguilleur ne compte pas
    assert croissance.famille("comptabilite") == croissance.HUMAINES


def test_curiosite_guidee_par_le_progres(tmp_path):
    from ia_aissa.autonomie import par_progres
    from ia_aissa.croissance import vitesse_apprentissage
    from ia_aissa.memoire import Memoire
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    v = vitesse_apprentissage(mem)
    assert not v.empty and v["progres"].is_monotonic_decreasing and "orientation" not in set(v["matiere"])
    premiere, derniere = v["matiere"].iloc[0], v["matiere"].iloc[-1]
    lacunes = [{"id": 1, "matiere_devinee": derniere}, {"id": 2, "matiere_devinee": premiere}]
    assert [l["id"] for l in par_progres(mem, lacunes)] == [2, 1]
