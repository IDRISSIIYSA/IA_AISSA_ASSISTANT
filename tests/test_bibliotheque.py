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


def test_connaissance_digeree_comble_les_lacunes(labo):
    mem = labo
    mem.ajouter_lacune("c'est quoi la photosynthèse des plantes ?", "sciences", 0.1)
    mem.ajouter_lacune("prix du pétrole à Rotterdam", "economie", 0.1)
    bilan = B.digerer(mem, {"type": "anthropic", "modele": "x"}, moteur(), "Livre de test", LIVRE, nb_bouchees=1)
    assert [c["concept"] for c in bilan["lacunes_comblees"]] == ["Photosynthèse"]
    assert [l["question"] for l in mem.lacunes_ouvertes()] == ["prix du pétrole à Rotterdam"]


def test_hors_programme_part_en_exploration(labo, monkeypatch):
    from ia_aissa import autonomie as A
    mem = labo
    mem.ajouter_lacune("comment fonctionne la photosynthèse", "sciences", 0.1)
    explores = []
    monkeypatch.setattr(B, "brouter_wikipedia", lambda sujet: (explores.append(sujet) or "Wikipédia — Photosynthèse", LIVRE))

    def creer(**kw):
        c = kw["messages"][0]["content"]
        if c.startswith("Tu aides IA AISSA"):          # étude : rien dans le programme de l'école
            return NS(content=[NS(type="text", text="[]")])
        return moteur().messages.create(**kw)
    bilan = A.etudier_seule(mem, {"type": "anthropic", "modele": "x"}, NS(messages=NS(create=creer)))
    assert explores == ["comment fonctionne la photosynthèse"] and bilan["explorations"][0]["concepts"] > 0
    assert any("Wikipédia" in d["source"] for d in mem.digestions())


def test_inspirations_de_la_bibliotheque_dans_l_invention():
    import random
    from ia_aissa import invention as I
    vus = []
    client = NS(messages=NS(create=lambda **kw: vus.append(kw["messages"][0]["content"]) or
                            NS(content=[NS(type="text", text="[]")])))
    I.generer_population({"type": "anthropic", "modele": "x"}, client, "problème", 2, random.Random(1),
                         [{"concept": "Photosynthèse", "source": "Livre", "explication": "lumière en énergie"}])
    assert "Photosynthèse (Livre)" in vus[0]


def test_broutage_autonome_sous_le_seuil(labo, monkeypatch):
    from ia_aissa import autonomie as A
    mem = labo
    explores = []
    monkeypatch.setattr(B, "brouter_wikipedia", lambda sujet: (explores.append(sujet) or "Wikipédia — Photosynthèse", LIVRE))
    sure = [{"confiance": 0.95, "cle": "sciences"}]
    hesitante = [{"confiance": 0.42, "cle": "sciences"}]
    config = {"type": "anthropic", "modele": "x"}
    assert A.brouter_si_lacune(mem, config, moteur(), "comment fonctionne la photosynthèse", sure) is None
    assert A.brouter_si_lacune(mem, config, moteur(), "salut", hesitante) is None      # trop vague
    assert explores == []
    bilan = A.brouter_si_lacune(mem, config, moteur(), "comment fonctionne la photosynthèse", hesitante)
    assert explores == ["comment fonctionne la photosynthèse"]
    assert bilan["confiance_avant"] == 0.42 and bilan["concepts"] > 0


def test_broutage_trace_sur_le_tableau_de_croissance(labo):
    mem = labo
    assert croissance.broutage(mem).empty
    mem.garder_digestion("IA AISSA", "Wikipédia — Photosynthèse", "Sciences naturelles",
                         json.dumps([{"nom": "a"}, {"nom": "b"}]), "", 0.8)
    mem.garder_digestion("Aissa", "Livre", "Sciences humaines et gestion", json.dumps([{"nom": "c"}]), "", 0.6)
    b = croissance.broutage(mem)
    assert int(b["Concepts broutés seule"].sum()) == 2 and int(b["Concepts lus avec toi"].sum()) == 1
    assert abs(b["Confiance de digestion"].iloc[-1] - 0.7) < 1e-9


def test_curiosite_cible_les_matieres_faibles(labo):
    from ia_aissa import curiosite as Q
    mem = labo
    classement = Q.matieres_faibles(mem, n=50)
    assert [x["faiblesse"] for x in classement] == sorted((x["faiblesse"] for x in classement), reverse=True)
    derniere = classement[-1]
    for _ in range(30):                                   # beaucoup de lacunes : elle remonte en tête
        mem.ajouter_lacune(f"question {_} sur {derniere['nom']}", derniere["cle"], 0.1)
    assert Q.matieres_faibles(mem, n=1)[0]["cle"] == derniere["cle"]


def test_cycle_de_curiosite_sans_humain(labo):
    from ia_aissa import curiosite as Q
    mem = labo
    lus = []

    def source(sujet):
        lus.append(sujet)
        return "Wikipédia — Photosynthèse", LIVRE

    def bloquee(sujet):
        raise B.ErreurBroutage("limite les visites (429)")
    bilan = Q.cycle_curiosite(mem, {"type": "anthropic", "modele": "x"}, moteur(), nb_matieres=1,
                              sources=[source, bloquee])
    cible = bilan["matieres"][0]
    assert lus == [cible["nom"]] and bilan["concepts"] > 0 and bilan["erreurs"]
    assert bilan["recompense"] == 1.0                     # bibliothèque vide : tout est nouveau
    assert any(d["source"].startswith(f"Curiosité ({cible['nom']})") for d in mem.digestions())
    again = Q.cycle_curiosite(mem, {"type": "anthropic", "modele": "x"}, moteur(), nb_matieres=1, sources=[source])
    assert again["recompense"] < 0.5                      # relire la même chose ne rapporte presque rien


def test_resumes_openalex_reconstitues(monkeypatch):
    import requests
    reponse = NS(status_code=200, headers={}, raise_for_status=lambda: None, json=lambda: {"results": [
        {"display_name": "Budget", "publication_year": 2020,
         "abstract_inverted_index": {"budget": [1], "Le": [0], "pilote": [2]}}]})
    monkeypatch.setattr(requests, "get", lambda *a, **k: reponse)
    titre, texte = B.brouter_openalex("contrôle de gestion")
    assert titre == "OpenAlex — contrôle de gestion" and texte == "Budget (2020) : Le budget pilote"
