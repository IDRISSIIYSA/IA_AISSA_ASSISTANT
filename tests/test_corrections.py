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


ARTICLE_LOCAL = ("Le contrôle de gestion aide la direction à piloter la performance. Le budget fixe les objectifs "
                 "de chaque centre de responsabilité. Le contrôle de gestion compare ensuite le budget au réalisé "
                 "et analyse chaque écart budgétaire. Un écart budgétaire défavorable déclenche une action corrective. "
                 "Le tableau de bord résume les indicateurs du contrôle de gestion pour chaque centre. ") * 2


def test_ia_aissa_lit_seule_sans_moteur(labo):
    from ia_aissa.autodidacte import ruminer_local
    from ia_aissa.bibliotheque import digerer
    d = ruminer_local(ARTICLE_LOCAL)
    noms = [c["nom"] for c in d["concepts"]]
    assert "Contrôle" in noms or "Budget" in noms or "Gestion" in noms
    assert d["famille"] in ("Sciences formelles", "Sciences naturelles", "Sciences humaines et gestion",
                            "Sciences appliquées") and 0 < d["confiance"] <= 0.6
    mem, _ = labo
    bilan = digerer(mem, None, None, "Wikipédia — Contrôle de gestion", ARTICLE_LOCAL, nb_bouchees=1)
    assert bilan["concepts"] >= 2 and bilan["exercices"] == 0 and mem.digestions()


def test_pratique_deliberee_sans_regression(labo):
    from ia_aissa.autodidacte import pratiquer
    mem, _ = labo
    bilan = pratiquer(mem, cle="ohm", pas=300)
    assert bilan["matiere"] == "ohm" and isinstance(bilan["adoptee"], bool)
    assert bilan["adoptee"] == (bilan["apres"] >= bilan["avant"] + 0.005)        # jamais d'adoption sans progrès
    assert mem.revisions()[0]["matiere"] == "ohm"
    assert pratiquer(mem, pas=200)["matiere"] != "orientation"                  # choisit seule sa matière


def test_apprendre_de_ses_propres_reponses(labo):
    from ia_aissa.autodidacte import apprendre_de_soi
    from ia_aissa.pensee import penser
    mem, _ = labo
    conclusion = {}
    penser("chkoun li bna lkoutoubia", mem, conclusion)
    assert conclusion["accord"] and conclusion["reponse"] == "Almohades (1121-1269)"
    assert apprendre_de_soi(mem, "chkoun li bna lkoutoubia", conclusion)
    assert any(c["source"] == "auto-apprentissage" for c in mem.corrections_de("histoire"))
    assert not apprendre_de_soi(mem, "bla bla bla", {"cle": "histoire", "reponse": "Almohades (1121-1269)",
                                                   "confiance": 0.5, "accord": True})        # pas assez sûre


def test_elle_se_corrige_avec_son_programme(labo):
    from ia_aissa.autodidacte import apprendre_du_programme, forme_originale
    mem, _ = labo
    assert forme_originale("photosynthese", "La photosynthèse des plantes") == "Photosynthèse"
    assert apprendre_du_programme(mem, "photosynthèse", "Sciences naturelles")
    assert mem.corrections_de("familles_sciences")[0]["bonne_reponse"] == "Sciences naturelles"
    assert not apprendre_du_programme(mem, "théorie des graphes", "Sciences formelles")     # déjà su


def test_fiscalite_locale_is_cotisation_minimale_et_tva_due():
    from ia_aissa import connaissances as K
    from ia_aissa.pensee import penser
    assert K.calculer_is_du(500_000, 2_000_000)["is_du"] == 100_000                      # IS 20 % > CM
    assert K.calculer_is_du(-50_000, 3_000_000)["is_du"] == 7_500                        # déficit : CM 0,25 %
    assert K.calculer_is_du(10_000, 100_000)["is_du"] == 3_000                           # plancher de 3 000 DH
    assert K.calculer_tva_due(50_000, 30_000)["tva_due"] == 20_000
    assert K.calculer_tva_due(20_000, 26_000)["credit_de_tva"] == 6_000
    assert "IS dû 7 500" in penser("déficit de 50 000 dh avec un chiffre d'affaires de 3 000 000 dh")[0]
    assert "IS dû 100 000" in penser("IS pour un bénéfice de 500 000 dh et un chiffre d affaires de 2 000 000 dh")[0]
    assert "crédit de TVA 6 000" in penser("tva collectée 20 000 dh, tva déductible 26 000 dh")[0]


def test_hygiene_de_la_memoire(labo):
    import json
    import time
    from ia_aissa.pensee import elaguer
    mem, _ = labo
    concept = lambda nom: json.dumps([{"nom": nom, "explication": "x"}])
    mem.garder_digestion("IA AISSA", "web", "Sciences naturelles", concept("Photosynthèse"), "", 0.5)
    mem.garder_digestion("IA AISSA", "web", "Sciences naturelles", concept("photosynthese"), "", 0.5)   # doublon
    mem.garder_digestion("Aissa", "mon livre", "Sciences humaines et gestion", concept("Budget"), "", 0.9)
    assert elaguer(mem)["dense"] is False and len(mem.digestions()) == 3                 # pas dense : rien ne bouge
    bilan = elaguer(mem, forcer=True)
    assert bilan["fusionnes"] == 1 and len(mem.digestions()) == 2
    premiere = min(d["id"] for d in mem.digestions())
    mem.definir_reglage(f"lecture_utilisee:{premiere}", "1")                             # utilisée pour répondre
    bilan = elaguer(mem, forcer=True, maintenant=time.time() + 8 * 86_400)              # 8 jours plus tard
    assert bilan["oublies"] == 0 and {d["source"] for d in mem.digestions()} == {"web", "mon livre"}
    mem.garder_digestion("IA AISSA", "web2", "Sciences naturelles", concept("Volcan"), "", 0.5)
    bilan = elaguer(mem, forcer=True, maintenant=time.time() + 8 * 86_400)
    assert bilan["oublies"] == 1 and "web2" not in {d["source"] for d in mem.digestions()}  # jamais utilisée : oubliée


def test_quarantaine_rumination_recursive_et_analogies(labo):
    from ia_aissa.autodidacte import (analogies_mathematiques, mettre_en_quarantaine, pertinence_programme,
                                      quarantaine, ruminer_recursif)
    mem, _ = labo
    assert pertinence_programme(ARTICLE_LOCAL) >= 0.15
    assert pertinence_programme("Zorglub frimousse zorglub frimousse quibble wobble quibble wobble") < 0.15
    mettre_en_quarantaine(mem, "Wikipédia — Zorglub", "zorglub", 0.02)
    assert quarantaine(mem)[0]["sujet"] == "zorglub"
    d, essais = ruminer_recursif(ARTICLE_LOCAL * 2, ARTICLE_LOCAL[:600])
    assert essais == 4 and d["concepts"]                                                 # 3 reformulations sous 75 %
    assert analogies_mathematiques(mem, "Photosynthèse", "Wikipédia — Photosynthèse") == 3
    titres = [i["titre"] for i in mem.idees_de("IA AISSA")]
    assert len(titres) == 3 and all("Photosynthèse" in t for t in titres)


def test_crises_financieres_synthetiques(labo):
    import numpy as np
    from ia_aissa.autodidacte import generer_crise, resoudre_crises
    mem, _ = labo
    rng = np.random.default_rng(3)
    crises = [generer_crise(rng) for _ in range(200)]
    assert any(c["ecart_pct"] >= 0.25 for c in crises) and any(c["ecart_pct"] < 0.1 for c in crises)
    bilan = resoudre_crises(mem, n=5, rng=np.random.default_rng(4))
    assert bilan["crises"] == 5 and 0 <= bilan["justes"] <= 5
    assert (bilan["pratique"] is None) == (bilan["justes"] == 5)                         # une erreur = s'exercer
    assert mem.reglages("crises:")


def test_memoire_vive_mesuree_et_allegee():
    from ia_aissa import ecole
    from ia_aissa.pensee import alleger, memoire_vive_mo
    ram = memoire_vive_mo()
    assert ram is None or ram > 10
    ecole.charger("tva")
    bilan = alleger(plafond=1)                       # plafond minuscule : elle doit s'alléger
    assert bilan["allege"] and not ecole._CACHE
    assert not alleger(plafond=10**9)["allege"]


def test_la_conversation_d_aissa_rejouee():
    """Les messages réels d'Aissa qui avaient mis IA AISSA en défaut."""
    from ia_aissa import connaissances as K
    from ia_aissa.espace import intention
    from ia_aissa.pensee import penser
    assert K.calculer_paie(K.brut_pour_net(6000))["salaire_net"] == 6000
    o = K.optimiser_salaire(6000)
    assert o["avec_indemnites"]["cout_employeur"] < o["tout_salaire"]["cout_employeur"]
    question = "SI UN SALAIRE DE 6000 NET QUEL SERA LE SALIRE BRUTE OPTIMSES LE MOINS CHERE EN CNSS ET IR SANS PERDRE AVANTAGES"
    r = penser(question)[0]
    assert "6 459.87" in r and "Optimisation légale" in r and "droits CNSS" in r       # honnête sur les avantages
    suite = penser("EXLIQUE PLUS", precedente=question)[0]
    assert suite.startswith("Je reprends ta question précédente") and "Comment j'ai raisonné" in suite
    assert intention("SIMULE UN BULLETIN DE PAIE CAS MAROC") is None                    # pas le bulletin de notes
    assert "7 273.65" in penser("SIMULE UN BULLETIN DE PAIE CAS MAROC")[0]
    assert "trompée" in penser("NON")[0] and "J'apprends en continu" in penser("TU DOIS APPRENDRE")[0]
    reponse, _, confiance = penser("bof")
    assert "pas sûre de comprendre" in reponse and confiance < 0.5                     # plus de réponse au hasard


def test_non_c_est_corrige_pendant_la_conversation(labo):
    from ia_aissa.pensee import correction_dans_la_conversation
    mem, _ = labo
    precedente = "paiement de la facture maroc telecom"
    merci = correction_dans_la_conversation("non, c'est 6145", mem,
                                            {"cle": "comptabilite", "reponse": "6125"}, precedente)
    assert "6145 Frais postaux" in merci
    assert mem.corrections_de("comptabilite")[0]["question"] == precedente
    assert correction_dans_la_conversation("non", mem, {"cle": "comptabilite"}, precedente) is None


def _pdf_de_test(texte):
    """Un vrai petit PDF avec du texte (sans dépendance supplémentaire)."""
    lignes = [texte[i:i + 90] for i in range(0, len(texte), 90)][:40]
    flux = "BT /F1 9 Tf 20 800 Td 11 TL " + " ".join(f"({l}) '" for l in lignes) + " ET"
    objets = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
              "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
              "/Resources << /Font << /F1 5 0 R >> >> >>",
              f"<< /Length {len(flux)} >>\nstream\n{flux}\nendstream",
              "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    sortie, positions = "%PDF-1.4\n", []
    for i, o in enumerate(objets, 1):
        positions.append(len(sortie.encode("latin-1")))
        sortie += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(sortie.encode("latin-1"))
    sortie += f"xref\n0 {len(objets) + 1}\n0000000000 65535 f \n" + "".join(f"{p:010d} 00000 n \n" for p in positions)
    sortie += f"trailer\n<< /Size {len(objets) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return sortie.encode("latin-1")


def test_ingestion_d_un_livre_pdf_sans_cle_api(labo, tmp_path, monkeypatch):
    import json
    import os
    import tempfile
    from ia_aissa.pensee import confirmation_ingestion, ingerer_pdf
    mem, _ = labo
    crees = []
    vrai = tempfile.NamedTemporaryFile
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", lambda **kw: crees.append(vrai(**kw)) or crees[-1])
    texte = ARTICLE_LOCAL.replace("ô", "o").replace("é", "e").replace("è", "e")
    bilan = ingerer_pdf(mem, "cours.pdf", _pdf_de_test(texte), fichier_json=tmp_path / "data" / "aissa_memoire.json")
    assert bilan["concepts"] >= 2 and bilan["entier"]
    assert not os.path.exists(crees[0].name)                                          # fichier temporaire supprimé
    archive = json.loads((tmp_path / "data" / "aissa_memoire.json").read_text(encoding="utf-8"))
    assert archive[0]["source"] == "cours.pdf" and archive[0]["concepts"]
    assert mem.digestions()[0]["utilisateur"] == "Aissa"                              # jamais oublié par l'élagage
    message = confirmation_ingestion(bilan)
    assert "Klit lktab kamel" in message and "supprimer le fichier source" in message
    import io
    import zipfile
    epub = io.BytesIO()
    with zipfile.ZipFile(epub, "w") as z:
        z.writestr("chap1.xhtml", "<html><body>" + "".join(f"<p>{p}.</p>" for p in ARTICLE_LOCAL.split(". ")) + "</body></html>")
    assert ingerer_pdf(mem, "livre.epub", epub.getvalue(), fichier_json=tmp_path / "e.json")["concepts"] >= 2
    with pytest.raises(ValueError, match="iwelah.com/fr/ocr-pdf"):
        ingerer_pdf(mem, "scan.pdf", _pdf_de_test(" "), fichier_json=tmp_path / "x.json")


def test_les_documents_de_chacun_restent_les_siens(labo):
    import json
    from ia_aissa.bibliotheque import chercher
    mem, _ = labo
    fiche = lambda nom: json.dumps([{"nom": nom, "explication": f"{nom} : marge brute et budget de l'entreprise"}])
    mem.garder_digestion("Aissa", "bilan société A", "Sciences humaines et gestion", fiche("Marge confidentielle A"), "", .5)
    mem.garder_digestion("Karim", "bilan société B", "Sciences humaines et gestion", fiche("Marge confidentielle B"), "", .5)
    mem.garder_digestion("IA AISSA", "Wikipédia", "Sciences humaines et gestion", fiche("Marge brute"), "", .5)
    vus = {l["source"] for l in chercher(mem, "marge brute budget", utilisateur="Aissa")}
    assert "bilan société A" in vus and "Wikipédia" in vus and "bilan société B" not in vus


class _BrouteurFactice:
    """Un brouteur sans réseau : chaque URL renvoie le PDF prévu, ou un refus."""
    def __init__(self, fichiers):
        self.fichiers = fichiers

    def telecharger(self, url, chemin):
        from ia_aissa.bibliotheque import ErreurBroutage
        contenu = self.fichiers[url]
        if isinstance(contenu, Exception):
            raise contenu
        if contenu == "403":
            raise ErreurBroutage("site.org refuse l'accès aux robots (403) : IA AISSA cherche ailleurs.")
        open(chemin, "wb").write(contenu)
        return len(contenu)


def test_livres_libres_recommandation_et_droits(labo, monkeypatch):
    from ia_aissa import livres_libres as LL
    from ia_aissa.bibliotheque import ErreurBroutage
    from ia_aissa.espace import intention
    mem, _ = labo
    assert intention("recommande moi des sites de livres gratuits en pdf") == "livres_libres"
    texte = LL.recommander("comptabilité management")
    assert "OpenStax" in texte and "management.org" in texte and "jamais de sites piratés" in texte
    assert LL.site_refuse("http://livre21.com/pf613.html") and not LL.site_refuse("https://openstax.org/x.pdf")
    propre = ARTICLE_LOCAL.replace("ô", "o").replace("é", "e").replace("è", "e")
    pirate = "Ce document est la propriete exclusive de Quelqu'un - 13 Septembre 2010. " + propre
    b = _BrouteurFactice({"https://libre.org/cours.pdf": _pdf_de_test(propre),
                          "https://libre.org/vole.pdf": _pdf_de_test(pirate)})
    bilan = LL.manger_livre(mem, b, "https://libre.org/cours.pdf", "Cours libre")
    assert bilan["concepts"] >= 2 and LL.deja_lu(mem, "https://libre.org/cours.pdf")
    with pytest.raises(ErreurBroutage, match="non autorisée"):
        LL.manger_livre(mem, b, "https://libre.org/vole.pdf")
    with pytest.raises(ErreurBroutage, match="ce site"):
        LL.manger_livre(mem, b, "http://livre21.com/LIVREF/F34/F034040.pdf")


def test_si_le_site_refuse_elle_cherche_ailleurs(labo, monkeypatch):
    from ia_aissa import livres_libres as LL
    mem, _ = labo
    propre = ARTICLE_LOCAL.replace("ô", "o").replace("é", "e").replace("è", "e")
    monkeypatch.setattr(LL, "catalogue_openstax", lambda b: [("Principles of Accounting", "https://a.org/refus.pdf"),
                                                             ("Principles of Management", "https://a.org/ok.pdf")])
    b = _BrouteurFactice({"https://a.org/refus.pdf": "403", "https://a.org/ok.pdf": _pdf_de_test(propre)})
    bilan = LL.repas_de_livre(mem, b)
    assert bilan["source"] == "OpenStax — Principles of Management" and "403" in bilan["refus"][0]
    assert LL.repas_de_livre(mem, b)["source"] is None                       # tout est lu ou refusé : rien à refaire


CGI_2021 = ("Article 98. Taux normal. Le taux normal de la taxe sur la valeur ajoutee est fixe a 20% pour toutes les "
            "operations non soumises a un taux reduit. Article 99. Taux reduits. Sont soumises a la taxe sur la valeur "
            "ajoutee au taux reduit de 7% avec droit a deduction les ventes d'eau et les produits pharmaceutiques. "
            "Sont soumises au taux de 14% les prestations de transport et l'energie electrique. ")
CGI_2026 = ("Article 98. Taux normal. Le taux normal de la taxe sur la valeur ajoutee est fixe a 20%. Article 99. Taux "
            "reduit. Sont soumises a la taxe sur la valeur ajoutee au taux reduit de 10% avec droit a deduction "
            "l'eau et l'energie electrique. Les taux de 7% et de 14% sont supprimes a compter du 1er janvier 2026. ")


def test_elle_repond_avec_ce_qu_elle_a_lu_dans_le_cgi(labo, tmp_path):
    from ia_aissa.lecture import examen_lecture, historique_examens
    from ia_aissa.pensee import ingerer_pdf, penser
    mem, _ = labo
    for nom, texte in (("CGI_2021.pdf", CGI_2021 * 2), ("CGI_2026.pdf", CGI_2026 * 2)):
        bilan = ingerer_pdf(mem, nom, _pdf_de_test(texte), "Bibliothèque", fichier_json=tmp_path / "m.json")
        assert bilan["passages_gardes"] >= 1
    reponse, etapes, _ = penser("QU IL EST LEVOLUSTION DE TVA AU MAROC DE 2021 A 2026", mem, utilisateur="Visiteur x")
    assert reponse.startswith("D'après mes lectures") and "CGI_2021.pdf" in reponse and "CGI_2026.pdf" in reponse
    assert "Connaissance intégrée" not in reponse                                   # ses lectures d'abord
    seule = penser("quel est le taux de tva sur l'energie electrique en 2026 ?", mem, utilisateur="Visiteur x")[0]
    assert "CGI_2026.pdf" in seule and "CGI_2021.pdf" not in seule and "10" in seule
    assert "Connaissance intégrée" in penser("évolution de l'IS", mem)[0]           # rien lu sur l'IS : elle le dit
    bilan = examen_lecture(mem, n=10)
    assert bilan["questions"] > 0 and bilan["score"] >= 0.5 and historique_examens(mem)


def test_un_scan_est_envoye_a_l_ocr_d_iwelah_puis_lu_en_texte(labo, tmp_path):
    from ia_aissa.pensee import GUIDE_OCR, ingerer_pdf, penser
    mem, _ = labo
    assert "https://iwelah.com/fr/ocr-pdf/" in GUIDE_OCR and "Redépose-le moi" in GUIDE_OCR
    texte_ocr = (CGI_2026 * 2).encode("utf-8")                            # le .txt téléchargé depuis IWELAH
    bilan = ingerer_pdf(mem, "CGI_2026_ocr.txt", texte_ocr, "Bibliothèque", fichier_json=tmp_path / "m.json")
    assert bilan["passages_gardes"] >= 1
    assert "CGI_2026_ocr.txt" in penser("taux de tva sur l'energie electrique", mem)[0]


def test_revision_non_adoptee_pas_relancee_sans_nouvelle_correction(tmp_path, monkeypatch):
    from ia_aissa import corrections as C
    from ia_aissa.memoire import Memoire
    mem = Memoire(f"sqlite:///{tmp_path / 'm.db'}")
    appels = []
    monkeypatch.setattr(C, "reviser", lambda m, cle: appels.append(cle) or {"matiere": cle, "adoptee": False})
    mem.ajouter_correction("Aissa", "pcm", "facture d'eau", "6125 Achats non stockés de matières et fournitures",
                           "utilisateur")
    assert C.a_reviser(mem) == ["pcm"]
    C.reviser_tout(mem)
    assert appels == ["pcm"] and C.a_reviser(mem) == []          # non adoptée : pas relancée à chaque message
    C.reviser_tout(mem)
    assert appels == ["pcm"]
    mem.ajouter_correction("Aissa", "pcm", "loyer du local", "6131 Locations et charges locatives", "utilisateur")
    assert C.a_reviser(mem) == ["pcm"]                           # une nouvelle correction : nouvelle tentative
    C.reviser_tout(mem)
    assert appels == ["pcm", "pcm"]
