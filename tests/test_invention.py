import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import invention as I  # noqa: E402
from ia_aissa.assistant import meta_conscience  # noqa: E402
from ia_aissa.avatar import avatar  # noqa: E402

CONFIG = {"type": "anthropic", "modele": "claude-opus-5-5"}


def moteur_simule():
    appels = []

    def creer(**kw):
        c = kw["messages"][0]["content"]
        appels.append(c)
        n = sum(1 for a in appels if a.startswith("Tu es le Critique"))
        if c.startswith("Tu es le Critique"):
            r = {"objections": ["coût"], "affirmations_a_verifier": ["chiffre douteux"] * max(0, 2 - n),
                 "faisabilite": 4 + n, "efficience": 5, "equilibre_financier": 3 + n}
        elif c.startswith("Tu es le Créateur"):
            r = {"titre": f"Idée v{n}", "description": "révisée", "reponses": ["coût réduit"]}
        elif c.startswith("Tu es le Contrôleur"):
            r = [{"index": i, "nouveaute": i, "impact": 5, "faisabilite": 5, "cout": 5, "defaut": "d"} for i in range(8)]
        else:
            r = [{"titre": f"I{i}", "description": "d", "domaines": ["a", "b"]} for i in range(4)]
        return NS(content=[NS(type="text", text="Voici : " + json.dumps(r))])

    return NS(messages=NS(create=creer)), appels


def test_evolution_puis_debat_en_trois_tours():
    client, appels = moteur_simule()
    historique, meilleure = I.evoluer(CONFIG, client, "problème", generations=2, taille=4, seed=3)
    assert len(historique) == 2 and meilleure["score"] == max(i["score"] for g in historique for i in g)
    finale, debat, meta = I.debattre(CONFIG, client, "problème", meilleure, iterations=3)
    assert [t["agent"] for t in debat] == ["Critique", "Créateur"] * 3 and finale["titre"] == "Idée v3"
    assert meta["evolution"] == sorted(meta["evolution"]) and meta["doutes_restants"] == 0
    assert 0 < meta["confiance"] <= 1 and 0 < meta["faisabilite"] <= 1
    assert len(appels) == 2 * 2 + 2 * 3                         # coût maîtrisé : 2 appels par génération et par tour


def test_doutes_baissent_la_confiance():
    sur = {"objections": [], "affirmations_a_verifier": [], "faisabilite": 8, "efficience": 8, "equilibre_financier": 8}
    douteux = dict(sur, affirmations_a_verifier=["a", "b", "c", "d", "e"])
    assert I.score_meta([sur, sur])["confiance"] > I.score_meta([douteux, douteux])["confiance"]


def test_annonce_darija_avec_proverbe_et_salutation():
    texte, sens = I.annonce_darija({"titre": "Facturation symbiotique"}, {"confiance": 0.71}, nom="Aissa")
    assert "Aissa" in texte and "71" in texte and any(p in texte for p, _ in I.PROVERBES) and sens


def test_hyper_propulsion_et_indicateur():
    h = avatar("Bonjour", etat="hyper", indicateur={"confiance": 0.83, "details": "2 outil(s) · 1.2 s"})
    assert 'class="alien photo reference hyper"' in h and "QUANTUM FUSION" in h and "confiance 83%" in h
    assert 'class="alien photo reference"' in avatar("Bonjour")
    assert 'class="alien hyper"' in avatar("Bonjour", etat="hyper", rendu="3d")


def test_meta_conscience():
    journal = [{"outil": "calculer_ir", "resultat": "{}"},
               {"outil": "consulter_ecole", "resultat": json.dumps({"propositions_ia_aissa": [{"confiance": 0.5}]})},
               {"outil": "calculer_is", "resultat": "Erreur : x"}]
    m = meta_conscience(journal, 2.0)
    assert m["confiance"] == round((0.85 + 0.95 + 0.5 + 0.4) / 4, 3) and m["details"] == "3 outil(s) · 2.0 s"


def test_alien_photo_par_defaut_aux_yeux_qui_clignent():
    h = avatar("Bonjour")
    assert "data:image/jpeg;base64," in h and 'class="paupiere g"' in h and 'class="paupiere d"' in h


def test_alien_3d_avec_repli_2d():
    h = avatar("Bonjour", rendu="3d")
    assert 'id="alien3d"' in h and 'id="alien2d"' in h and "three@0.160.0" in h      # 3D + alien dessiné en secours
    assert "window.alienParle = oui" in h                                             # la bouche 3D suit la parole
    assert 'id="alien3d"' not in avatar("Bonjour", en_3d=False, rendu="3d")
    assert 'data-hyper="1"' in avatar("Bonjour", etat="hyper", rendu="3d")
