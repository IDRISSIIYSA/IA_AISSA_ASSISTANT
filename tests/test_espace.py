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


def test_creation_de_l_admin_exige_le_code_des_secrets(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    monkeypatch.delenv("ADMIN_CODE", raising=False)

    def page():
        from ia_aissa.espace_admin import espace_admin
        espace_admin()

    at = AppTest.from_function(page, default_timeout=300).run()
    assert not at.exception and "ADMIN_CODE" in at.error[0].value and not at.button      # bloqué sans code
    monkeypatch.setenv("ADMIN_CODE", "code-secret-123")
    at = AppTest.from_function(page, default_timeout=300).run()
    at.text_input(key="adm_code").set_value("mauvais")
    at.text_input(key="adm_new").set_value("motdepasse-solide")
    at.text_input(key="adm_new2").set_value("motdepasse-solide")
    at.button[0].click().run()
    assert "incorrect" in at.error[-1].value


def test_parle_de_tva_au_maroc_donne_une_vraie_fiche():
    from ia_aissa.pensee import nombres, penser
    r = penser("PARLE DE TVA AU MAROC")[0]
    assert "La TVA au Maroc" in r and "20 %" in r and "10 %" in r and "Exonéré" in r and "crédit de TVA" in r
    assert "La TVA au Maroc" in penser("TVA ?")[0] and "impôt sur les sociétés" in penser("c'est quoi l'IS")[0]
    assert "Almohades" in penser("parle des dynasties du maroc")[0]
    assert "Exonéré" in penser("tva dyal dwa")[0] and "La TVA au Maroc" not in penser("tva dyal dwa")[0]
    assert "TVA 200 DH" in penser("tva sur 1000 dh")[0]                           # aucun produit : taux normal
    assert nombres("dariba 3la rb7 dyal charika") == [] and nombres("khlast 3000dh") == [3000.0]
    assert "IS (impôt sur les sociétés)" in penser("dariba 3la rb7 dyal charika")[0]


def test_impots_budget_de_l_etat_et_balance_commerciale():
    from ia_aissa.pensee import penser
    q = ("ARLE MOI BIEVEMENT DES IMPOTS AU MAROC ET SUR LES RECTTES ET DEPENSE DE LETAT MAROCAIN ET LA BALANCE "
         "COMMERICALE")
    r = penser(q)[0]
    assert "Les impôts au Maroc" in r and "Recettes et dépenses de l'État" in r and "balance commerciale" in r
    assert "432.8" in r and "57.2 %" in r and "Plan Comptable" not in r                  # plus la mauvaise fiche
    assert "## 🎓 Imputation" not in penser("parle du maroc")[0]                       # pas la fiche du plan comptable
    assert "La TVA au Maroc" in penser("parle des impôts : la TVA")[0]


def test_un_extrait_de_lecture_doit_partager_plusieurs_vrais_mots(tmp_path):
    from ia_aissa.lecture import repondre_par_lecture
    from ia_aissa.memoire import Memoire
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    mem.garder_passages("IA AISSA", "OpenStax — Principles of Management", [
        "Finding the optimal balance between organizational and personal control is not an easy task for managers."])
    assert repondre_par_lecture("la balance commerciale du Maroc", mem) is None             # « balance » seul : non


def test_toutes_les_simulations(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from ia_aissa import simulations as S
    from ia_aissa.pensee import nombres, penser
    e = S.echeancier_credit(200_000, 0.05, 120)
    assert e["mensualite"] == 2121.31 and e["tableau"]["Capital restant dû"].iloc[-1] == 0
    assert S.epargne(500, 0.04, 10)["capital_final"] == 73624.9
    assert S.amortissement(100_000, 5, "degressif")["tableau"]["Dotation"].tolist() == [40000, 24000, 14400, 10800, 10800]
    r = S.rentabilite_investissement(100_000, [30_000, 40_000, 50_000, 20_000], 0.08)
    assert r["van"] > 0 and abs(r["tri"] - 0.1532) < 0.001 and r["delai_recuperation_ans"] == 2.6
    assert S.prix_de_vente(80, taux_de_marque=0.2)["prix_ht"] == 100
    assert S.tresorerie(10_000, [20_000] * 3, [25_000, 26_000, 10_000])["premier_mois_a_decouvert"] == 2
    assert 0 < S.risque_monte_carlo(800_000, 1_200_000, 0.55, 0.7, 350_000)["probabilite_de_perte"] < 1
    assert nombres("flux 30000 40000 50000 20000") == [30000, 40000, 50000, 20000]
    assert nombres("6 459,87 et 1.234,56") == [6459.87, 1234.56]
    assert "TRI 15.3%" in penser("TRI investissement 100000 flux 30000 40000 50000 20000 à 8%")[0]
    assert "2 121.31" in penser("échéancier crédit 200000 dh à 5% sur 10 ans")[0]
    assert "Monte-Carlo" in penser("quelles simulations sais-tu faire ?")[0]
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")

    def page():
        import streamlit as st
        from ia_aissa.espace_simulations import afficher
        from ia_aissa.partage import memoire
        afficher(st.session_state["simulation"], memoire())

    from ia_aissa.espace_simulations import CATEGORIES
    for noms in CATEGORIES.values():
        for nom in noms:
            at = AppTest.from_function(page, default_timeout=300)
            at.session_state["simulation"] = nom
            at.run()
            assert not at.exception, nom
            assert any("Méthode et justification" in m.value for m in at.markdown), nom
            assert any("Références" in m.value for m in at.markdown), nom


def test_secrets_ranges_dans_une_section_et_adresse_neon_copiee_avec_psql(monkeypatch):
    from ia_aissa import partage
    from ia_aissa.memoire import normaliser_url
    monkeypatch.setattr(partage.st, "secrets", {"general": {"ADMIN_CODE": " code-1 "}, "memoire_url": "sqlite://"})
    assert partage.secret("ADMIN_CODE") == "code-1" and partage.secret("MEMOIRE_URL") == "sqlite://"
    assert partage.noms_des_secrets() == ["ADMIN_CODE", "memoire_url"]
    assert normaliser_url("psql 'postgresql://u:p@h.neon.tech/db?sslmode=require'") == \
        "postgresql+psycopg://u:p@h.neon.tech/db?sslmode=require"


def test_diagnostic_des_secrets_sur_la_page_admin(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv("ADMIN_CODE", raising=False)
    monkeypatch.delenv("MEMOIRE_URL", raising=False)

    def page():
        from ia_aissa.espace_admin import espace_admin
        espace_admin()

    at = AppTest.from_function(page, default_timeout=300).run()
    texte = " ".join(i.value for i in at.info)
    assert "Diagnostic des Secrets" in texte and "❌ `ADMIN_CODE`" in texte and "❌ `MEMOIRE_URL (ou DATABASE_URL)`" in texte



def test_rapports_justifies_traces_et_pdf(tmp_path):
    from ia_aissa import baremes as B
    from ia_aissa.memoire import Memoire
    from ia_aissa.rapports import journal, journaliser, pdf, rapport, verifier
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    assert B.ir_annee(120_000, 2024)["ir_annuel"] == 120_000 * 0.34 - 17_200        # barème LF 2010 (38 % max)
    assert B.ir_annee(120_000, 2026)["ir_annuel"] == 18_800
    with pytest.raises(ValueError, match="non vérifié"):
        B.ir_annee(120_000, 1996)                                                       # jamais inventé
    B.ajouter_bareme_ir(mem, 1996, 1996, "Loi de finances 1996 (exemple de test)", "Bulletin officiel (test)",
                        [(20_000, 0.0, 0), (None, 0.4, 8_000)])
    assert B.ir_annee(100_000, 1996, mem)["ir_annuel"] == 32_000 and 1996 in B.annees_couvertes("ir", mem)
    with pytest.raises(ValueError, match="obligatoires"):
        B.ajouter_bareme_ir(mem, 1990, 1990, "", "", [(None, 0.4, 0)])
    r = rapport("IR (impôt sur le revenu)", "🧾 Fiscalité", {"Revenu": "120 000 DH"}, {"IR": "18 800 DH"},
                ["IR = revenu × taux − somme à déduire."], ["CGI, art. 73-I"], 2026)
    contenu = pdf(r)
    assert contenu.startswith(b"%PDF") and len(contenu) > 1000
    journaliser(mem, r)
    assert journal(mem)[0]["numero"] == r["numero"] and verifier(mem, r["numero"], r["empreinte"])
    assert not verifier(mem, r["numero"], "0" * 64)


def test_paie_complete_conseils_et_barre_repliable():
    from ia_aissa import connaissances as K
    from ia_aissa import simulations as S
    from ia_aissa.espace_simulations import CATEGORIES
    p = S.paie_complete(8000, 6, 2, 500)
    assert p["prime_anciennete"] == 800 and p["brut"] == 8800                         # 10 % après 5 ans (art. 350)
    assert p["deduction_famille"] == round(2 * 500 / 12, 2) and p["ir"] < p["ir_avant_famille"]
    assert set(p["patronal"]) == {"CNSS (prestations, plafonnée)", "Allocations familiales", "AMO",
                                  "Formation professionnelle"}
    assert S.paie_complete(3000)["sous_smig"] and not S.paie_complete(4000)["sous_smig"]  # 17,92 × 191 = 3 422,72
    assert K.taux_prime_anciennete(1) == 0 and K.taux_prime_anciennete(25) == 0.25
    assert len(CATEGORIES) >= 10 and sum(len(v) for v in CATEGORIES.values()) >= 28


def test_echeancier_date_amortissement_prorata_et_paie_a_l_envers():
    import datetime
    from ia_aissa import simulations as S
    e = S.echeancier_credit(200_000, 0.05, 120, datetime.date(2026, 1, 31))
    assert e["tableau"]["Échéance"].iloc[0] == "28/02/2026" and e["derniere_echeance"] == "31/01/2036"
    assert e["mensualite"] == 2121.31 and e["par_annee"]["Année"].iloc[0] == 2026
    d = S.echeancier_credit(100_000, 0.06, 24, datetime.date(2026, 1, 1), differe_mois=3)
    assert d["tableau"]["Capital remboursé"].iloc[:3].sum() == 0 and d["tableau"]["Capital restant dû"].iloc[-1] == 0
    a = S.amortissement(100_000, 5, "lineaire", 7, 2026)["tableau"]
    assert a["Dotation"].iloc[0] == 10_000 and a["Exercice"].iloc[-1] == 2031 and a["Dotation"].sum() == 100_000
    assert S.amortissement(100_000, 5, "degressif")["tableau"]["Dotation"].tolist() == [40000, 24000, 14400, 10800, 10800]
    base = S.base_pour_net(7_000, 6, 2)
    assert abs(S.paie_complete(base, 6, 2)["net"] - 7_000) <= 0.01
    assert S.retenue_dividendes(100_000, 2026)["taux"] == 0.1125 and S.RAS_DIVIDENDES[2027] == 0.10


def test_business_plan_obligations_et_impots_decortiques():
    import datetime
    from ia_aissa import decortiqueur as D, obligations as O, projets as P
    p = dict(ca_annee1=1_200_000, croissance_ca=0.10, taux_couts_variables=0.45, charges_fixes=450_000,
             hausse_charges_fixes=0.03, investissement=500_000, duree_amortissement=5, apport=200_000, emprunt=400_000,
             taux_emprunt=0.06, duree_emprunt_ans=5, delai_clients_jours=60, delai_fournisseurs_jours=30, stock_jours=30,
             taux_actualisation=0.10, annee_debut=2026, mois_debut=3)
    bp = P.business_plan(**p)
    cr = bp["compte_de_resultat"]
    assert cr["Exercice"].tolist() == [2026, 2027, 2028, 2029, 2030]
    assert cr["Chiffre d'affaires"].iloc[0] == 1_000_000                  # 10 mois sur 12 la 1re année
    assert cr["IS"].iloc[0] == round(cr["Résultat avant impôt"].iloc[0] * 0.20, 2)   # < 36 mois : pas de CM
    assert bp["van"] > 0 and 0 < bp["tri"] < 1 and bp["dscr_min"] > 1.2
    s = P.sensibilite(p)
    assert 0 < s["baisse_critique_des_ventes"] < 0.5 and len(s["tableau"]) == len(P.SCENARIOS)
    cal = O.calendrier(O.FORMES[0], 2026, datetime.date(2022, 1, 1), 2_000_000, 3, 24_000, 80_000, 30_000,
                       datetime.date(2026, 10, 30))
    t = cal["tableau"]
    assert (t["Obligation"].str.contains("acompte provisionnel").sum() == 4
            and t["Obligation"].str.contains("TVA du mois").sum() == 12
            and t["Obligation"].str.contains("9421").sum() == 1)
    assert cal["prochaine"]["Date limite"] == "31/10/2026"
    ae = O.calendrier(O.FORMES[2], 2026, datetime.date(2025, 1, 1), 150_000, 0, 0, 0)["tableau"]
    assert len(ae) == 4 and not ae["Obligation"].str.contains("TVA").any()
    f = D.revenus_fonciers(96_000, 120_000, 2026)
    assert f["net_foncier"] == 57_600 and f["taux_ras"] == 0.10 and f["ras"] == 9_600 and f["option_20"] == 19_200
    assert D.revenus_fonciers(30_000, 0, 2026)["dispense"]
    e = D.etat_9421([("A", 96_000, 5_370, 2, 0)], 2026)
    assert e["ecarts"] == ["A"] and e["total_brut"] == 96_000
    assert {"IR décortiqué", "IS décortiqué", "TVA décortiquée", "Documents et attestations de régularité"} <= set(D.FICHES)


def test_choix_entre_chat_et_simulations(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    from ia_aissa.espace_simulations import CATEGORIES, MODES
    assert len(CATEGORIES) >= 13 and sum(len(v) for v in CATEGORIES.values()) >= 60
    import ia_aissa.parole as P
    monkeypatch.setattr(P, "synthetiser", lambda t, l: b"ID3")
    at = AppTest.from_file(str(RACINE / "controle_gestion_ia.py"), default_timeout=300)
    at.run()
    assert not at.exception and at.session_state["mode_visiteur"] == MODES[0] and len(at.chat_input) == 1
    at.session_state["mode_visiteur"] = MODES[1]
    at.session_state["simulation"] = "Business plan sur 5 ans"
    at.run()
    assert not at.exception and len(at.chat_input) == 0
    assert any("Compte de résultat prévisionnel" in m.value for m in at.markdown)


def test_temps_d_ouverture_des_pages_sous_3_secondes(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from ia_aissa import chrono
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    import ia_aissa.parole as P
    monkeypatch.setattr(P, "synthetiser", lambda t, l: b"ID3")
    chrono.reinitialiser()
    at = AppTest.from_file(str(RACINE / "controle_gestion_ia.py"), default_timeout=300)
    at.run()                                             # premier affichage (imports déjà faits par les tests)
    at.run()
    at.session_state["mode_visiteur"] = "🧮 Simulations et guides"
    at.session_state["simulation"] = "Crédit (échéancier)"
    at.run()
    at.run()
    t = chrono.tableau().set_index("Page")
    assert {"Visiteurs — 💬 Chat avec IA AISSA", "Visiteurs — 🧮 Simulations et guides"} <= set(t.index)
    assert (t["Médiane (s)"] < chrono.OBJECTIF_S).all(), t
    assert chrono.age_du_processus() is None or chrono.age_du_processus() > 0


def test_adresse_de_la_memoire_donnee_par_neon(tmp_path, monkeypatch):
    from ia_aissa import partage
    monkeypatch.delenv("MEMOIRE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/neondb")
    assert partage.adresse_memoire().endswith("/neondb")              # le nom donné par Neon suffit
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    assert partage.adresse_memoire().startswith("sqlite")               # MEMOIRE_URL reste prioritaire
    (tmp_path / ".env.local").write_text('# neon deploy\nDATABASE_URL="postgresql://a:b@h/db"\nexport X=1\n')
    monkeypatch.setattr(partage, "RACINE", str(tmp_path))
    assert partage.fichier_env() == {}                                  # jamais pendant les tests
    monkeypatch.delenv("IA_AISSA_TESTS")
    assert partage.fichier_env() == {"DATABASE_URL": "postgresql://a:b@h/db", "X": "1"}


def test_simulations_dans_une_seule_liste_deroulante(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from ia_aissa.espace_simulations import CATEGORIES
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    import ia_aissa.parole as P
    monkeypatch.setattr(P, "synthetiser", lambda t, l: b"ID3")
    at = AppTest.from_file(str(RACINE / "controle_gestion_ia.py"), default_timeout=300).run()
    liste = at.sidebar.selectbox[0]
    assert len(at.sidebar.selectbox) == 1 and liste.value is None and not at.sidebar.expander
    assert len(liste.options) == sum(len(v) for v in CATEGORIES.values())
    liste.select("👥 Bulletin de paie complet").run()
    assert not at.exception and at.session_state["simulation"] == "Bulletin de paie complet"
    assert any(m.value == "### Bulletin de paie complet" for m in at.markdown) and len(at.chat_input) == 0
    at.sidebar.button[0].click().run()                    # ✖ Fermer : retour au chat
    assert "simulation" not in at.session_state and len(at.chat_input) == 1


def test_profit_foncier_solde_de_tout_compte_remboursement_anticipe_et_excel():
    import io
    import openpyxl
    from ia_aissa import simulations as S
    from ia_aissa.espace_simulations import excel
    from ia_aissa.rapports import rapport
    # Profit foncier : max(20 % du profit net, 3 % du prix), forfait de 15 %, exonérations
    x = S.profit_foncier(1_500_000, 20_000, 800_000, 0, 100_000, 1.30)
    assert x["frais_acquisition"] == 120_000 and x["profit_net"] == 154_000 and x["tpi"] == 45_000   # 3 % > 20 %
    assert S.profit_foncier(900_000, 0, 800_000, 0, 0, 1.0)["tpi"] == 27_000                        # dû sans profit
    assert S.profit_foncier(3_000_000, 0, 500_000, 0, 0, 1.2)["tpi"] == round((3_000_000 - 690_000) * 0.2, 2)
    assert S.profit_foncier(130_000, 0, 50_000, 0, 0, 1.0)["tpi"] == 0                              # ≤ 140 000 DH
    assert S.profit_foncier(2_000_000, 0, 500_000, 0, 0, 1.0, True)["tpi"] == 0                     # résidence 5 ans
    assert S.profit_foncier(5_000_000, 0, 500_000, 0, 0, 1.0, True)["tpi"] == 30_000                # 3 % > 4 MDH
    # Préavis (décret 2-04-469) et solde de tout compte
    assert S.preavis("Employé ou ouvrier", 0.5)[0] == "8 jours" and S.preavis("Cadre ou assimilé", 7)[0] == "3 mois"
    s = S.solde_de_tout_compte(8_000, "Cadre ou assimilé", 7, "Licenciement (hors faute grave)", False, 13, 13)
    assert s["imposable"] == 4_000 + 4_000 + 24_000 and s["exonere"] > 0
    assert len(S.solde_de_tout_compte(8_000, "Cadre ou assimilé", 7, "Démission", False, 13, 0)["tableau"]) == 2
    # Remboursement anticipé
    d = S.remboursement_anticipe(500_000, 0.05, 240, 60, 100_000, 1, "la durée")
    m = S.remboursement_anticipe(500_000, 0.05, 240, 60, 100_000, 1, "la mensualité")
    assert d["economie"] > m["economie"] > 0 and d["nouveaux_mois"] < 180 and m["nouvelle_mensualite"] < d["mensualite"]
    assert d["indemnite"] == round(100_000 * 0.05 / 12, 2)
    assert S.remboursement_anticipe(500_000, 0.05, 240, 60, 10**7)["nouveaux_mois"] == 0
    # Classeur Excel : synthèse et tableau
    r = rapport("Test", "🧾 Fiscalité", {"A": 1}, {"B": 2}, ["m"], ["CGI"], 2026, tableau=d and S.ferraillage([(12, 2, 6)])["tableau"])
    r["annexes"] = {"Compte de résultat": S.ferraillage([(10, 1, 1)])["tableau"]}
    classeur = openpyxl.load_workbook(io.BytesIO(excel(r)))
    assert classeur.sheetnames == ["Synthèse", "Tableau", "Compte de résultat"]
    valeurs = [c.value for c in classeur["Synthèse"]["B"]]
    assert "Test" in valeurs and r["empreinte"] in valeurs


def test_chaque_simulation_a_ses_propres_cles_de_saisie():
    import re
    proprietaires = {}
    for f in ("ia_aissa/espace_simulations.py", "ia_aissa/espace_simulations_plus.py"):
        courante = None
        for ligne in (RACINE / f).read_text(encoding="utf-8").splitlines():
            m = re.search(r'if nom == "([^"]+)"', ligne) or re.search(r"if nom in (.+):", ligne)
            courante = m.group(1) if m else courante
            for cle in re.findall(r'key="([^"{]+)"', ligne):
                proprietaires.setdefault(cle, set()).add(courante)
    assert not {k: v for k, v in proprietaires.items() if len(v) > 1}


def test_registre_des_taux_et_mises_a_jour(tmp_path):
    import datetime
    import pytest
    from ia_aissa import connaissances as K, parametres as P, simulations as S
    from ia_aissa.memoire import Memoire
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    avant = S.paie_complete(3_500)["sous_smig"]
    assert not avant and len(P.registre(mem)) == len(P.PARAMETRES)
    with pytest.raises(ValueError, match="source"):
        P.mettre_a_jour(mem, "smig_horaire", 19.0, "01/01/2027", "décret …", "")
    with pytest.raises(ValueError, match="décimal"):
        P.mettre_a_jour(mem, "cnss_salarie", 4.48, "01/01/2027", "décret", "BO")
    try:
        P.mettre_a_jour(mem, "smig_horaire", 19.0, "01/01/2027", "Décret de revalorisation 2027", "BO n° …")
        assert K.SMIG_HORAIRE_2026 == 19.0 and S.paie_complete(3_500)["sous_smig"]     # appliqué aux calculs
        ligne = P.registre(mem).set_index("Clé").loc["smig_horaire"]
        assert ligne["Valeur"] == "19 DH/heure" and ligne["Statut"].startswith("🛠️")
        P.annuler(mem, "smig_horaire")
        assert K.SMIG_HORAIRE_2026 == 17.92 and not P.historique(mem, "smig_horaire")
    finally:
        P.annuler(mem, "smig_horaire")
        P.appliquer(None)
    assert P.alertes(mem, datetime.date(2026, 10, 30)) == []
    nouvelle = P.alertes(mem, datetime.date(2027, 1, 15))
    assert any("Loi de finances 2027" in a for a in nouvelle) and any("revérifier" in a for a in nouvelle)


def test_voix_dans_la_langue_de_la_reponse_et_lecture_au_choix(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from ia_aissa.langues import detecter_langue, partie_dans_la_langue
    assert detecter_langue("Revenu net imposable **120 000 DH** : taux marginal 34 %, somme à déduire") == "Français"
    assert detecter_langue("La TVA au Maroc : la taxe sur la valeur ajoutée est un impôt") == "Français"
    assert detecter_langue("Salam ! Labas 3lik ? Je suis là. Pose-moi une question") == "Français"
    assert detecter_langue("The capital of Japan is Tokyo.") == "English"
    assert detecter_langue("El impuesto sobre la renta es progresivo") == "Español"
    assert detecter_langue("كيداير لاباس عليك؟ واش بغيتي تحسب الضريبة") == "Darija"
    assert detecter_langue("ما هي نسبة الضريبة على القيمة المضافة") == "Arabe"
    mixte = "مسا الخير، كيف داز نهارك؟\nBonsoir ! Je suis IA AISSA."
    assert partie_dans_la_langue(mixte, "Français") == "Bonsoir ! Je suis IA AISSA."
    assert partie_dans_la_langue(mixte, "Darija") == "مسا الخير، كيف داز نهارك؟"
    monkeypatch.setenv("MEMOIRE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    import ia_aissa.parole as P
    dites = []
    monkeypatch.setattr(P, "synthetiser", lambda t, l: dites.append(l) or b"ID3")
    import ia_aissa.interface as I
    monkeypatch.setattr(I, "synthetiser", lambda t, l: dites.append((l, t)) or b"ID3")
    at = AppTest.from_file(str(RACINE / "controle_gestion_ia.py"), default_timeout=300).run()
    assert at.toggle(key="lecture_voix").value is True
    assert [l for l, _ in dites] == ["Darija", "Français"]               # salut : chaque partie avec sa voix
    dites.clear()
    at.chat_input[0].set_value("Calcule mon IR pour un revenu net imposable de 120000 DH").run()
    assert dites and dites[-1][0] == "Français"                           # une réponse en français : voix française
    at.toggle(key="lecture_voix").set_value(False).run()
    dites.clear()
    at.chat_input[0].set_value("agadir").run()
    assert not at.exception and dites == []                               # lecture coupée : rien n'est lu
