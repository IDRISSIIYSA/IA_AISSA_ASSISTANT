import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import bibliotheque as B  # noqa: E402
from ia_aissa import corrections as C  # noqa: E402
from ia_aissa import croissance  # noqa: E402
from ia_aissa import ecole  # noqa: E402
from ia_aissa.memoire import Memoire  # noqa: E402

LIVRE = ("Le contrôle de gestion compare le budget et le réalisé. " * 40 +
         "La photosynthèse transforme la lumière en énergie chimique dans les plantes. " * 40)


@pytest.fixture
def labo(tmp_path, monkeypatch):
    dossier = tmp_path / "cerveaux"
    shutil.copytree(ecole.DOSSIER_CERVEAUX, dossier)
    monkeypatch.setattr(ecole, "DOSSIER_CERVEAUX", dossier)
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    C.brancher(mem)
    yield mem
    ecole.STOCKAGE = None
    ecole._CACHE.clear()


def moteur():
    def creer(**kw):
        c = kw["messages"][0]["content"]
        if c.startswith("Tu es le système digestif"):
            r = {"famille": "Sciences naturelles", "concepts": [
                {"nom": "Photosynthèse", "explication": "La lumière devient énergie chimique."},
                {"nom": "Écart budgétaire", "explication": "Différence entre budget et réalisé."}],
                 "analogie_controle_gestion": "La plante pilote son énergie comme un budget.", "confiance": 0.8}
        else:   # exercices pour l'école
            ids = [int(x.split(".")[0]) for x in c.split("Questions :\n")[1].split("\n\n")[0].splitlines()]
            r = [{"id": ids[0], "matiere": "sciences", "reponse": "Biologie (SVT)"}] + \
                [{"id": i, "matiere": None, "reponse": None} for i in ids[1:]]
        return NS(content=[NS(type="text", text=json.dumps(r, ensure_ascii=False))])
    return NS(messages=NS(create=creer))


def test_livre_mange_en_bouchees_reparties():
    morceaux = B.bouchees("a" * (B.TAILLE_MORCEAU * 20), 4)
    assert len(morceaux) == 4
    assert B.bouchees("court texte", 4) == ["court texte"]


def test_adresses_internes_refusees():
    for url in ["http://127.0.0.1/admin", "http://169.254.169.254/latest/meta-data", "http://localhost:8501",
                "file:///etc/passwd", "ftp://exemple.com/x"]:
        with pytest.raises(B.ErreurBroutage):
            B.adresse_publique(url)


def test_lecture_html_sans_menus_ni_scripts():
    titre, texte = B.texte_html(b"<html><title>Cours</title><script>pirate()</script><nav>menu menu menu menu menu menu</nav>"
                                b"<p>Le seuil de rentabilite est atteint quand la marge couvre les charges fixes.</p></html>")
    assert titre == "Cours" and "seuil de rentabilite" in texte and "pirate" not in texte and "menu" not in texte


def test_digestion_complete_et_croissance(labo):
    mem = labo
    avant = croissance.serie(mem).iloc[-1].sum()
    bilan = B.digerer(mem, {"type": "anthropic", "modele": "claude-opus-5-5"}, moteur(), "Livre de test",
                      LIVRE, nb_bouchees=2)
    assert bilan["concepts"] == 2 * len(bilan["digestions"]) and bilan["exercices"] == 1
    assert {c["matiere"] for c in mem.corrections_de()} >= {"sciences"}
    assert croissance.serie(mem).iloc[-1].sum() > avant                  # la lecture fait grandir IA AISSA
    trouve = B.chercher(mem, "qu'est-ce que la photosynthèse ?")
    assert trouve and trouve[0]["concept"] == "Photosynthèse" and trouve[0]["source"] == "Livre de test"
    with pytest.raises(B.ErreurBroutage):
        B.digerer(mem, {"type": "anthropic", "modele": "x"}, moteur(), "vide", "trop court")
