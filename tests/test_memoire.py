import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa.assistant import executer_outil, profil_conversation  # noqa: E402
from ia_aissa.memoire import Memoire, historique_api  # noqa: E402


@pytest.fixture
def memoire(tmp_path):
    return Memoire(f"sqlite:///{tmp_path / 'test.db'}")


def test_conversation_enregistree_et_reprise(memoire):
    cid = memoire.nouvelle_conversation("Aissa", "Combien d'IR pour 8000 DH ?")
    memoire.ajouter_message("Aissa", cid, "user", "Combien d'IR pour 8000 DH ?")
    memoire.ajouter_message("Aissa", cid, "assistant", "Environ 500 DH par mois.")
    assert memoire.lister_conversations("Aissa")[0]["titre"] == "Combien d'IR pour 8000 DH ?"
    assert historique_api(memoire.messages_de("Aissa", cid)) == [
        {"role": "user", "content": "Combien d'IR pour 8000 DH ?"},
        {"role": "assistant", "content": "Environ 500 DH par mois."}]


def test_chaque_utilisateur_ne_voit_que_sa_memoire(memoire):
    cid = memoire.nouvelle_conversation("Aissa", "secret")
    memoire.memoriser("Aissa", "Aissa travaille à Fès.")
    assert memoire.lister_conversations("Karim") == [] and memoire.souvenirs_de("Karim") == []
    assert memoire.messages_de("Karim", cid) == []
    with pytest.raises(PermissionError):
        memoire.ajouter_message("Karim", cid, "user", "intrusion")
    memoire.supprimer_conversation("Karim", cid)
    assert len(memoire.lister_conversations("Aissa")) == 1


def test_souvenirs_sans_doublon_et_oubli(memoire):
    a = memoire.memoriser("Aissa", "  Aissa préfère   les réponses en darija. ")
    assert memoire.memoriser("Aissa", "Aissa préfère les réponses en darija.") == a
    memoire.oublier("Aissa", a)
    assert memoire.souvenirs_de("Aissa") == []


def test_question_sans_reponse_retiree_de_l_historique():
    assert historique_api([{"role": "user", "texte": "a"}]) == []


def test_outil_memoriser_et_profil(memoire):
    executer_outil("memoriser_souvenir", {"fait": "Aissa prépare le bac."}, lambda f: memoire.memoriser("Aissa", f))
    profil = profil_conversation("Aissa", "Lycée / Baccalauréat", False, [s["fait"] for s in memoire.souvenirs_de("Aissa")])
    assert "Aissa prépare le bac." in profil and "memoriser_souvenir" in profil
