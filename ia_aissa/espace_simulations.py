"""
L'espace des simulations : la liste, classée par type, dans la barre latérale ; chaque simulation produit un rapport
justifié (méthode, lois et articles, année de référence et taux appliqués), traçable et téléchargeable en PDF.
"""

import streamlit as st

from . import baremes as B
from . import connaissances as K
from . import simulations as S
from .rapports import journaliser, markdown, pdf, rapport

CATEGORIES = {
    "🧾 Fiscalité": ["IR (impôt sur le revenu)", "IS (impôt sur les sociétés)", "TVA due ou crédit de TVA",
                    "Auto-entrepreneur", "Douane à l'importation"],
    "👥 RH et paie": ["Paie (brut ↔ net)", "Heures supplémentaires", "Indemnité de licenciement", "Congés payés"],
    "📒 Comptabilité": ["Amortissement", "Seuil de rentabilité", "Prix de vente et marges"],
    "🏦 Banque": ["Crédit (échéancier)", "Capacité d'emprunt", "Épargne (intérêts composés)"],
    "💰 Finance": ["Investissement (VAN, TRI)", "Besoin en fonds de roulement (BFR)", "Trésorerie sur 12 mois",
                  "Risque de perte (Monte-Carlo)"],
    "🛠️ Technique": ["Consommation électrique", "Stock optimal (Wilson)"],
    "🏗️ Bâtiment": ["Béton (ciment, sable, gravier)", "Peinture", "Carrelage"],
}
CODE_TRAVAIL = "Loi n° 65-99 relative au Code du travail"
CNSS_AMO = ("CNSS : Dahir portant loi n° 1-72-184 du 27 juillet 1972 relatif au régime de sécurité sociale ; AMO : loi "
            "n° 65-00 portant code de la couverture médicale de base")


def dh(v, decimales=2):
    texte = f"{v:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return texte.removesuffix(",00") + " DH"


def pc(v):
    return f"{v * 100:.2f}".rstrip("0").rstrip(",.").replace(".", ",") + " %"


def barre_laterale():
    """La liste des simulations, classées par type, dans la barre latérale. Renvoie la simulation choisie."""
    with st.sidebar:
        st.markdown("## 🧮 Simulations")
        st.caption("Résultats justifiés : méthode, lois et articles, année et taux appliqués. Rapport PDF traçable.")
        for categorie, noms in CATEGORIES.items():
            st.markdown(f"**{categorie}**")
            for nom in noms:
                actif = st.session_state.get("simulation") == nom
                if st.button(("▶ " if actif else "") + nom, key=f"sim_{nom}", width="stretch",
                             type="primary" if actif else "secondary"):
                    st.session_state["simulation"] = nom
                    st.rerun()
        if st.session_state.get("simulation") and st.button("✖ Fermer la simulation", width="stretch"):
            st.session_state.pop("simulation")
            st.rerun()
    return st.session_state.get("simulation")


def categorie_de(nom):
    return next(c for c, noms in CATEGORIES.items() if nom in noms)


def afficher(nom, memoire):
    """La simulation choisie : saisie, rapport justifié, tableau, et téléchargement du PDF."""
    st.markdown(f"### {nom}")
    r = construire(nom, memoire)
    if r is None:
        return
    st.markdown(markdown(r), unsafe_allow_html=True)
    if r.get("tableau") is not None:
        st.dataframe(r["tableau"], hide_index=True, width="stretch", height=260)
    if st.download_button("📄 Télécharger le rapport PDF", pdf(r), f"{r['numero']}.pdf", "application/pdf",
                          key=f"pdf_{nom}"):
        journaliser(memoire, r)


def construire(nom, memoire):
    c = st.columns(3)
    if nom == "IR (impôt sur le revenu)":
        annees = B.annees_couvertes("ir", memoire)
        annee = c[0].selectbox("Année de référence", annees[::-1], key="ir_annee")
        revenu = c[1].number_input("Revenu net imposable annuel (DH)", 0.0, value=120_000.0, step=5_000.0, key="ir_rev")
        try:
            x = B.ir_annee(revenu, annee, memoire)
        except ValueError as e:
            st.warning(str(e))
            return None
        p = x["periode"]
        tranches = " ; ".join(("au-delà" if t[0] == float("inf") else f"jusqu'à {dh(t[0], 0)}") + f" : {pc(t[1])}"
                              + (f" (− {dh(t[2], 0)})" if t[2] else "") for t in p["bareme"])
        return rapport(nom, categorie_de(nom), {"Année de référence": annee, "Revenu net imposable annuel": dh(revenu)},
                       {"Taux marginal": pc(x["taux_marginal"]), "Somme à déduire": dh(x["somme_a_deduire"]),
                        "IR annuel": dh(x["ir_annuel"]), "IR mensuel": dh(x["ir_mensuel"]),
                        "Taux moyen": pc(x["taux_moyen"])},
                       [f"Barème {annee} (période {p['de']}–{p['a']}) : {tranches}.",
                        f"IR = revenu × taux marginal − somme à déduire = {dh(revenu)} × {pc(x['taux_marginal'])} − "
                        f"{dh(x['somme_a_deduire'])} = {dh(x['ir_annuel'])}.",
                        "La somme à déduire évite de taxer tout le revenu au taux le plus haut : chaque tranche n'est "
                        "imposée qu'à son propre taux."],
                       [p["loi"], *(f"Source consultée : {s}" for s in p["sources"]), f"Vérifié le {B.VERIFIE_LE}."],
                       annee, remarques=["Barèmes antérieurs à 2010 non encodés faute de source vérifiée : "
                                         "l'administrateur peut les ajouter à partir du Bulletin officiel."])
    if nom == "IS (impôt sur les sociétés)":
        p = B.periode("is", 2026)
        benefice = c[0].number_input("Résultat fiscal (DH)", value=500_000.0, step=10_000.0, key="is_ben")
        produits = c[1].number_input("Produits / chiffre d'affaires HT (DH)", 0.0, value=3_000_000.0, step=100_000.0,
                                     key="is_prod")
        secteur = c[2].selectbox("Secteur", ["Droit commun", "Établissements de crédit et assurances"], key="is_sect")
        x = K.calculer_is_du(benefice, produits)
        if secteur != "Droit commun":                       # CGI art. 19 : taux de 40 % pour ce secteur
            x["taux"] = 0.40
            x["is"] = round(max(benefice, 0) * 0.40, 2)
            x["is_du"] = max(x["is"], x["cotisation_minimale"])
            x["retenu"] = "cotisation minimale" if x["cotisation_minimale"] > x["is"] else "IS proportionnel"
        return rapport(nom, categorie_de(nom), {"Année de référence": 2026, "Secteur": secteur,
                                                "Résultat fiscal": dh(benefice), "Produits": dh(produits)},
                       {"Taux d'IS": pc(x["taux"]), "IS proportionnel": dh(x["is"]),
                        "Cotisation minimale": dh(x["cotisation_minimale"]), "IS dû": dh(x["is_du"]),
                        "Retenu": x["retenu"]},
                       [f"Taux 2026 : {pc(0.20)} si bénéfice < 100 millions DH, {pc(0.35)} au-delà, {pc(0.40)} "
                        "pour les banques et assurances.",
                        f"IS proportionnel = {dh(max(benefice, 0))} × {pc(x['taux'])} = {dh(x['is'])}.",
                        f"Cotisation minimale = max(3 000 DH ; 0,25 % × {dh(produits)}) = {dh(x['cotisation_minimale'])}.",
                        f"IS dû = le plus élevé des deux = {dh(x['is_du'])}."],
                       [p["loi"], p["cotisation_minimale"]["loi"] + " (cotisation minimale)",
                        *(f"Source consultée : {s}" for s in p["sources"]), f"Vérifié le {B.VERIFIE_LE}."],
                       2026, remarques=["Années 2023-2025 : barème de transition (les sources divergent sur 2025), "
                                        "non encodé.", "Régimes particuliers non appliqués : sociétés exportatrices, zones "
                                        "d'accélération industrielle, Casablanca Finance City, sociétés nouvellement "
                                        "créées (exonération de cotisation minimale), entreprises agricoles."])
    if nom == "TVA due ou crédit de TVA":
        annee = c[0].selectbox("Année de référence", B.annees_couvertes("tva")[::-1], key="tva_annee")
        coll = c[1].number_input("TVA collectée sur les ventes", 0.0, value=50_000.0, key="tva_coll")
        ded = c[2].number_input("TVA déductible sur les achats", 0.0, value=30_000.0, key="tva_ded")
        p = B.periode("tva", annee)
        x = K.calculer_tva_due(coll, ded)
        return rapport(nom, categorie_de(nom), {"Année de référence": annee, "TVA collectée": dh(coll),
                                                "TVA déductible": dh(ded)},
                       {"TVA due": dh(x["tva_due"]), "Crédit de TVA": dh(x["credit_de_tva"])},
                       [f"Taux en vigueur en {annee} : normal {pc(p['taux']['normal'])} ; réduits : "
                        + ", ".join(pc(t) if isinstance(t, float) else t for t in p["taux"]["réduits"]) + ".",
                        f"TVA due = collectée − déductible = {dh(coll)} − {dh(ded)} = {dh(coll - ded)}.",
                        "Si le résultat est négatif, c'est un crédit de TVA reportable sur les déclarations suivantes."],
                       [p["loi"], "CGI, art. 101 (droit à déduction)", *(f"Source consultée : {s}" for s in p["sources"]),
                        f"Vérifié le {B.VERIFIE_LE}."], annee, remarques=[p["remarque"]])
    if nom == "Auto-entrepreneur":
        ca = c[0].number_input("Chiffre d'affaires annuel (DH)", 0.0, value=150_000.0, step=10_000.0, key="ae_ca")
        act = c[1].radio("Activité", ["services", "commerce"], key="ae_act")
        x = S.auto_entrepreneur(ca, act)
        return rapport(nom, categorie_de(nom), {"Activité": x["activite"], "Chiffre d'affaires": dh(ca)},
                       {"Impôt": dh(x["impot"]), "Taux": pc(x["taux"]), "Plafond": dh(x["plafond"], 0),
                        "Plafond dépassé": "oui" if x["depasse_le_plafond"] else "non"},
                       [f"Impôt = chiffre d'affaires × {pc(x['taux'])} = {dh(x['impot'])}.",
                        "Taux : 0,5 % (commerce, industrie, artisanat), 1 % (services)."],
                       ["Loi n° 114-13 relative au statut de l'auto-entrepreneur", "CGI, art. 73 (taux de l'IR)",
                        f"Taux et plafonds de la base de connaissances (mise à jour {K.MISE_A_JOUR})."], 2026)
    if nom == "Douane à l'importation":
        caf = c[0].number_input("Valeur CAF (DH)", 0.0, value=100_000.0, step=5_000.0, key="dou_caf")
        di = c[1].number_input("Droit d'importation (%)", 0.0, 200.0, 17.5, key="dou_di") / 100
        x = K.calculer_droits_import(caf, di)
        return rapport(nom, categorie_de(nom), {"Valeur CAF": dh(caf), "Droit d'importation": pc(di)},
                       {"Droit d'importation": dh(x["droit_importation"]), "TVA à l'import": dh(x["tva_import"]),
                        "Total droits et taxes": dh(x["total_droits_et_taxes"]),
                        "Coût dédouané": dh(x["cout_total_dedouane"])},
                       [f"Droit = valeur CAF × taux = {dh(caf)} × {pc(di)} = {dh(x['droit_importation'])}.",
                        f"TVA à l'import = (valeur CAF + droit) × 20 % = {dh(x['tva_import'])}."],
                       ["Code des douanes et impôts indirects (dahir n° 1-77-339) et tarif douanier de l'ADII",
                        "CGI : TVA à l'importation", x["remarque"]], 2026)
    if nom == "Paie (brut ↔ net)":
        sens = c[0].radio("Je connais", ["le brut", "le net"], key="paie_sens2")
        montant = c[1].number_input("Montant mensuel (DH)", 0.0, value=8000.0, step=500.0, key="paie_mont2")
        brut = K.brut_pour_net(montant) if sens == "le net" else montant
        x = K.calculer_paie(brut)
        base = min(brut, K.PLAFOND_CNSS_MENSUEL)
        return rapport(nom, categorie_de(nom), {"Année de référence": 2026, "Saisie": f"{dh(montant)} ({sens})"},
                       {"Salaire brut": dh(brut), "CNSS salarié": dh(x["cnss_salarie"]), "AMO salarié": dh(x["amo_salarie"]),
                        "Frais professionnels": dh(x["frais_professionnels"]), "Net imposable": dh(x["net_imposable"]),
                        "IR": dh(x["ir"]), "Salaire net": dh(x["salaire_net"]),
                        "Charges patronales": dh(x["charges_patronales"]),
                        "Coût employeur": dh(brut + x["charges_patronales"])},
                       [f"CNSS = {pc(K.CNSS_SALARIE)} × min(brut ; 6 000 DH) = {pc(K.CNSS_SALARIE)} × {dh(base)} = "
                        f"{dh(x['cnss_salarie'])}.",
                        f"AMO = {pc(K.AMO_SALARIE)} × brut = {dh(x['amo_salarie'])}.",
                        "Frais professionnels : 35 % du brut si le brut annuel ≤ 78 000 DH, sinon 25 %, plafonnés à "
                        f"35 000 DH par an → {dh(x['frais_professionnels'])} par mois.",
                        f"Net imposable = brut − CNSS − AMO − frais professionnels = {dh(x['net_imposable'])} ; IR mensuel "
                        f"selon le barème 2026 ÷ 12 = {dh(x['ir'])}.",
                        f"Net = brut − CNSS − AMO − IR = {dh(x['salaire_net'])}."]
                       + (["Brut retrouvé à partir du net par dichotomie (essais successifs jusqu'au centime)."]
                          if sens == "le net" else []),
                       [CNSS_AMO, "CGI, art. 59 (frais professionnels) et art. 73 (barème de l'IR, LF n° 60-24)",
                        f"Taux de la base de connaissances, vérifiés le {K.MISE_A_JOUR}."], 2026,
                       remarques=[x["remarque"]])
    if nom == "Crédit (échéancier)":
        capital = c[0].number_input("Capital (DH)", 0.0, value=200_000.0, step=10_000.0, key="cr_cap")
        taux = c[1].number_input("Taux annuel (%)", 0.0, 30.0, 5.0, 0.1, key="cr_taux") / 100
        ans = c[2].number_input("Durée (ans)", 1, 30, 10, key="cr_ans")
        x = S.echeancier_credit(capital, taux, ans * 12)
        return rapport(nom, categorie_de(nom), {"Capital": dh(capital), "Taux nominal annuel": pc(taux),
                                                "Durée": f"{ans} ans ({ans * 12} mois)"},
                       {"Mensualité": dh(x["mensualite"]), "Coût des intérêts": dh(x["cout_total"]),
                        "Total remboursé": dh(x["total_rembourse"])},
                       ["Mensualité constante M = C × t / (1 − (1 + t)^−n), avec t = taux annuel ÷ 12 et n = nombre de mois.",
                        f"M = {dh(capital)} × {taux / 12:.6f} / (1 − (1 + {taux / 12:.6f})^−{ans * 12}) = {dh(x['mensualite'])}.",
                        "Chaque mois : intérêts = capital restant × t ; capital remboursé = M − intérêts."],
                       ["Formule de l'annuité constante (mathématiques financières)",
                        "Loi n° 31-08 édictant des mesures de protection du consommateur (information sur le crédit, TEG)"],
                       remarques=["Hors assurance, frais de dossier et garanties : le taux effectif global (TEG) de la "
                                  "banque est plus élevé que le taux nominal."], tableau=x["tableau"])
    if nom == "Épargne (intérêts composés)":
        versement = c[0].number_input("Versement mensuel (DH)", 0.0, value=500.0, step=100.0, key="ep_ver")
        taux = c[1].number_input("Rendement annuel (%)", 0.0, 20.0, 4.0, 0.1, key="ep_taux") / 100
        ans = c[2].number_input("Durée (ans)", 1, 50, 10, key="ep_ans")
        x = S.epargne(versement, taux, ans)
        return rapport(nom, categorie_de(nom), {"Versement mensuel": dh(versement), "Rendement annuel": pc(taux),
                                                "Durée": f"{ans} ans"},
                       {"Capital final": dh(x["capital_final"]), "Total versé": dh(x["total_verse"]),
                        "Intérêts gagnés": dh(x["interets"])},
                       ["Chaque mois : capital = capital × (1 + rendement ÷ 12) + versement.",
                        "Les intérêts produisent à leur tour des intérêts (capitalisation mensuelle)."],
                       ["Formule des intérêts composés (mathématiques financières)"],
                       remarques=["Rendement supposé constant, avant impôt sur les produits de placement."],
                       tableau=x["tableau"])
    if nom == "Investissement (VAN, TRI)":
        investissement = c[0].number_input("Investissement (DH)", 0.0, value=100_000.0, step=10_000.0, key="inv_i")
        taux = c[1].number_input("Taux d'actualisation (%)", 0.0, 50.0, 8.0, 0.5, key="inv_t") / 100
        flux = c[2].text_input("Flux annuels (DH, séparés par ;)", "30000; 40000; 50000; 20000", key="inv_f")
        try:
            liste = [float(v.replace(" ", "").replace(",", ".")) for v in flux.split(";") if v.strip()]
        except ValueError:
            st.error("Écris les flux comme ceci : 30000; 40000; 50000")
            return None
        x = S.rentabilite_investissement(investissement, liste, taux)
        return rapport(nom, categorie_de(nom), {"Investissement": dh(investissement), "Taux d'actualisation": pc(taux),
                                                "Flux": " ; ".join(dh(f) for f in liste)},
                       {"VAN": dh(x["van"]), "TRI": pc(x["tri"]) if x["tri"] is not None else "non calculable",
                        "Délai de récupération": f"{x['delai_recuperation_ans']} an(s)", "Décision": x["decision"]},
                       ["VAN = −I + Σ Fₜ / (1 + a)ᵗ : la valeur d'aujourd'hui des flux futurs, moins l'investissement.",
                        "TRI = le taux qui annule la VAN (trouvé par dichotomie) ; projet intéressant si TRI > taux exigé.",
                        "Délai de récupération = temps pour que les flux cumulés remboursent l'investissement."],
                       ["Méthodes d'évaluation des investissements (finance d'entreprise)"])
    if nom == "Seuil de rentabilité":
        prix = c[0].number_input("Prix de vente unitaire", 0.0, value=100.0, key="sr_p")
        cv = c[1].number_input("Coût variable unitaire", 0.0, value=60.0, key="sr_cv")
        cf = c[2].number_input("Charges fixes annuelles", 0.0, value=200_000.0, step=10_000.0, key="sr_cf")
        x = K.seuil_rentabilite(prix, cv, cf)
        if x.get("seuil_en_quantite") is None:
            st.error(x["remarque"])
            return None
        return rapport(nom, categorie_de(nom), {"Prix unitaire": dh(prix), "Coût variable unitaire": dh(cv),
                                                "Charges fixes": dh(cf)},
                       {"Marge sur coût variable unitaire": dh(x["marge_sur_cout_variable_unitaire"]),
                        "Seuil (unités)": f"{x['seuil_en_quantite']:,.0f}".replace(",", " "),
                        "Seuil (chiffre d'affaires)": dh(x["seuil_en_chiffre_affaires"])},
                       ["Marge unitaire = prix − coût variable.", "Seuil (quantité) = charges fixes ÷ marge unitaire.",
                        "Seuil (CA) = quantité × prix : en dessous, l'entreprise perd de l'argent."],
                       ["Méthode du coût variable (comptabilité analytique)"])
    if nom == "Prix de vente et marges":
        cout = c[0].number_input("Coût de revient (DH)", 0.0, value=80.0, key="pv_c")
        base = c[1].radio("Je fixe", ["un taux de marge (sur coût)", "un taux de marque (sur prix)"], key="pv_b")
        taux = c[2].number_input("Taux (%)", 0.0, 99.0, 25.0, key="pv_t") / 100
        x = S.prix_de_vente(cout, taux_de_marque=taux) if "marque" in base else S.prix_de_vente(cout, taux_marge_sur_cout=taux)
        return rapport(nom, categorie_de(nom), {"Coût de revient": dh(cout), "Base": f"{base} : {pc(taux)}"},
                       {"Prix HT": dh(x["prix_ht"]), "Prix TTC (TVA 20 %)": dh(x["prix_ttc"]), "Marge": dh(x["marge"]),
                        "Taux de marge": pc(x["taux_de_marge"]), "Taux de marque": pc(x["taux_de_marque"])},
                       ["Taux de marge = marge ÷ coût de revient ; taux de marque = marge ÷ prix de vente HT.",
                        "Prix HT = coût × (1 + taux de marge) ou coût ÷ (1 − taux de marque)."],
                       ["Définitions du Code général de normalisation comptable (CGNC) et de la gestion commerciale",
                        "CGI, art. 98 et 99 (TVA au taux normal de 20 %)"], 2026)
    if nom == "Trésorerie sur 12 mois":
        solde = c[0].number_input("Solde de départ (DH)", value=50_000.0, step=5_000.0, key="tr_s")
        enc = c[1].text_input("Encaissements (;)", "80000; 60000; 90000; 70000; 85000; 60000; 95000; 70000; 80000; "
                                                   "90000; 75000; 100000", key="tr_e")
        dec = c[2].text_input("Décaissements (;)", "90000; 85000; 80000; 75000; 80000; 85000; 80000; 90000; 75000; "
                                                   "80000; 85000; 80000", key="tr_d")
        try:
            lire = lambda t: [float(v.replace(" ", "").replace(",", ".")) for v in t.split(";") if v.strip()]
            x = S.tresorerie(solde, lire(enc), lire(dec))
        except ValueError:
            st.error("Écris les montants comme ceci : 80000; 60000; 90000")
            return None
        return rapport(nom, categorie_de(nom), {"Solde de départ": dh(solde), "Encaissements": enc, "Décaissements": dec},
                       {"Solde final": dh(x["solde_final"]), "Solde le plus bas": dh(x["solde_minimum"]),
                        "Premier mois à découvert": x["premier_mois_a_decouvert"] or "aucun"},
                       ["Solde de fin de mois = solde précédent + encaissements − décaissements.",
                        "Un solde négatif signale un besoin de financement (découvert, facilité de caisse)."],
                       ["Plan de trésorerie (gestion financière à court terme)"], tableau=x["tableau"])
    if nom == "Amortissement":
        valeur = c[0].number_input("Valeur d'acquisition HT (DH)", 0.0, value=100_000.0, step=5_000.0, key="am_v")
        ans = c[1].number_input("Durée (ans)", 1, 40, 5, key="am_n")
        methode = c[2].radio("Méthode", ["lineaire", "degressif"], format_func=str.capitalize, key="am_m")
        x = S.amortissement(valeur, ans, methode)
        etapes = (["Dotation annuelle = valeur ÷ durée."] if methode == "lineaire" else
                  [f"Taux dégressif = (1 ÷ durée) × coefficient = (1 ÷ {ans}) × {x['coefficient']} = {pc(x['taux'])}.",
                   "Coefficients : 1,5 (3 ou 4 ans), 2 (5 ou 6 ans), 3 (plus de 6 ans).",
                   "Dotation = valeur nette comptable × taux ; passage au linéaire dès qu'il donne davantage."])
        return rapport(nom, categorie_de(nom), {"Valeur": dh(valeur), "Durée": f"{ans} ans", "Méthode": methode},
                       {"Première dotation": dh(x["tableau"]["Dotation"].iloc[0]),
                        "Total amorti": dh(x["tableau"]["Dotation"].sum())},
                       etapes, ["CGI, art. 10 (dotations aux amortissements déductibles)",
                                "Code général de normalisation comptable (CGNC)"], 2026, tableau=x["tableau"])
    if nom == "Stock optimal (Wilson)":
        d = c[0].number_input("Demande annuelle (unités)", 0.0, value=12_000.0, key="st_d")
        cp = c[1].number_input("Coût d'une commande (DH)", 0.0, value=500.0, key="st_cp")
        cs = c[2].number_input("Coût de stockage / unité / an", 0.01, value=2.0, key="st_cs")
        x = K.quantite_wilson(d, cp, cs)
        return rapport(nom, categorie_de(nom), {"Demande annuelle": d, "Coût d'une commande": dh(cp),
                                                "Coût de stockage unitaire": dh(cs)},
                       {k.replace("_", " ").capitalize(): v for k, v in x.items()},
                       ["Quantité économique Q* = √(2 × demande × coût de commande ÷ coût de stockage unitaire).",
                        "À Q*, le coût total de passation des commandes égale le coût de possession du stock."],
                       ["Modèle de Wilson (gestion des stocks)"])
    if nom == "Risque de perte (Monte-Carlo)":
        ca = st.slider("Chiffre d'affaires possible (DH)", 0, 5_000_000, (800_000, 1_200_000), 50_000, key="mc_ca")
        tcv = st.slider("Coûts variables (% du chiffre d'affaires)", 0, 100, (55, 70), key="mc_tcv")
        cf = st.number_input("Charges fixes (DH)", 0.0, value=350_000.0, step=10_000.0, key="mc_cf")
        x = S.risque_monte_carlo(ca[0], ca[1], tcv[0] / 100, tcv[1] / 100, cf)
        return rapport(nom, categorie_de(nom), {"Chiffre d'affaires": f"{dh(ca[0], 0)} à {dh(ca[1], 0)}",
                                                "Coûts variables": f"{tcv[0]} % à {tcv[1]} %", "Charges fixes": dh(cf)},
                       {"Probabilité de perte": pc(x["probabilite_de_perte"]), "Résultat moyen": dh(x["resultat_moyen"]),
                        "Fourchette à 90 %": f"{dh(x['p5'], 0)} à {dh(x['p95'], 0)}"},
                       [f"{x['simulations']:,} scénarios tirés au hasard (lois uniformes) dans les fourchettes saisies."
                        .replace(",", " "),
                        "Résultat de chaque scénario = CA × (1 − taux de coûts variables) − charges fixes.",
                        "Probabilité de perte = part des scénarios où le résultat est négatif."],
                       ["Méthode de Monte-Carlo (statistiques, gestion des risques)"])
    if nom == "Heures supplémentaires":
        taux = c[0].number_input("Salaire horaire (DH)", 0.0, value=20.0, key="hs_t")
        hj = c[1].number_input("Heures 6 h – 21 h (jours ouvrables)", 0.0, value=10.0, key="hs_j")
        hn = c[2].number_input("Heures 21 h – 6 h (jours ouvrables)", 0.0, value=0.0, key="hs_n")
        c2 = st.columns(3)
        rj = c2[0].number_input("Heures 6 h – 21 h (repos hebdo.)", 0.0, value=0.0, key="hs_rj")
        rn = c2[1].number_input("Heures 21 h – 6 h (repos hebdo.)", 0.0, value=0.0, key="hs_rn")
        x = S.heures_supplementaires(taux, hj, hn, rj, rn)
        return rapport(nom, categorie_de(nom), {"Salaire horaire": dh(taux), "Heures": f"{hj + hn + rj + rn:g}"},
                       {"Montant des heures supplémentaires": dh(x["total"])},
                       ["Montant = heures × salaire horaire × (1 + majoration).",
                        "Majorations : 25 % de 6 h à 21 h et 50 % de 21 h à 6 h les jours ouvrables ; 50 % et 100 % le "
                        "jour du repos hebdomadaire."],
                       [f"{CODE_TRAVAIL}, art. 196 à 204 (heures supplémentaires), notamment art. 201 (majorations)"],
                       tableau=x["tableau"])
    if nom == "Indemnité de licenciement":
        sh = c[0].number_input("Salaire horaire moyen (DH)", 0.0, value=50.0, key="il_s",
                               help="Moyenne des 52 dernières semaines (salaire mensuel ÷ 191 heures environ).")
        ans = c[1].number_input("Ancienneté (années)", 0.0, 60.0, 12.0, 0.5, key="il_a")
        x = S.indemnite_licenciement(sh, ans)
        return rapport(nom, categorie_de(nom), {"Salaire horaire moyen": dh(sh), "Ancienneté": f"{ans:g} ans"},
                       {"Heures dues": f"{x['heures']:g} h", "Indemnité de licenciement": dh(x["indemnite"])},
                       ["96 heures de salaire par année pour les 5 premières années, 144 h de la 6e à la 10e, 192 h de "
                        "la 11e à la 15e, 240 h au-delà.", "Indemnité = heures dues × salaire horaire moyen."],
                       [f"{CODE_TRAVAIL}, art. 52 et 53 (indemnité de licenciement)"],
                       remarques=["Non due en cas de faute grave ; des dommages-intérêts pour licenciement abusif "
                                  "(art. 41) peuvent s'ajouter.", "Exonération d'IR dans les limites de l'art. 57 du CGI."],
                       tableau=x["tableau"])
    if nom == "Congés payés":
        mois = c[0].number_input("Mois de service dans l'année", 0, 12, 12, key="cp_m")
        anc = c[1].number_input("Ancienneté (années)", 0, 60, 10, key="cp_a")
        x = S.conges_payes(mois, anc)
        return rapport(nom, categorie_de(nom), {"Mois de service": mois, "Ancienneté": f"{anc} ans"},
                       {"Jours ouvrables de congé": f"{x['jours']:g}"},
                       [f"Base : 1,5 jour par mois de service = {x['base']:g} jours.",
                        f"Ancienneté : 1,5 jour par période de 5 ans = {x['anciennete']:g} jours.",
                        "Total plafonné à 30 jours ouvrables."],
                       [f"{CODE_TRAVAIL}, art. 231 (durée du congé) et art. 241 (majoration pour ancienneté)"],
                       remarques=["Salariés de moins de 18 ans : 2 jours par mois (art. 231)."])
    if nom == "Capacité d'emprunt":
        revenu = c[0].number_input("Revenu net mensuel (DH)", 0.0, value=15_000.0, step=500.0, key="ce_r")
        charges = c[1].number_input("Crédits en cours (mensualités, DH)", 0.0, value=0.0, key="ce_c")
        taux = c[2].number_input("Taux annuel (%)", 0.0, 20.0, 5.0, 0.1, key="ce_t") / 100
        c2 = st.columns(3)
        ans = c2[0].number_input("Durée (ans)", 1, 30, 20, key="ce_a")
        endettement = c2[1].number_input("Taux d'endettement retenu (%)", 10, 60, 40, key="ce_e") / 100
        x = S.capacite_emprunt(revenu, charges, taux, ans * 12, endettement)
        return rapport(nom, categorie_de(nom), {"Revenu net mensuel": dh(revenu), "Crédits en cours": dh(charges),
                                                "Taux": pc(taux), "Durée": f"{ans} ans",
                                                "Taux d'endettement": pc(endettement)},
                       {"Mensualité maximale": dh(x["mensualite_max"]), "Capital empruntable": dh(x["capital_max"])},
                       ["Mensualité maximale = revenu × taux d'endettement − mensualités en cours.",
                        "Capital = M × (1 − (1 + t)^−n) / t (annuité constante inversée)."],
                       ["Usage bancaire : un taux d'endettement d'environ 40 % du revenu est couramment retenu "
                        "(chaque banque fixe sa propre limite)", "Loi n° 31-08 (protection du consommateur, crédit)"])
    if nom == "Besoin en fonds de roulement (BFR)":
        stocks = c[0].number_input("Stocks (DH)", 0.0, value=100_000.0, step=10_000.0, key="bfr_s")
        clients = c[1].number_input("Créances clients (DH)", 0.0, value=200_000.0, step=10_000.0, key="bfr_c")
        fourn = c[2].number_input("Dettes fournisseurs (DH)", 0.0, value=120_000.0, step=10_000.0, key="bfr_f")
        ca = st.number_input("Chiffre d'affaires annuel HT (DH)", 0.0, value=1_800_000.0, step=100_000.0, key="bfr_ca")
        x = S.besoin_fonds_roulement(stocks, clients, fourn, ca)
        return rapport(nom, categorie_de(nom), {"Stocks": dh(stocks), "Créances clients": dh(clients),
                                                "Dettes fournisseurs": dh(fourn), "Chiffre d'affaires": dh(ca)},
                       {"BFR": dh(x["bfr"]), "BFR en jours de CA": f"{x['jours_de_ca']} jours"},
                       ["BFR = stocks + créances clients − dettes fournisseurs.", "En jours de CA = BFR ÷ CA × 360."],
                       ["Analyse fonctionnelle du bilan (CGNC)", "Loi n° 69-21 sur les délais de paiement (60 jours en "
                        "principe, 120 jours au plus par accord) : elle influe sur les créances et les dettes"])
    if nom == "Consommation électrique":
        p = c[0].number_input("Puissance de l'appareil (W)", 0.0, value=2000.0, step=100.0, key="el_p")
        h = c[1].number_input("Heures par jour", 0.0, 24.0, 3.0, key="el_h")
        j = c[2].number_input("Jours", 1, 366, 30, key="el_j")
        prix = st.number_input("Prix du kWh (DH, voir votre facture)", 0.0, value=1.2, step=0.05, key="el_px")
        x = S.consommation_electrique(p, h, j, prix)
        return rapport(nom, categorie_de(nom), {"Puissance": f"{p:g} W", "Utilisation": f"{h:g} h/jour pendant {j} jours",
                                                "Prix du kWh": dh(prix)},
                       {"Énergie": f"{x['kwh']:g} kWh", "Coût": dh(x["cout"])},
                       ["Énergie (kWh) = puissance (kW) × heures d'utilisation.", "Coût = kWh × prix du kWh."],
                       ["Physique : énergie = puissance × temps"],
                       remarques=["Le prix du kWh dépend des tranches de consommation de votre distributeur : prenez "
                                  "celui de votre facture."])
    if nom == "Béton (ciment, sable, gravier)":
        lo = c[0].number_input("Longueur (m)", 0.0, value=5.0, key="be_l")
        la = c[1].number_input("Largeur (m)", 0.0, value=4.0, key="be_w")
        ep = c[2].number_input("Épaisseur (m)", 0.0, value=0.15, step=0.01, key="be_e")
        dosage = st.number_input("Dosage en ciment (kg/m³)", 150, 500, 350, 25, key="be_d")
        x = S.beton(lo, la, ep, dosage)
        return rapport(nom, categorie_de(nom), {"Dimensions": f"{lo:g} × {la:g} × {ep:g} m", "Dosage": f"{dosage} kg/m³"},
                       {"Volume": f"{x['volume_m3']:g} m³", "Ciment": f"{x['ciment_kg']:g} kg ({x['sacs_ciment_50kg']} sacs de 50 kg)",
                        "Sable": f"{x['sable_m3']:g} m³", "Gravier": f"{x['gravier_m3']:g} m³", "Eau": f"{x['eau_litres']:g} L"},
                       ["Volume = longueur × largeur × épaisseur.",
                        "Pour 1 m³ de béton courant : environ 400 L de sable, 800 L de gravier et 175 L d'eau."],
                       ["Dosages usuels de chantier pour un béton courant (à adapter à l'étude de structure)"],
                       remarques=["Pour un ouvrage porteur, suivez les prescriptions de l'ingénieur ou du bureau d'études."])
    if nom == "Peinture":
        surface = c[0].number_input("Surface à peindre (m²)", 0.0, value=60.0, key="pe_s")
        couches = c[1].number_input("Couches", 1, 5, 2, key="pe_c")
        rendement = c[2].number_input("Rendement (m²/L, voir le pot)", 1.0, value=10.0, key="pe_r")
        x = S.peinture(surface, couches, rendement)
        return rapport(nom, categorie_de(nom), {"Surface": f"{surface:g} m²", "Couches": couches,
                                                "Rendement": f"{rendement:g} m²/L"},
                       {"Peinture nécessaire": f"{x['litres']:g} L"},
                       ["Litres = surface × couches ÷ rendement."], ["Rendement indiqué par le fabricant sur le pot"])
    if nom == "Carrelage":
        surface = c[0].number_input("Surface (m²)", 0.0, value=20.0, key="ca_s")
        lo = c[1].number_input("Longueur du carreau (cm)", 1.0, value=60.0, key="ca_l")
        la = c[2].number_input("Largeur du carreau (cm)", 1.0, value=60.0, key="ca_w")
        x = S.carrelage(surface, lo, la)
        return rapport(nom, categorie_de(nom), {"Surface": f"{surface:g} m²", "Carreau": f"{lo:g} × {la:g} cm"},
                       {"Surface à commander (+10 % de chutes)": f"{x['surface_a_commander_m2']:g} m²",
                        "Nombre de carreaux": x["carreaux"]},
                       ["Surface à commander = surface × 1,10 (chutes et casse).",
                        "Carreaux = surface à commander ÷ surface d'un carreau, arrondi au-dessus."],
                       ["Pratique de chantier : 10 % de marge pour la pose droite (15 % en diagonale)"])
    return None
