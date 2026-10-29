import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import admin  # noqa: E402
from ia_aissa.memoire import Memoire  # noqa: E402


@pytest.fixture
def mem(tmp_path):
    return Memoire(f"sqlite:///{tmp_path / 'a.db'}")


def test_mots_de_passe_jamais_en_clair():
    e = admin.empreinte("secret-123")
    assert "secret-123" not in e and e.startswith("pbkdf2$")
    assert admin.verifier("secret-123", e) and not admin.verifier("autre", e) and not admin.verifier("x", None)


def test_premier_administrateur_puis_connexion(mem):
    assert not admin.admin_existe(mem)
    with pytest.raises(ValueError):
        admin.creer_admin(mem, "court")
    jeton = admin.creer_admin(mem, "motdepasse-aissa")
    assert admin.jeton_valide(mem, jeton) and not admin.jeton_valide(mem, "faux")
    with pytest.raises(PermissionError):
        admin.creer_admin(mem, "un-intrus-123")                 # un seul administrateur
    assert admin.connexion_admin(mem, "mauvais") is None
    nouveau = admin.connexion_admin(mem, "motdepasse-aissa")
    assert admin.jeton_valide(mem, nouveau) and not admin.jeton_valide(mem, jeton)   # l'ancien jeton expire
    admin.deconnexion(mem)
    assert not admin.jeton_valide(mem, nouveau)
    admin.changer_mot_de_passe(mem, "motdepasse-aissa", "nouveau-mdp-99")
    assert admin.connexion_admin(mem, "nouveau-mdp-99")


def test_cles_de_l_application_et_personnes_autorisees(mem):
    admin.definir_valeur_app(mem, "ANTHROPIC_API_KEY", " sk-ant-abcdefghijklmnop ")
    assert admin.valeur_app(mem, "ANTHROPIC_API_KEY") == "sk-ant-abcdefghijklmnop"
    assert admin.masquer("sk-ant-abcdefghijklmnop") == "sk-ant-…mnop"
    with pytest.raises(KeyError):
        admin.definir_valeur_app(mem, "MEMOIRE_URL", "x")      # seules les clés prévues sont réglables
    admin.definir_valeur_app(mem, "ANTHROPIC_API_KEY", None)
    assert admin.valeur_app(mem, "ANTHROPIC_API_KEY") is None
    admin.ajouter_utilisateur(mem, "Karim", "karim-123")
    assert admin.verifier_utilisateur(mem, "karim", "karim-123") == "Karim"
    assert admin.verifier_utilisateur(mem, "Karim", "faux") is None
    admin.retirer_utilisateur(mem, "Karim")
    assert admin.utilisateurs(mem) == {}
