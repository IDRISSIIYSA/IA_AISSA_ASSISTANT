import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia_aissa import corrections as C  # noqa: E402
from ia_aissa import ecole  # noqa: E402
from ia_aissa.assistant import converser  # noqa: E402
from ia_aissa.espace import analyser_controle, detecter_role, intention, reponse_locale, urls  # noqa: E402
from ia_aissa.memoire import Memoire  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("texte,fichiers,role", [
    ("écris une fonction python qui trie une liste", (), "programmeur"),
    ("invente un système pour réduire les retards de paiement", (), "inventeur"),
    ("analyse l'écart entre budget et réalisé", (), "controleur"),
    ("qu'est-ce que la photosynthèse ?", (), "savant"),
    ("voici mes chiffres", ("ventes.xlsx",), "controleur"),
    ("résume ce livre", ("livre.pdf",), "lecteur"),
    ("lis https://fr.wikipedia.org/wiki/Maroc", (), "lecteur"),
    ("bonjour, ça va ?", (), "compagnon"),
])
def test_role_choisi_selon_la_demande(texte, fichiers, role):
    assert detecter_role(texte, fichiers) == role


def test_intentions_et_liens():
    assert intention("montre-moi ton bulletin") == "bulletin"
    assert intention("qu'as-tu lu cette semaine ?") == "bibliotheque"
    assert intention("apprends-moi à prononcer en darija") == "prononciation"
    assert intention("bonjour") is None
    assert urls("voir https://exemple.ma/page et http://a.b/c.") == ["https://exemple.ma/page", "http://a.b/c."]


def test_reponse_locale_sans_cle():
    assert "Souss-Massa" in reponse_locale("agadir")[0]
    reponse, etapes, confiance = reponse_locale("zzz qwerty xyz")
    assert "pas sûre de comprendre" in reponse and confiance < 0.3 and etapes


def test_ia_aissa_pense_avec_son_propre_cerveau():
    from ia_aissa.pensee import MemoireAssociative, calculer, nombres, penser
    assert nombres("8 000 dh et 1.234.567 puis 12,5 et 8k") == [8000.0, 1234567.0, 12.5, 8000.0]
    assert "87" in penser("combien font 12*7+3 ?")[0]
    assert "7 273.65" in penser("salaire brut 8000 dh")[0]                     # paie marocaine
    assert "18 800" in penser("ir sur 10000 dh par mois")[0]                    # IR annuel (×12)
    assert "1 979.87" in penser("crédit 300000 dh à 5% sur 20 ans")[0]
    assert calculer("__import__('os').system('ls')") is None                     # jamais d'exécution de code
    reponse, etapes, confiance = penser("chkoun li bna lkoutoubia")
    assert "Almohades" in reponse and confiance > 0.8 and any("Mémoire associative" in e for e in etapes)
    m = MemoireAssociative([("achat d'un camion", "comptabilite", "2340 Matériel de transport")])
    assert m.chercher("chrit camion")[0]["reponse"] == "2340 Matériel de transport"


def test_les_corrections_nourrissent_la_memoire_associative(tmp_path):
    from ia_aissa.memoire import Memoire
    from ia_aissa.pensee import memoire_associative
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    avant = len(memoire_associative(mem).souvenirs)
    mem.ajouter_correction("Aissa", "comptabilite", "chrit camion l charika", "2340 Matériel de transport", "utilisateur")
    assert len(memoire_associative(mem).souvenirs) == avant + 1


def test_controleur_de_gestion_sur_un_fichier_brut():
    resume, elements, precision = analyser_controle(
        "suivi_budgetaire_2024.xlsx", (RACINE / "exemples" / "suivi_budgetaire_2024.xlsx").read_bytes(), n_episodes=8)
    assert "4 centre(s)" in resume and "écart global" in resume
    assert {e["type"] for e in elements} >= {"metriques", "graphique", "tableau", "telechargement", "liste"}
    assert 0 <= precision <= 1


def test_programmeur_execute_le_code_dans_le_bac_a_sable():
    appels = []

    def creer(**kw):
        appels.append([t["type"] for t in kw["tools"] if "type" in t])
        if len(appels) == 1:
            return NS(stop_reason="pause_turn", content=[
                NS(type="server_tool_use", id="s1", name="bash_code_execution", input={"command": "python t.py"})])
        return NS(stop_reason="end_turn", content=[
            NS(type="bash_code_execution_tool_result", tool_use_id="s1",
               content=NS(type="bash_code_execution_result", stdout="[1, 2, 3]\n", stderr="", return_code=0)),
            NS(type="text", text="Trié : [1, 2, 3].")])
    journal = []
    texte = converser(NS(beta=NS(messages=NS(create=creer))), [{"role": "user", "content": "trie"}],
                      journal=journal, execution_code=True)
    assert texte == "Trié : [1, 2, 3]." and appels[0] == ["code_execution_20260521"]
    assert journal == [{"outil": "exécution de code", "entree": {"command": "python t.py"}, "resultat": "[1, 2, 3]"}]
    sans = []
    converser(NS(beta=NS(messages=NS(create=lambda **kw: sans.append(kw["tools"]) or NS(
        stop_reason="end_turn", content=[NS(type="text", text="ok")])))), [{"role": "user", "content": "x"}])
    assert not any(t.get("type") == "code_execution_20260521" for t in sans[0])     # pas de bac à sable par défaut


def test_espace_unique_s_ouvre_et_repond_sans_cle(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    dossier = tmp_path / "cerveaux"
    shutil.copytree(ecole.DOSSIER_CERVEAUX, dossier)
    monkeypatch.setattr(ecole, "DOSSIER_CERVEAUX", dossier)
    for cle in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MINIMAX_API_KEY"):
        monkeypatch.delenv(cle, raising=False)
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    import ia_aissa.parole as P
    monkeypatch.setattr(P, "synthetiser", lambda t, l: b"ID3")
    at = AppTest.from_file(str(RACINE / "controle_gestion_ia.py"), default_timeout=300).run()
    assert not at.exception and any("alien3d" in str(e.proto) for e in at.get("iframe"))
    at.chat_input[0].set_value("agadir").run()
    assert not at.exception and "Souss-Massa" in at.chat_message[-1].markdown[1].value
    ecole.STOCKAGE = None
    ecole._CACHE.clear()


def test_barre_de_conversation_ergonomique():
    from ia_aissa.interface import STYLE
    for regle in ("stChatInputMicButton", "stChatInputApproveButton", "stChatInputCancelButton", "micro-respire",
                  ":has([data-testid=\"stChatInputApproveButton\"])", "Enregistrement", "prefers-reduced-motion"):
        assert regle in STYLE


def test_cle_api_gardee_dans_le_coffre_de_l_appareil(monkeypatch):
    import ia_aissa.interface as I
    from ia_aissa import coffre
    nom = I.nom_cookie("ANTHROPIC_API_KEY")
    assert nom == "ia_aissa_anthropic_api_key"
    monkeypatch.setattr(coffre.st, "session_state", {"coffre_valeurs": {nom: "sk-ant-test"}})
    assert I.lire_cle_cookie(nom) == "sk-ant-test"                    # relue depuis le stockage local
    I.ecrire_cookie(nom, None)                                        # « oublier »
    assert I.lire_cle_cookie(nom) is None
    assert coffre.st.session_state["coffre_ecritures"] == [(nom, None)]   # effacée du navigateur au prochain affichage


def test_le_compte_administrateur_est_le_compte_du_proprietaire(tmp_path):
    from ia_aissa import admin
    from ia_aissa.memoire import Memoire
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    admin.creer_admin(mem, "motdepasse-solide", "Aissa")
    assert admin.proprietaire(mem) == "Aissa"
    assert admin.verifier_utilisateur(mem, "aissa", "motdepasse-solide") == "Aissa"   # même compte pour entrer
    jeton = admin.ouvrir_session(mem, "Aissa")
    assert admin.session(mem, jeton) == "Aissa"                        # connexion retenue sur l'appareil
    admin.fermer_session(mem, jeton)
    assert admin.session(mem, jeton) is None


def test_la_bibliotheque_n_ajoute_que_des_lectures_pertinentes(tmp_path):
    import json
    from ia_aissa.memoire import Memoire
    from ia_aissa.pensee import penser
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    mem.garder_digestion("Aissa", "wikipedia", "Sciences humaines", json.dumps(
        [{"nom": "7 World Trade Center", "explication": "La tour a été inaugurée le 18 mai 2006."}]), "", 0.8)
    assert "World Trade" not in penser("chkoun li bna lkoutoubia", mem)[0]


def test_roles_de_conseil_et_ecoute_securisee():
    from ia_aissa.ecoute import SECURITE, ecoute_locale, en_detresse
    attendus = {"je me sens triste et seul": "psy", "mon employeur veut me licencier sans préavis": "social",
                "comment passer l'écriture d'une facture": "comptable", "je veux un prêt pour investir": "financier",
                "mon wifi ne marche plus": "technicien", "mon voisin ne paie pas, quel tribunal": "juriste"}
    for question, role in attendus.items():
        assert detecter_role(question) == role, question
    for phrase in ("je veux en finir", "bghit nmout", "j'ai envie de mourir"):
        assert en_detresse(phrase) and ecoute_locale(phrase) == SECURITE
    assert "141" in SECURITE and "19" in SECURITE
    assert not en_detresse("je suis stressé par mon examen") and "pas un psychologue" in ecoute_locale("je suis stressé")


def test_evolutions_fiscales_et_annees_qui_ne_sont_pas_des_montants():
    from ia_aissa.pensee import penser
    r = penser("QU IL EST LEVOLUSTION DE TVA AU MAROC DE 2021 A 2026")[0]
    assert "Évolution de la TVA" in r and "20 %" in r and "10 %" in r and "TTC" not in r
    assert "Évolution de l'IS" in penser("évolution de l'IS")[0]
    assert "405.20" in penser("tva sur 2026 dh ht")[0]                        # un vrai montant reste un montant


def test_corrections_des_visiteurs_attendent_l_admin(tmp_path):
    from ia_aissa.memoire import Memoire
    from ia_aissa.pensee import correction_dans_la_conversation, propositions
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    merci = correction_dans_la_conversation("non, c'est 6145", mem, {"cle": "comptabilite"},
                                            "paiement de la facture maroc telecom", valider=False, auteur="Visiteur ab12")
    assert "administrateur la vérifiera" in merci and not mem.corrections_de()           # rien d'appris sans l'admin
    (cle, p), = propositions(mem)
    assert p["reponse"].startswith("6145") and p["auteur"] == "Visiteur ab12"


def test_espace_administrateur_s_affiche(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")

    def page():
        import streamlit as st
        st.session_state["admin"] = True
        from ia_aissa.espace_admin import espace_admin
        espace_admin()

    at = AppTest.from_function(page, default_timeout=300).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["📊 Tableau de bord", "📈 Apprentissage", "📚 Livres", "🕹️ Commandes",
                                          "👥 Visiteurs et accès", "🔑 Clés et sécurité"]
    assert any(m.label == "Corrections à valider" for m in at.metric)
