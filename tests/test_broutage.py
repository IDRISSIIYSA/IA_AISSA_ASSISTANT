import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import broutage as BR  # noqa: E402
from ia_aissa import corrections as C  # noqa: E402
from ia_aissa import ecole  # noqa: E402
from ia_aissa.bibliotheque import ErreurBroutage  # noqa: E402
from ia_aissa.memoire import Memoire  # noqa: E402

ARTICLE = "Le contrôle de gestion compare le budget et le réalisé pour piloter la performance. " * 30


class Reponse:
    def __init__(self, code=200, texte="", entetes=None):
        self.status_code, self.text, self.headers = code, texte, entetes or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


@pytest.fixture
def reseau(monkeypatch):
    """Faux internet : robots.txt, pages, et une file de réponses programmées."""
    visites, file = [], []

    def get(url, params=None, headers=None, timeout=None):
        visites.append((url, params, headers))
        if url.endswith("/robots.txt"):
            return Reponse(200, "User-agent: *\nDisallow: /prive/\n")
        return file.pop(0) if file else Reponse(200, "<html><nav>menu</nav><p>" + ARTICLE + "</p></html>")
    import requests
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(BR, "adresse_publique", lambda url: url)
    return visites, file


def test_politesse_robots_identite_et_delais(reseau):
    visites, _ = reseau
    pauses = []
    b = BR.Brouteur(dormir=pauses.append)
    texte = b.page("https://exemple.org/cours")
    b.page("https://exemple.org/cours2")
    assert "menu" not in texte and len(texte) <= BR.TAILLE_MAX_PAGE
    assert all(h["User-Agent"].startswith("IA-AISSA/") for _, _, h in visites)   # identité honnête, jamais déguisée
    assert len(pauses) == 1 and 0 < pauses[0] <= 5                               # 2 à 5 s entre deux visites d'un site
    with pytest.raises(ErreurBroutage, match="robots.txt"):
        b.page("https://exemple.org/prive/notes")


def test_repos_sur_429(reseau):
    _, file = reseau
    file.append(Reponse(429, "", {"Retry-After": "120"}))
    b = BR.Brouteur(dormir=lambda s: None)
    with pytest.raises(ErreurBroutage, match="429"):
        b.page("https://exemple.org/a")
    with pytest.raises(ErreurBroutage, match="au repos"):
        b.page("https://exemple.org/b")                         # le site est laissé tranquille pendant le repos


def test_arxiv_et_choix_du_sujet(reseau, tmp_path):
    _, file = reseau
    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Graph theory for budgets</title>'
            '<summary>We study cost allocation on graphs.</summary></entry></feed>')
    file.append(Reponse(200, atom))
    source, texte = BR.Brouteur(dormir=lambda s: None).arxiv("théorie des graphes")
    assert source.startswith("arXiv") and "cost allocation" in texte
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    sujet, famille = BR.choisir_sujet(mem)
    assert famille in BR.SUJETS and sujet in BR.SUJETS[famille]
    mem.ajouter_lacune("prix du pétrole à Rotterdam", "economie", 0.1)
    assert BR.choisir_sujet(mem) == ("prix du pétrole à Rotterdam", None)       # les lacunes passent en premier


def test_cycle_complet_rumination_et_injection(reseau, tmp_path, monkeypatch):
    dossier = tmp_path / "cerveaux"
    shutil.copytree(ecole.DOSSIER_CERVEAUX, dossier)
    monkeypatch.setattr(ecole, "DOSSIER_CERVEAUX", dossier)
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    C.brancher(mem)
    _, file = reseau
    file += [Reponse(200, json.dumps({"query": {"search": [{"title": "Contrôle de gestion"}]}})),
             Reponse(200, json.dumps({"query": {"pages": {"1": {"extract": ARTICLE}}}}))]

    def moteur(**kw):
        c = kw["messages"][0]["content"]
        r = ({"famille": "Sciences humaines et gestion", "concepts": [{"nom": "Écart budgétaire", "explication": "x"}],
              "analogie_controle_gestion": "Réallouer les ressources vers les centres en dérive.", "confiance": 0.8}
             if c.startswith("Tu es le système digestif") else [])
        return NS(content=[NS(type="text", text=json.dumps(r, ensure_ascii=False))])
    monkeypatch.setattr(BR, "choisir_sujet", lambda m, rng=None: ("contrôle de gestion", "Sciences humaines et gestion"))
    bilan = BR.cycle(mem, {"type": "anthropic", "modele": "x"}, NS(messages=NS(create=moteur)),
                     BR.Brouteur(dormir=lambda s: None))
    assert bilan["concepts"] == 1 and bilan["injections"] == 1 and bilan["source"].startswith("Wikipédia")
    assert mem.idees_de("IA AISSA")[0]["description"].startswith("Réallouer")
    ecole.STOCKAGE = None
    ecole._CACHE.clear()
