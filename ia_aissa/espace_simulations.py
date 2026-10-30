"""
L'espace des simulations : la liste, classée par type, dans la barre latérale ; chaque simulation produit un rapport
justifié (méthode, lois et articles, année de référence et taux appliqués), traçable et téléchargeable en PDF.
"""

import datetime

import streamlit as st

from . import baremes as B
from . import connaissances as K
from . import simulations as S
from .rapports import journaliser, markdown, pdf, rapport

CATEGORIES = {
    "🧭 Mes obligations (guide)": ["Mes impôts et déclarations (calendrier)", "Feuille de route du débutant",
                                   "Documents et attestations de régularité"],
    "📚 Impôts décortiqués": ["IR décortiqué", "IS décortiqué", "TVA décortiquée", "État 9421 (traitements et salaires)",
                             "Déclaration du revenu global (personnes physiques)", "Revenus fonciers (loyers) décortiqués"],
    "🧾 Fiscalité": ["IR (impôt sur le revenu)", "IS (impôt sur les sociétés)", "TVA due ou crédit de TVA",
                    "Revenus fonciers (loyers)", "Plus-value immobilière (profit foncier)", "Retenue sur dividendes", "Pénalités de retard (IS, TVA, IR)",
                    "Auto-entrepreneur", "Douane à l'importation"],
    "👥 RH et paie": ["Bulletin de paie complet", "Paie (brut ↔ net)", "État 9421 (préparation)",
                     "Masse salariale et augmentation", "Heures supplémentaires", "Indemnité de licenciement",
                     "Congés payés", "Solde de tout compte", "Retraite CNSS (pension)"],
    "📊 Projets et business plans": ["Business plan sur 5 ans", "Étude de sensibilité du projet",
                                    "Plan de financement initial"],
    "📒 Comptabilité": ["Amortissement", "Seuil de rentabilité", "Prix de vente et marges", "Coût de revient complet",
                       "Ratios financiers (bilan)"],
    "🏦 Banque": ["Crédit (échéancier)", "TEG d'un crédit", "Remboursement anticipé d'un crédit", "Capacité d'emprunt",
                 "Leasing ou crédit",
                 "Épargne (intérêts composés)"],
    "💰 Finance": ["Investissement (VAN, TRI)", "Besoin en fonds de roulement (BFR)", "Trésorerie sur 12 mois",
                  "Valorisation d'entreprise (DCF)", "Effet de levier financier", "Risque de perte (Monte-Carlo)"],
    "🛠️ Technique": ["Consommation électrique", "Section de câble électrique", "Pompe (puissance et coût)",
                    "Stock optimal (Wilson)"],
    "🏗️ Bâtiment": ["Béton (ciment, sable, gravier)", "Ferraillage (poids d'acier)", "Maçonnerie (blocs et mortier)",
                   "Peinture", "Carrelage"],
    "🏠 Immobilier": ["Rentabilité locative", "Frais d'acquisition immobilière", "Acheter ou louer"],
    "☀️ Énergie": ["Énergie solaire (photovoltaïque)", "Chauffe-eau solaire", "Groupe électrogène"],
    "📈 Statistiques et prévision": ["Croissance et projection (TCAM)", "Tendance et prévision (régression)",
                                    "Taille d'échantillon (sondage)"],
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
    """Toutes les simulations, classées par type, dans une seule liste déroulante de la barre latérale (on peut y
    taper pour chercher). Renvoie la simulation choisie."""
    toutes = [(categorie, nom) for categorie, noms in CATEGORIES.items() for nom in noms]
    libelles = [f"{categorie.split()[0]} {nom}" for categorie, nom in toutes]     # l'icône dit le type : 👥 Paie…

    def choisir():
        choix = st.session_state.get("sim_liste")
        if choix:
            st.session_state["simulation"] = toutes[libelles.index(choix)][1]
            st.session_state["mode_visiteur"] = MODES[1]

    def fermer():
        st.session_state.pop("simulation", None)
        st.session_state["sim_liste"] = None
        st.session_state["mode_visiteur"] = MODES[0]

    actuelle = st.session_state.get("simulation")
    attendu = next((l for l, (_, n) in zip(libelles, toutes) if n == actuelle), None)
    # N'écrire la valeur de la liste que si elle doit changer : la réécrire à chaque affichage effaçait un choix
    # fait pendant qu'une relance automatique (coffre de l'appareil) était en cours
    if attendu and st.session_state.get("sim_liste") != attendu:
        st.session_state["sim_liste"] = attendu
    with st.sidebar:
        st.markdown("## 🧮 Simulations")
        st.caption(f"{len(toutes)} simulations et guides, classés par type. Résultats justifiés (lois, articles, année, "
                   "taux) et rapport PDF traçable.")
        st.caption(" · ".join(categorie for categorie in CATEGORIES))
        st.selectbox("Choisir une simulation", libelles, index=None, key="sim_liste", on_change=choisir,
                     placeholder="🔎 Choisir ou taper (paie, crédit, TVA…)", label_visibility="collapsed")
        if actuelle:
            st.button("✖ Fermer la simulation", width="stretch", on_click=fermer)
    return st.session_state.get("simulation")


MODES = ["💬 Chat avec IA AISSA", "🧮 Simulations et guides"]


def choix_principal():
    """Sur mobile, la barre latérale est cachée : le même choix, par type puis par simulation, dans la page. Les deux
    listes suivent toujours la simulation en cours (choisie ici ou dans la barre latérale)."""
    actuelle = st.session_state.get("simulation") or next(iter(CATEGORIES.values()))[0]
    st.session_state["simulation"] = actuelle
    for cle, valeur in (("choix_type", categorie_de(actuelle)), ("choix_sim", actuelle)):
        if st.session_state.get(cle) != valeur:            # seulement si elle doit changer (voir barre_laterale)
            st.session_state[cle] = valeur

    def changer_type():
        st.session_state["simulation"] = CATEGORIES[st.session_state["choix_type"]][0]

    def changer_simulation():
        st.session_state["simulation"] = st.session_state["choix_sim"]

    c = st.columns(2)
    c[0].selectbox("Type", list(CATEGORIES), key="choix_type", on_change=changer_type)
    c[1].selectbox("Simulation ou guide", CATEGORIES[categorie_de(actuelle)], key="choix_sim",
                   on_change=changer_simulation)
    return actuelle


def excel(r):
    """Le rapport en classeur Excel : une feuille de synthèse (données, résultats, méthode, références, traçabilité)
    et le tableau de calcul, pour le reprendre dans ses propres fichiers."""
    import io
    import pandas as pd
    lignes = ([("Rapport", r["titre"]), ("Numéro", r["numero"]), ("Date", r["date"]), ("Type", r["categorie"]),
               ("Année de référence", r.get("annee") or "")]
              + [("", "")] + [("Donnée : " + k, v) for k, v in r["entrees"].items()]
              + [("", "")] + [("Résultat : " + k, v) for k, v in r["resultats"].items()]
              + [("", "")] + [("Méthode", m) for m in r["methode"]] + [("Référence", x) for x in r["references"]]
              + [("Proposition", x) for x in r.get("conseils", [])] + [("À savoir", x) for x in r.get("remarques", [])]
              + [("", ""), ("Empreinte SHA-256", r["empreinte"]), ("Limites", r["limites"])])
    sortie = io.BytesIO()
    with pd.ExcelWriter(sortie, engine="openpyxl") as classeur:
        pd.DataFrame(lignes, columns=["Rubrique", "Valeur"]).to_excel(classeur, sheet_name="Synthèse", index=False)
        if r.get("tableau") is not None:
            r["tableau"].to_excel(classeur, sheet_name="Tableau", index=False)
        for titre, tableau in r.get("annexes", {}).items():          # tableaux complémentaires (CPC, par année…)
            tableau.to_excel(classeur, sheet_name=titre[:31], index=False)
        for feuille in classeur.book.worksheets:
            for colonne in feuille.columns:
                largeur = max(len(str(c.value or "")) for c in colonne)
                feuille.column_dimensions[colonne[0].column_letter].width = min(80, max(12, largeur + 2))
    return sortie.getvalue()


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
    c = st.columns(2)
    if c[0].download_button("📄 Rapport PDF", pdf(r), f"{r['numero']}.pdf", "application/pdf", key=f"pdf_{nom}",
                            width="stretch"):
        journaliser(memoire, r)
    if c[1].download_button("📊 Classeur Excel", excel(r), f"{r['numero']}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"xlsx_{nom}",
                            width="stretch"):
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
        conseils = [f"Chaque dirham de plus est imposé à {pc(x['taux_marginal'])} (taux marginal) : c'est ce taux qui compte "
                    "pour juger d'une prime ou d'une dépense déductible."]
        if x["taux_marginal"] >= 0.30:
            conseils.append("Leviers légaux à étudier : cotisations de retraite complémentaire déductibles (CGI, art. 28), "
                            "intérêts d'un prêt pour l'habitation principale (art. 28), dons aux organismes reconnus "
                            "d'utilité publique (art. 28) ; faites chiffrer chaque levier par votre expert-comptable.")
        if x["taux_marginal"] == 0:
            conseils.append("Revenu sous le seuil d'exonération : aucune optimisation d'IR à rechercher.")
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
                                         "l'administrateur peut les ajouter à partir du Bulletin officiel."], conseils=conseils)
    if nom == "IS (impôt sur les sociétés)":
        p = B.periode("is", 2026)
        benefice = c[0].number_input("Résultat fiscal (DH)", value=500_000.0, step=10_000.0, key="is_ben")
        produits = c[1].number_input("Produits / chiffre d'affaires HT (DH)", 0.0, value=3_000_000.0, step=100_000.0,
                                     key="is_prod")
        secteur = c[2].selectbox("Secteur", ["Droit commun", "Établissements de crédit et assurances"], key="is_sect")
        debut = st.date_input("Début d'activité de la société", value=datetime.date(2015, 1, 1), key="is_debut")
        mois_activite = (2026 - debut.year) * 12 + (12 - debut.month + 1)
        x = K.calculer_is_du(benefice, produits)
        nouvelle = mois_activite <= 36                     # CGI art. 144 : exonération de cotisation minimale 36 mois
        if nouvelle:
            x["cotisation_minimale"] = 0.0
            x["is_du"] = x["is"]
            x["retenu"] = "IS proportionnel (cotisation minimale exonérée : société de moins de 36 mois)"
        if secteur != "Droit commun":                       # CGI art. 19 : taux de 40 % pour ce secteur
            x["taux"] = 0.40
            x["is"] = round(max(benefice, 0) * 0.40, 2)
            x["is_du"] = max(x["is"], x["cotisation_minimale"])
            x["retenu"] = "cotisation minimale" if x["cotisation_minimale"] > x["is"] else "IS proportionnel"
        conseils = []
        if x["retenu"] == "cotisation minimale":
            conseils.append("La cotisation minimale dépasse l'IS : la marge est faible ou négative. Priorité : rétablir la "
                            "rentabilité (prix, coûts) plutôt que chercher à réduire l'IS.")
        if benefice > 0 and x["taux"] >= 0.20:
            conseils.append("Vérifiez que toutes les charges déductibles sont comptabilisées (amortissements, provisions "
                            "justifiées, dotations) : chaque 100 000 DH de charge déductible réduit l'IS de "
                            f"{dh(100_000 * x['taux'])}.")
        if benefice >= 90_000_000 and secteur == "Droit commun":
            conseils.append("Bénéfice proche du seuil de 100 millions DH : au-delà, tout le bénéfice passe à 35 %. "
                            "Anticipez avec votre conseil (calendrier des produits et charges, investissements).")
        return rapport(nom, categorie_de(nom), {"Année de référence": 2026, "Secteur": secteur,
                                                "Début d'activité": debut.strftime("%d/%m/%Y"),
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
                                        "d'accélération industrielle, Casablanca Finance City, entreprises agricoles, "
                                        "réductions d'impôt spécifiques. Appliqué : exonération de cotisation minimale "
                                        "pendant les 36 premiers mois d'activité (CGI, art. 144)."], conseils=conseils)
    if nom == "TVA due ou crédit de TVA":
        annee = c[0].selectbox("Année de référence", B.annees_couvertes("tva")[::-1], key="tva_annee")
        coll = c[1].number_input("TVA collectée sur les ventes", 0.0, value=50_000.0, key="tva_coll")
        ded = c[2].number_input("TVA déductible sur les achats", 0.0, value=30_000.0, key="tva_ded")
        p = B.periode("tva", annee)
        x = K.calculer_tva_due(coll, ded)
        conseils = []
        if x["credit_de_tva"] > 0:
            conseils.append("Crédit de TVA : il s'impute sur les déclarations suivantes. S'il devient structurel (taux de "
                            "vente inférieur au taux d'achat, export, investissements), étudiez les cas de remboursement "
                            "prévus par le CGI (art. 103) avec votre expert-comptable.")
        else:
            conseils.append("Contrôlez que toute la TVA déductible est récupérée : factures conformes (identifiant fiscal, "
                            "montants HT/TVA), paiement effectif, délai d'un an pour la déduction.")
        return rapport(nom, categorie_de(nom), {"Année de référence": annee, "TVA collectée": dh(coll),
                                                "TVA déductible": dh(ded)},
                       {"TVA due": dh(x["tva_due"]), "Crédit de TVA": dh(x["credit_de_tva"])},
                       [f"Taux en vigueur en {annee} : normal {pc(p['taux']['normal'])} ; réduits : "
                        + ", ".join(pc(t) if isinstance(t, float) else t for t in p["taux"]["réduits"]) + ".",
                        f"TVA due = collectée − déductible = {dh(coll)} − {dh(ded)} = {dh(coll - ded)}.",
                        "Si le résultat est négatif, c'est un crédit de TVA reportable sur les déclarations suivantes."],
                       [p["loi"], "CGI, art. 101 (droit à déduction)", *(f"Source consultée : {s}" for s in p["sources"]),
                        f"Vérifié le {B.VERIFIE_LE}."], annee, remarques=[p["remarque"]], conseils=conseils)
    if nom == "Auto-entrepreneur":
        ca = c[0].number_input("Chiffre d'affaires annuel (DH)", 0.0, value=150_000.0, step=10_000.0, key="ae_ca")
        act = c[1].radio("Activité", ["services", "commerce"], key="ae_act")
        x = S.auto_entrepreneur(ca, act)
        conseils = []
        if x["depasse_le_plafond"]:
            conseils.append("Plafond dépassé : passez au régime du résultat net simplifié ou créez une SARL (associé "
                            "unique possible) ; comparez la charge fiscale et sociale avant le changement.")
        elif ca > 0.8 * x["plafond"]:
            conseils.append(f"Vous êtes à {ca / x['plafond']:.0%} du plafond : préparez dès maintenant le passage à une "
                            "forme sociale adaptée pour ne pas être bloqué en cours d'année.")
        else:
            conseils.append("Régime très avantageux à ce niveau : gardez des justificatifs du chiffre d'affaires et "
                            "déclarez-le chaque trimestre.")
        return rapport(nom, categorie_de(nom), {"Activité": x["activite"], "Chiffre d'affaires": dh(ca)},
                       {"Impôt": dh(x["impot"]), "Taux": pc(x["taux"]), "Plafond": dh(x["plafond"], 0),
                        "Plafond dépassé": "oui" if x["depasse_le_plafond"] else "non"},
                       [f"Impôt = chiffre d'affaires × {pc(x['taux'])} = {dh(x['impot'])}.",
                        "Taux : 0,5 % (commerce, industrie, artisanat), 1 % (services)."],
                       ["Loi n° 114-13 relative au statut de l'auto-entrepreneur", "CGI, art. 73 (taux de l'IR)",
                        f"Taux et plafonds de la base de connaissances (mise à jour {K.MISE_A_JOUR})."], 2026, conseils=conseils)
    if nom == "Douane à l'importation":
        caf = c[0].number_input("Valeur CAF (DH)", 0.0, value=100_000.0, step=5_000.0, key="dou_caf")
        di = c[1].number_input("Droit d'importation (%)", 0.0, 200.0, 17.5, key="dou_di") / 100
        x = K.calculer_droits_import(caf, di)
        conseils = ["Vérifiez l'origine de la marchandise : avec un certificat d'origine (EUR.1 pour l'Union européenne, "
                    "accords de libre-échange), le droit d'importation peut être réduit ou nul.",
                    "La TVA à l'import est déductible si la marchandise sert à une activité taxable : intégrez-la dans "
                    "votre trésorerie, pas dans votre coût de revient."]
        return rapport(nom, categorie_de(nom), {"Valeur CAF": dh(caf), "Droit d'importation": pc(di)},
                       {"Droit d'importation": dh(x["droit_importation"]), "TVA à l'import": dh(x["tva_import"]),
                        "Total droits et taxes": dh(x["total_droits_et_taxes"]),
                        "Coût dédouané": dh(x["cout_total_dedouane"])},
                       [f"Droit = valeur CAF × taux = {dh(caf)} × {pc(di)} = {dh(x['droit_importation'])}.",
                        f"TVA à l'import = (valeur CAF + droit) × 20 % = {dh(x['tva_import'])}."],
                       ["Code des douanes et impôts indirects (dahir n° 1-77-339) et tarif douanier de l'ADII",
                        "CGI : TVA à l'importation", x["remarque"]], 2026, conseils=conseils)
    if nom == "Paie (brut ↔ net)":
        sens = c[0].radio("Je connais", ["le brut", "le net"], key="paie_sens2")
        montant = c[1].number_input("Montant mensuel (DH)", 0.0, value=8000.0, step=500.0, key="paie_mont2")
        brut = K.brut_pour_net(montant) if sens == "le net" else montant
        x = K.calculer_paie(brut)
        base = min(brut, K.PLAFOND_CNSS_MENSUEL)
        conseils = ["Pour le bulletin complet (prime d'ancienneté, charges de famille, allocations familiales, formation "
                    "professionnelle, contrôle du SMIG), ouvrez « Bulletin de paie complet »."]
        if x["ir"] > 0:
            conseils.append("Indemnités exonérées dans les limites légales (transport, panier…) : même net pour un coût "
                            "employeur plus faible, mais des droits CNSS calculés sur un brut plus bas.")
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
                       remarques=[x["remarque"]], conseils=conseils)
    if nom == "Crédit (échéancier)":
        capital = c[0].number_input("Capital (DH)", 0.0, value=200_000.0, step=10_000.0, key="cr_cap")
        taux = c[1].number_input("Taux annuel (%)", 0.0, 30.0, 5.0, 0.1, key="cr_taux") / 100
        ans = c[2].number_input("Durée (ans)", 1, 30, 10, key="cr_ans")
        c2 = st.columns(4)
        deblocage = c2[0].date_input("Date de déblocage", value=datetime.date.today(), key="cr_date", format="DD/MM/YYYY")
        differe = c2[1].number_input("Différé (mois, intérêts seuls)", 0, 36, 0, key="cr_diff")
        assurance = c2[2].number_input("Assurance (DH/mois)", 0.0, value=0.0, step=10.0, key="cr_ass")
        frais = c2[3].number_input("Frais de dossier (DH)", 0.0, value=0.0, step=100.0, key="cr_frais")
        x = S.echeancier_credit(capital, taux, ans * 12, deblocage, differe, assurance)
        teg = S.taux_effectif_global(capital, taux, ans * 12, frais, assurance) if not differe else None
        plus_court = S.echeancier_credit(capital, taux, max(12, (ans - 2) * 12))
        conseils = [f"Sur {ans - 2} ans au lieu de {ans} : mensualité {dh(plus_court['mensualite'])} (+"
                    f"{dh(plus_court['mensualite'] - x['mensualite'])}) mais {dh(x['cout_total'] - plus_court['cout_total'])} "
                    "d'intérêts en moins." if ans > 3 else "Durée déjà courte : le coût des intérêts est contenu.",
                    "Négociez le taux et comparez le TEG (assurance et frais compris) de plusieurs banques : 0,5 point de "
                    f"moins économise environ {dh(x['cout_total'] - S.echeancier_credit(capital, max(0, taux - 0.005), ans * 12)['cout_total'])}.",
                    "Vérifiez les indemnités de remboursement anticipé prévues au contrat avant de signer."]
        r = rapport(nom, categorie_de(nom), {"Capital": dh(capital), "Taux nominal annuel": pc(taux),
                                                "Durée": f"{ans} ans ({ans * 12} mois)",
                                                "Date de déblocage": deblocage.strftime("%d/%m/%Y"),
                                                "Différé": f"{differe} mois", "Assurance": dh(assurance) + "/mois",
                                                "Frais de dossier": dh(frais)},
                       {"Mensualité (hors assurance)": dh(x["mensualite"]),
                        "Première échéance": x["premiere_echeance"], "Dernière échéance": x["derniere_echeance"],
                        "Coût des intérêts": dh(x["cout_total"]), "Total remboursé": dh(x["total_rembourse"]),
                        "Coût de l'assurance": dh(assurance * ans * 12),
                        "TEG (frais et assurance compris)": pc(teg["teg"]) if teg else "non calculé avec un différé"},
                       ["Mensualité constante M = C × t / (1 − (1 + t)^−n), avec t = taux annuel ÷ 12 et n = nombre de mois.",
                        f"M = {dh(capital)} × {taux / 12:.6f} / (1 − (1 + {taux / 12:.6f})^−{ans * 12}) = {dh(x['mensualite'])}.",
                        "Chaque mois : intérêts = capital restant × t ; capital remboursé = M − intérêts.",
                        "Échéances datées un mois après le déblocage, puis de mois en mois (fin de mois si le jour "
                        "n'existe pas) ; pendant le différé, seuls les intérêts sont payés et M est calculée sur les "
                        "mois restants.",
                        "TEG : taux annuel qui égalise le capital reçu (moins les frais) et toutes les sommes payées "
                        "(mensualités et assurance), comme l'exige l'information du consommateur."],
                       ["Formule de l'annuité constante (mathématiques financières)",
                        "Loi n° 31-08 édictant des mesures de protection du consommateur (information sur le crédit, TEG)"],
                       remarques=["Hors assurance, frais de dossier et garanties : le taux effectif global (TEG) de la "
                                  "banque est plus élevé que le taux nominal.",
                                  "Récapitulatif par année civile : " + " ; ".join(
                                      f"{int(l['Année'])} : intérêts {dh(l['Intérêts'])}, capital {dh(l['Capital remboursé'])}"
                                      for l in x["par_annee"].to_dict("records"))],
                       tableau=x["tableau"], conseils=conseils + ([
                           f"Le différé de {differe} mois coûte {dh(x['cout_total'] - S.echeancier_credit(capital, taux, ans * 12)['cout_total'])} "
                           "d'intérêts en plus : ne le prenez que si le projet ne produit pas encore de revenus."] if differe else []))
        r["annexes"] = {"Par année": x["par_annee"]}
        return r
    if nom == "Épargne (intérêts composés)":
        versement = c[0].number_input("Versement mensuel (DH)", 0.0, value=500.0, step=100.0, key="ep_ver")
        taux = c[1].number_input("Rendement annuel (%)", 0.0, 20.0, 4.0, 0.1, key="ep_taux") / 100
        ans = c[2].number_input("Durée (ans)", 1, 50, 10, key="ep_ans")
        debut_ep = st.number_input("Année du premier versement", 2000, 2100, datetime.date.today().year, key="ep_deb")
        x = S.epargne(versement, taux, ans, annee_debut=debut_ep)
        conseils = [f"Commencer tôt compte plus que le montant : sur {ans} ans, les intérêts représentent "
                    f"{x['interets'] / max(x['capital_final'], 1):.0%} du capital final.",
                    "Comparez les produits d'épargne (rendement, fiscalité des produits de placement, disponibilité)."]
        return rapport(nom, categorie_de(nom), {"Versement mensuel": dh(versement), "Rendement annuel": pc(taux),
                                                "Durée": f"{ans} ans"},
                       {"Capital final": dh(x["capital_final"]), "Total versé": dh(x["total_verse"]),
                        "Intérêts gagnés": dh(x["interets"])},
                       ["Chaque mois : capital = capital × (1 + rendement ÷ 12) + versement.",
                        "Les intérêts produisent à leur tour des intérêts (capitalisation mensuelle)."],
                       ["Formule des intérêts composés (mathématiques financières)"],
                       remarques=["Rendement supposé constant, avant impôt sur les produits de placement."],
                       tableau=x["tableau"], conseils=conseils)
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
        conseils = [("Projet créateur de valeur : la VAN est positive au taux exigé." if x["van"] > 0 else
                     "VAN négative : revoyez le prix, les coûts ou phasez l'investissement."),
                    "Testez la sensibilité : refaites la simulation avec des flux 20 % plus faibles (scénario prudent)."]
        return rapport(nom, categorie_de(nom), {"Investissement": dh(investissement), "Taux d'actualisation": pc(taux),
                                                "Flux": " ; ".join(dh(f) for f in liste)},
                       {"VAN": dh(x["van"]), "TRI": pc(x["tri"]) if x["tri"] is not None else "non calculable",
                        "Délai de récupération": f"{x['delai_recuperation_ans']} an(s)", "Décision": x["decision"]},
                       ["VAN = −I + Σ Fₜ / (1 + a)ᵗ : la valeur d'aujourd'hui des flux futurs, moins l'investissement.",
                        "TRI = le taux qui annule la VAN (trouvé par dichotomie) ; projet intéressant si TRI > taux exigé.",
                        "Délai de récupération = temps pour que les flux cumulés remboursent l'investissement."],
                       ["Méthodes d'évaluation des investissements (finance d'entreprise)"], conseils=conseils)
    if nom == "Seuil de rentabilité":
        prix = c[0].number_input("Prix de vente unitaire", 0.0, value=100.0, key="sr_p")
        cv = c[1].number_input("Coût variable unitaire", 0.0, value=60.0, key="sr_cv")
        cf = c[2].number_input("Charges fixes annuelles", 0.0, value=200_000.0, step=10_000.0, key="sr_cf")
        x = K.seuil_rentabilite(prix, cv, cf)
        if x.get("seuil_en_quantite") is None:
            st.error(x["remarque"])
            return None
        conseils = ["Pour baisser le seuil : augmenter la marge unitaire (prix, achats) a souvent plus d'effet que "
                    "réduire les charges fixes.", "Calculez la marge de sécurité : (CA prévu − CA du seuil) ÷ CA prévu."]
        return rapport(nom, categorie_de(nom), {"Prix unitaire": dh(prix), "Coût variable unitaire": dh(cv),
                                                "Charges fixes": dh(cf)},
                       {"Marge sur coût variable unitaire": dh(x["marge_sur_cout_variable_unitaire"]),
                        "Seuil (unités)": f"{x['seuil_en_quantite']:,.0f}".replace(",", " "),
                        "Seuil (chiffre d'affaires)": dh(x["seuil_en_chiffre_affaires"])},
                       ["Marge unitaire = prix − coût variable.", "Seuil (quantité) = charges fixes ÷ marge unitaire.",
                        "Seuil (CA) = quantité × prix : en dessous, l'entreprise perd de l'argent."],
                       ["Méthode du coût variable (comptabilité analytique)"], conseils=conseils)
    if nom == "Prix de vente et marges":
        cout = c[0].number_input("Coût de revient (DH)", 0.0, value=80.0, key="pv_c")
        base = c[1].radio("Je fixe", ["un taux de marge (sur coût)", "un taux de marque (sur prix)"], key="pv_b")
        taux = c[2].number_input("Taux (%)", 0.0, 99.0, 25.0, key="pv_t") / 100
        x = S.prix_de_vente(cout, taux_de_marque=taux) if "marque" in base else S.prix_de_vente(cout, taux_marge_sur_cout=taux)
        conseils = ["Comparez votre prix aux concurrents et à la valeur perçue : le taux de marque est l'indicateur "
                    "lisible pour piloter vos ventes."]
        return rapport(nom, categorie_de(nom), {"Coût de revient": dh(cout), "Base": f"{base} : {pc(taux)}"},
                       {"Prix HT": dh(x["prix_ht"]), "Prix TTC (TVA 20 %)": dh(x["prix_ttc"]), "Marge": dh(x["marge"]),
                        "Taux de marge": pc(x["taux_de_marge"]), "Taux de marque": pc(x["taux_de_marque"])},
                       ["Taux de marge = marge ÷ coût de revient ; taux de marque = marge ÷ prix de vente HT.",
                        "Prix HT = coût × (1 + taux de marge) ou coût ÷ (1 − taux de marque)."],
                       ["Définitions du Code général de normalisation comptable (CGNC) et de la gestion commerciale",
                        "CGI, art. 98 et 99 (TVA au taux normal de 20 %)"], 2026, conseils=conseils)
    if nom == "Trésorerie sur 12 mois":
        solde = c[0].number_input("Solde de départ (DH)", value=50_000.0, step=5_000.0, key="tr_s")
        enc = c[1].text_input("Encaissements (;)", "80000; 60000; 90000; 70000; 85000; 60000; 95000; 70000; 80000; "
                                                   "90000; 75000; 100000", key="tr_e")
        dec = c[2].text_input("Décaissements (;)", "90000; 85000; 80000; 75000; 80000; 85000; 80000; 90000; 75000; "
                                                   "80000; 85000; 80000", key="tr_d")
        try:
            lire = lambda t: [float(v.replace(" ", "").replace(",", ".")) for v in t.split(";") if v.strip()]
            depart = st.date_input("Premier mois du plan", value=datetime.date.today().replace(day=1), key="tr_m",
                                   format="DD/MM/YYYY")
            x = S.tresorerie(solde, lire(enc), lire(dec), depart)
        except ValueError:
            st.error("Écris les montants comme ceci : 80000; 60000; 90000")
            return None
        conseils = ([f"Découvert prévu en {x['periode_decouvert']} (besoin maximal {dh(x['besoin_maximal'])}) : négociez dès maintenant une facilité de "
                     "caisse, décalez un investissement ou accélérez l'encaissement des créances."]
                    if x["premier_mois_a_decouvert"] else ["Trésorerie toujours positive : placez l'excédent à court terme."])
        return rapport(nom, categorie_de(nom), {"Solde de départ": dh(solde), "Encaissements": enc, "Décaissements": dec},
                       {"Solde final": dh(x["solde_final"]), "Solde le plus bas": dh(x["solde_minimum"]),
                        "Premier mois à découvert": x["periode_decouvert"] or "aucun",
                        "Besoin de financement maximal": dh(x["besoin_maximal"])},
                       ["Solde de fin de mois = solde précédent + encaissements − décaissements.",
                        "Un solde négatif signale un besoin de financement (découvert, facilité de caisse)."],
                       ["Plan de trésorerie (gestion financière à court terme)"], tableau=x["tableau"], conseils=conseils)
    if nom == "Amortissement":
        valeur = c[0].number_input("Valeur d'acquisition HT (DH)", 0.0, value=100_000.0, step=5_000.0, key="am_v")
        ans = c[1].number_input("Durée (ans)", 1, 40, 5, key="am_n")
        methode = c[2].radio("Méthode", ["lineaire", "degressif"], format_func=str.capitalize, key="am_m")
        c2 = st.columns(3)
        nature = c2[0].selectbox("Nature du bien", ["Matériel, outillage, mobilier, informatique",
                                                    "Véhicule de transport de personnes", "Construction"], key="am_nat")
        service = c2[1].date_input("Date d'acquisition ou de mise en service", value=datetime.date(2026, 1, 1),
                                   key="am_date", format="DD/MM/YYYY")
        valeur_ttc = valeur
        remarques_am = ["Exercices supposés calés sur l'année civile (1er janvier – 31 décembre)."]
        if nature != "Matériel, outillage, mobilier, informatique" and methode == "degressif":
            methode = "lineaire"
            st.info("Dégressif exclu pour les constructions et les véhicules de transport de personnes (CGI, art. 10) : "
                    "linéaire appliqué.")
            remarques_am.append("Dégressif exclu pour ce bien : plan linéaire.")
        if methode == "degressif" and ans < 3:
            methode = "lineaire"
            remarques_am.append("Durée inférieure à 3 ans : plan linéaire.")
        if nature == "Véhicule de transport de personnes":
            valeur_ttc = c2[2].number_input("Valeur TTC du véhicule (DH)", 0.0, value=valeur * 1.2, step=5_000.0,
                                            key="am_ttc")
            if ans < 5:
                ans = 5
                remarques_am.append("Véhicule de tourisme : taux d'amortissement de 20 % par an (5 ans).")
        base_deductible = min(valeur_ttc, 300_000) if nature == "Véhicule de transport de personnes" else valeur
        x = S.amortissement(base_deductible, ans, methode, service.month, service.year)
        if nature == "Véhicule de transport de personnes" and valeur_ttc > 300_000:
            remarques_am.append(f"Base déductible plafonnée à 300 000 DH TTC : la part au-delà ({dh(valeur_ttc - 300_000)}) "
                                "n'est pas déductible (CGI, art. 10-I-F-1-b) — à réintégrer au résultat fiscal.")
        etapes = (["Dotation annuelle = valeur ÷ durée."] if methode == "lineaire" else
                  [f"Taux dégressif = (1 ÷ durée) × coefficient = (1 ÷ {ans}) × {x['coefficient']} = {pc(x['taux'])}.",
                   "Coefficients : 1,5 (3 ou 4 ans), 2 (5 ou 6 ans), 3 (plus de 6 ans).",
                   "Dotation = valeur nette comptable × taux ; passage au linéaire dès qu'il donne davantage."])
        etapes.append(f"Point de départ : 1er jour du mois de mise en service ({service.strftime('%m/%Y')}) ; première "
                      f"annuité au prorata ({13 - service.month}/12), plan sur {x['exercices']} exercices.")
        lin = S.amortissement(base_deductible, ans, "lineaire", service.month)["tableau"]["Dotation"].iloc[0]
        deg = (S.amortissement(base_deductible, ans, "degressif", service.month)["tableau"]["Dotation"].iloc[0]
               if ans >= 3 and nature.startswith("Matériel") else lin)
        conseils = [f"Le dégressif déduit {dh(deg - lin)} de plus la première année : environ {dh((deg - lin) * 0.20)} "
                    "d'IS reporté (au taux de 20 %), utile pour la trésorerie d'une entreprise bénéficiaire."
                    if deg > lin else "Durée trop courte pour le dégressif : le linéaire s'applique.",
                    "L'option pour le dégressif se fait bien par bien et dans les règles du CGI : documentez-la."]
        return rapport(nom, categorie_de(nom), {"Valeur": dh(valeur), "Nature": nature, "Durée": f"{ans} ans",
                                                "Méthode": methode, "Mise en service": service.strftime("%d/%m/%Y")},
                       {"Base amortissable": dh(base_deductible),
                        f"Dotation {service.year}": dh(x["tableau"]["Dotation"].iloc[0]),
                        "Dernier exercice": int(x["tableau"]["Exercice"].iloc[-1]),
                        "Total amorti": dh(x["tableau"]["Dotation"].sum())},
                       etapes, ["CGI, art. 10-I-F-1-b (amortissements : point de départ, dégressif, véhicules)",
                                "Loi n° 9-88 et Code général de normalisation comptable (CGNC)"], service.year,
                       tableau=x["tableau"], remarques=remarques_am, conseils=conseils)
    if nom == "Stock optimal (Wilson)":
        d = c[0].number_input("Demande annuelle (unités)", 0.0, value=12_000.0, key="st_d")
        cp = c[1].number_input("Coût d'une commande (DH)", 0.0, value=500.0, key="st_cp")
        cs = c[2].number_input("Coût de stockage / unité / an", 0.01, value=2.0, key="st_cs")
        x = K.quantite_wilson(d, cp, cs)
        conseils = ["Ajoutez un stock de sécurité (demande pendant le délai de livraison × incertitude) au point de "
                    "commande."]
        return rapport(nom, categorie_de(nom), {"Demande annuelle": d, "Coût d'une commande": dh(cp),
                                                "Coût de stockage unitaire": dh(cs)},
                       {k.replace("_", " ").capitalize(): v for k, v in x.items()},
                       ["Quantité économique Q* = √(2 × demande × coût de commande ÷ coût de stockage unitaire).",
                        "À Q*, le coût total de passation des commandes égale le coût de possession du stock."],
                       ["Modèle de Wilson (gestion des stocks)"], conseils=conseils)
    if nom == "Risque de perte (Monte-Carlo)":
        ca = st.slider("Chiffre d'affaires possible (DH)", 0, 5_000_000, (800_000, 1_200_000), 50_000, key="mc_ca")
        tcv = st.slider("Coûts variables (% du chiffre d'affaires)", 0, 100, (55, 70), key="mc_tcv")
        cf = st.number_input("Charges fixes (DH)", 0.0, value=350_000.0, step=10_000.0, key="mc_cf")
        x = S.risque_monte_carlo(ca[0], ca[1], tcv[0] / 100, tcv[1] / 100, cf)
        conseils = ([f"Risque de perte élevé ({pc(x['probabilite_de_perte'])}) : réduisez les charges fixes ou "
                     "sécurisez une partie du chiffre d'affaires (contrats, acomptes)."]
                    if x["probabilite_de_perte"] > 0.2 else ["Risque contenu : gardez une réserve équivalente au scénario bas."])
        return rapport(nom, categorie_de(nom), {"Chiffre d'affaires": f"{dh(ca[0], 0)} à {dh(ca[1], 0)}",
                                                "Coûts variables": f"{tcv[0]} % à {tcv[1]} %", "Charges fixes": dh(cf)},
                       {"Probabilité de perte": pc(x["probabilite_de_perte"]), "Résultat moyen": dh(x["resultat_moyen"]),
                        "Fourchette à 90 %": f"{dh(x['p5'], 0)} à {dh(x['p95'], 0)}"},
                       [f"{x['simulations']:,} scénarios tirés au hasard (lois uniformes) dans les fourchettes saisies."
                        .replace(",", " "),
                        "Résultat de chaque scénario = CA × (1 − taux de coûts variables) − charges fixes.",
                        "Probabilité de perte = part des scénarios où le résultat est négatif."],
                       ["Méthode de Monte-Carlo (statistiques, gestion des risques)"], conseils=conseils)
    if nom == "Heures supplémentaires":
        taux = c[0].number_input("Salaire horaire (DH)", 0.0, value=20.0, key="hs_t")
        hj = c[1].number_input("Heures 6 h – 21 h (jours ouvrables)", 0.0, value=10.0, key="hs_j")
        hn = c[2].number_input("Heures 21 h – 6 h (jours ouvrables)", 0.0, value=0.0, key="hs_n")
        c2 = st.columns(3)
        rj = c2[0].number_input("Heures 6 h – 21 h (repos hebdo.)", 0.0, value=0.0, key="hs_rj")
        rn = c2[1].number_input("Heures 21 h – 6 h (repos hebdo.)", 0.0, value=0.0, key="hs_rn")
        x = S.heures_supplementaires(taux, hj, hn, rj, rn)
        conseils = ["Au-delà d'un volume régulier, comparez avec une embauche à temps partiel : la majoration (25 % à "
                    "100 %) et la fatigue coûtent souvent plus cher qu'un renfort.",
                    "Les heures supplémentaires exigent une autorisation et restent plafonnées : tenez un registre."]
        return rapport(nom, categorie_de(nom), {"Salaire horaire": dh(taux), "Heures": f"{hj + hn + rj + rn:g}"},
                       {"Montant des heures supplémentaires": dh(x["total"])},
                       ["Montant = heures × salaire horaire × (1 + majoration).",
                        "Majorations : 25 % de 6 h à 21 h et 50 % de 21 h à 6 h les jours ouvrables ; 50 % et 100 % le "
                        "jour du repos hebdomadaire."],
                       [f"{CODE_TRAVAIL}, art. 196 à 204 (heures supplémentaires), notamment art. 201 (majorations)"],
                       tableau=x["tableau"], conseils=conseils)
    if nom == "Indemnité de licenciement":
        sh = c[0].number_input("Salaire horaire moyen (DH)", 0.0, value=50.0, key="il_s",
                               help="Moyenne des 52 dernières semaines (salaire mensuel ÷ 191 heures environ).")
        ans = c[1].number_input("Ancienneté (années)", 0.0, 60.0, 12.0, 0.5, key="il_a")
        x = S.indemnite_licenciement(sh, ans)
        conseils = ["Respectez la procédure (art. 62 et suivants : convocation, audition, notification) : un vice de "
                    "procédure ouvre droit à des dommages-intérêts en plus de l'indemnité.",
                    "Une rupture négociée (transaction signée devant l'inspection du travail) sécurise les deux parties."]
        return rapport(nom, categorie_de(nom), {"Salaire horaire moyen": dh(sh), "Ancienneté": f"{ans:g} ans"},
                       {"Heures dues": f"{x['heures']:g} h", "Indemnité de licenciement": dh(x["indemnite"])},
                       ["96 heures de salaire par année pour les 5 premières années, 144 h de la 6e à la 10e, 192 h de "
                        "la 11e à la 15e, 240 h au-delà.", "Indemnité = heures dues × salaire horaire moyen."],
                       [f"{CODE_TRAVAIL}, art. 52 et 53 (indemnité de licenciement)"],
                       remarques=["Non due en cas de faute grave ; des dommages-intérêts pour licenciement abusif "
                                  "(art. 41) peuvent s'ajouter.", "Exonération d'IR dans les limites de l'art. 57 du CGI."],
                       tableau=x["tableau"], conseils=conseils)
    if nom == "Congés payés":
        mois = c[0].number_input("Mois de service dans l'année", 0, 12, 12, key="cp_m")
        anc = c[1].number_input("Ancienneté (années)", 0, 60, 10, key="cp_a")
        x = S.conges_payes(mois, anc)
        conseils = ["Planifiez les congés à l'avance et gardez un registre : le congé non pris dans les délais légaux "
                    "peut donner lieu à une indemnité compensatrice."]
        return rapport(nom, categorie_de(nom), {"Mois de service": mois, "Ancienneté": f"{anc} ans"},
                       {"Jours ouvrables de congé": f"{x['jours']:g}"},
                       [f"Base : 1,5 jour par mois de service = {x['base']:g} jours.",
                        f"Ancienneté : 1,5 jour par période de 5 ans = {x['anciennete']:g} jours.",
                        "Total plafonné à 30 jours ouvrables."],
                       [f"{CODE_TRAVAIL}, art. 231 (durée du congé) et art. 241 (majoration pour ancienneté)"],
                       remarques=["Salariés de moins de 18 ans : 2 jours par mois (art. 231)."], conseils=conseils)
    if nom == "Capacité d'emprunt":
        revenu = c[0].number_input("Revenu net mensuel (DH)", 0.0, value=15_000.0, step=500.0, key="ce_r")
        charges = c[1].number_input("Crédits en cours (mensualités, DH)", 0.0, value=0.0, key="ce_c")
        taux = c[2].number_input("Taux annuel (%)", 0.0, 20.0, 5.0, 0.1, key="ce_t") / 100
        c2 = st.columns(3)
        ans = c2[0].number_input("Durée (ans)", 1, 30, 20, key="ce_a")
        endettement = c2[1].number_input("Taux d'endettement retenu (%)", 10, 60, 40, key="ce_e") / 100
        x = S.capacite_emprunt(revenu, charges, taux, ans * 12, endettement)
        conseils = ["Un apport personnel réduit le capital à emprunter et améliore le taux proposé.",
                    "Allonger la durée augmente le capital empruntable mais aussi le coût total : comparez 15, 20 et 25 ans."]
        return rapport(nom, categorie_de(nom), {"Revenu net mensuel": dh(revenu), "Crédits en cours": dh(charges),
                                                "Taux": pc(taux), "Durée": f"{ans} ans",
                                                "Taux d'endettement": pc(endettement)},
                       {"Mensualité maximale": dh(x["mensualite_max"]), "Capital empruntable": dh(x["capital_max"])},
                       ["Mensualité maximale = revenu × taux d'endettement − mensualités en cours.",
                        "Capital = M × (1 − (1 + t)^−n) / t (annuité constante inversée)."],
                       ["Usage bancaire : un taux d'endettement d'environ 40 % du revenu est couramment retenu "
                        "(chaque banque fixe sa propre limite)", "Loi n° 31-08 (protection du consommateur, crédit)"], conseils=conseils)
    if nom == "Besoin en fonds de roulement (BFR)":
        stocks = c[0].number_input("Stocks (DH)", 0.0, value=100_000.0, step=10_000.0, key="bfr_s")
        clients = c[1].number_input("Créances clients (DH)", 0.0, value=200_000.0, step=10_000.0, key="bfr_c")
        fourn = c[2].number_input("Dettes fournisseurs (DH)", 0.0, value=120_000.0, step=10_000.0, key="bfr_f")
        ca = st.number_input("Chiffre d'affaires annuel HT (DH)", 0.0, value=1_800_000.0, step=100_000.0, key="bfr_ca")
        x = S.besoin_fonds_roulement(stocks, clients, fourn, ca)
        conseils = [f"Chaque jour de délai client gagné libère environ {dh(ca / 360)} de trésorerie.",
                    "Leviers : relances et escompte pour paiement rapide, stocks au plus juste, délais fournisseurs "
                    "négociés dans la limite de la loi n° 69-21 (60 jours, 120 jours au plus par accord)."]
        return rapport(nom, categorie_de(nom), {"Stocks": dh(stocks), "Créances clients": dh(clients),
                                                "Dettes fournisseurs": dh(fourn), "Chiffre d'affaires": dh(ca)},
                       {"BFR": dh(x["bfr"]), "BFR en jours de CA": f"{x['jours_de_ca']} jours"},
                       ["BFR = stocks + créances clients − dettes fournisseurs.", "En jours de CA = BFR ÷ CA × 360."],
                       ["Analyse fonctionnelle du bilan (CGNC)", "Loi n° 69-21 sur les délais de paiement (60 jours en "
                        "principe, 120 jours au plus par accord) : elle influe sur les créances et les dettes"], conseils=conseils)
    if nom == "Consommation électrique":
        p = c[0].number_input("Puissance de l'appareil (W)", 0.0, value=2000.0, step=100.0, key="el_p")
        h = c[1].number_input("Heures par jour", 0.0, 24.0, 3.0, key="el_h")
        j = c[2].number_input("Jours", 1, 366, 30, key="el_j")
        prix = st.number_input("Prix du kWh (DH, voir votre facture)", 0.0, value=1.2, step=0.05, key="el_px")
        x = S.consommation_electrique(p, h, j, prix)
        conseils = ["Un appareil plus efficace ou un usage en heures creuses réduit la facture ; comparez avec une "
                    "installation solaire dans « Énergie solaire »."]
        return rapport(nom, categorie_de(nom), {"Puissance": f"{p:g} W", "Utilisation": f"{h:g} h/jour pendant {j} jours",
                                                "Prix du kWh": dh(prix)},
                       {"Énergie": f"{x['kwh']:g} kWh", "Coût": dh(x["cout"])},
                       ["Énergie (kWh) = puissance (kW) × heures d'utilisation.", "Coût = kWh × prix du kWh."],
                       ["Physique : énergie = puissance × temps"],
                       remarques=["Le prix du kWh dépend des tranches de consommation de votre distributeur : prenez "
                                  "celui de votre facture."], conseils=conseils)
    if nom == "Béton (ciment, sable, gravier)":
        lo = c[0].number_input("Longueur (m)", 0.0, value=5.0, key="be_l")
        la = c[1].number_input("Largeur (m)", 0.0, value=4.0, key="be_w")
        ep = c[2].number_input("Épaisseur (m)", 0.0, value=0.15, step=0.01, key="be_e")
        dosage = st.number_input("Dosage en ciment (kg/m³)", 150, 500, 350, 25, key="be_d")
        x = S.beton(lo, la, ep, dosage)
        conseils = ["Prévoyez 5 à 10 % de matériaux en plus pour les pertes ; respectez le temps de cure (arrosage) "
                    "pour atteindre la résistance."]
        return rapport(nom, categorie_de(nom), {"Dimensions": f"{lo:g} × {la:g} × {ep:g} m", "Dosage": f"{dosage} kg/m³"},
                       {"Volume": f"{x['volume_m3']:g} m³", "Ciment": f"{x['ciment_kg']:g} kg ({x['sacs_ciment_50kg']} sacs de 50 kg)",
                        "Sable": f"{x['sable_m3']:g} m³", "Gravier": f"{x['gravier_m3']:g} m³", "Eau": f"{x['eau_litres']:g} L"},
                       ["Volume = longueur × largeur × épaisseur.",
                        "Pour 1 m³ de béton courant : environ 400 L de sable, 800 L de gravier et 175 L d'eau."],
                       ["Dosages usuels de chantier pour un béton courant (à adapter à l'étude de structure)"],
                       remarques=["Pour un ouvrage porteur, suivez les prescriptions de l'ingénieur ou du bureau d'études."], conseils=conseils)
    if nom == "Peinture":
        surface = c[0].number_input("Surface à peindre (m²)", 0.0, value=60.0, key="pe_s")
        couches = c[1].number_input("Couches", 1, 5, 2, key="pe_c")
        rendement = c[2].number_input("Rendement (m²/L, voir le pot)", 1.0, value=10.0, key="pe_r")
        x = S.peinture(surface, couches, rendement)
        conseils = ["Une sous-couche sur un support neuf ou poreux réduit la consommation de peinture de finition."]
        return rapport(nom, categorie_de(nom), {"Surface": f"{surface:g} m²", "Couches": couches,
                                                "Rendement": f"{rendement:g} m²/L"},
                       {"Peinture nécessaire": f"{x['litres']:g} L"},
                       ["Litres = surface × couches ÷ rendement."], ["Rendement indiqué par le fabricant sur le pot"], conseils=conseils)
    if nom == "Carrelage":
        surface = c[0].number_input("Surface (m²)", 0.0, value=20.0, key="ca_s")
        lo = c[1].number_input("Longueur du carreau (cm)", 1.0, value=60.0, key="ca_l")
        la = c[2].number_input("Largeur du carreau (cm)", 1.0, value=60.0, key="ca_w")
        x = S.carrelage(surface, lo, la)
        conseils = ["Commandez tout dans le même lot de fabrication (teinte identique) et gardez quelques carreaux "
                    "pour les réparations."]
        return rapport(nom, categorie_de(nom), {"Surface": f"{surface:g} m²", "Carreau": f"{lo:g} × {la:g} cm"},
                       {"Surface à commander (+10 % de chutes)": f"{x['surface_a_commander_m2']:g} m²",
                        "Nombre de carreaux": x["carreaux"]},
                       ["Surface à commander = surface × 1,10 (chutes et casse).",
                        "Carreaux = surface à commander ÷ surface d'un carreau, arrondi au-dessus."],
                       ["Pratique de chantier : 10 % de marge pour la pose droite (15 % en diagonale)"], conseils=conseils)
    if nom == "Bulletin de paie complet":
        sens = st.radio("Je connais", ["le salaire de base (calcul à l'endroit)", "le salaire net (calcul à l'envers)"],
                        horizontal=True, key="bp_sens")
        a_l_envers = sens.startswith("le salaire net")
        if a_l_envers:
            net_vise = c[0].number_input("Salaire net à payer voulu (DH)", 0.0, value=7000.0, step=250.0, key="bp_net")
        else:
            base = c[0].number_input("Salaire de base mensuel (DH)", 0.0, value=8000.0, step=250.0, key="bp_base")
        anc = c[1].number_input("Ancienneté (années)", 0, 50, 6, key="bp_anc")
        pac = c[2].number_input("Personnes à charge", 0, 10, 2, key="bp_pac")
        c2 = st.columns(3)
        ded = c2[0].number_input("Déduction par personne à charge (DH/an)", 0.0, value=500.0, step=50.0, key="bp_ded",
                                 help="500 DH selon la LF 2025 ; certaines sources annoncent 600 DH pour 2026 : "
                                      "saisissez le montant de la loi de finances de l'année.")
        indem = c2[1].number_input("Indemnités exonérées (DH/mois)", 0.0, value=0.0, step=50.0, key="bp_ind")
        if a_l_envers:
            base = S.base_pour_net(net_vise, anc, pac, ded, indem)
            st.success(f"Pour un net de {dh(net_vise)}, le salaire de base à inscrire au contrat est de **{dh(base)}** "
                       "(bulletin détaillé ci-dessous).")
        x = S.paie_complete(base, anc, pac, ded, indem)
        patronal = " ; ".join(f"{k} {dh(v)}" for k, v in x["patronal"].items())
        conseils = []
        if x["sous_smig"]:
            conseils.append(f"⚠️ Salaire de base sous le SMIG ({dh(K.SMIG_HORAIRE_2026)}/h × {K.HEURES_LEGALES_MOIS} h = "
                            f"{dh(K.SMIG_HORAIRE_2026 * K.HEURES_LEGALES_MOIS)}) : à régulariser (Code du travail, art. 356).")
        if pac > 6:
            conseils.append("La déduction pour charges de famille est limitée à 6 personnes.")
        conseils.append(f"Coût employeur {dh(x['cout_employeur'])} pour un net de {dh(x['net'])} : le salarié perçoit "
                        f"{x['net'] / x['cout_employeur']:.0%} de ce que l'entreprise dépense.")
        if not indem:
            conseils.append("Indemnités exonérées (transport, panier…) justifiées : même net à coût moindre, mais droits "
                            "CNSS calculés sur un brut plus bas — à décider en connaissance de cause.")
        return rapport(nom, categorie_de(nom), {"Année de référence": 2026, "Calcul": sens,
                                                **({"Net voulu": dh(net_vise)} if a_l_envers else {}),
                                                "Salaire de base": dh(base),
                                                "Ancienneté": f"{anc} ans", "Personnes à charge": pac,
                                                "Déduction par personne": dh(ded), "Indemnités exonérées": dh(indem)},
                       {"Prime d'ancienneté": f"{dh(x['prime_anciennete'])} ({pc(x['taux_prime'])})",
                        "Salaire brut": dh(x["brut"]), "CNSS salarié": dh(x["cnss"]), "AMO salarié": dh(x["amo"]),
                        "Frais professionnels": f"{dh(x['frais_pro'])} ({pc(x['taux_frais_pro'])})",
                        "Net imposable": dh(x["net_imposable"]), "IR avant charges de famille": dh(x["ir_avant_famille"]),
                        "Déduction charges de famille": dh(x["deduction_famille"]), "IR": dh(x["ir"]),
                        "Salaire net à payer": dh(x["net"]), "Charges patronales": dh(x["total_patronal"]),
                        "Coût employeur": dh(x["cout_employeur"])},
                       [f"Prime d'ancienneté = salaire de base × {pc(x['taux_prime'])} (5 % après 2 ans, 10 % après 5, "
                        "15 % après 12, 20 % après 20, 25 % après 25).",
                        f"CNSS salarié = 4,48 % × min(brut ; 6 000 DH) ; AMO = 2,26 % × brut.",
                        "Frais professionnels : 35 % si brut annuel ≤ 78 000 DH, sinon 25 %, plafond 35 000 DH par an.",
                        "IR mensuel = barème annuel 2026 appliqué au net imposable × 12, ÷ 12, moins la déduction pour "
                        "charges de famille (au plus 6 personnes).",
                        f"Charges patronales : {patronal}."],
                       [f"{CODE_TRAVAIL}, art. 350 (prime d'ancienneté), art. 356 (SMIG)", CNSS_AMO,
                        "Taxe de formation professionnelle : 1,60 % ; allocations familiales : 6,40 %",
                        "CGI, art. 59 (frais professionnels), art. 73-I (barème), art. 74 (charges de famille)",
                        f"Taux vérifiés le {B.VERIFIE_LE} auprès de cabinets de paie (Humantal, Nexora, Jobsquare)"],
                       2026, remarques=["Non appliqués : avantages en nature, heures supplémentaires, primes "
                                        "exceptionnelles, retraite complémentaire (CIMR), mutuelle, exonérations "
                                        "spécifiques (stagiaires, premier emploi)."], conseils=conseils)
    if nom == "Rentabilité locative":
        prix = c[0].number_input("Prix d'achat (DH)", 0.0, value=1_000_000.0, step=50_000.0, key="rl_p")
        frais = c[1].number_input("Frais d'acquisition (DH)", 0.0, value=60_000.0, step=5_000.0, key="rl_f",
                                  help="Droits d'enregistrement, conservation foncière, notaire : demandez le montant exact au notaire.")
        loyer = c[2].number_input("Loyer mensuel (DH)", 0.0, value=5_000.0, step=250.0, key="rl_l")
        c2 = st.columns(3)
        charges = c2[0].number_input("Charges annuelles (DH)", 0.0, value=8_000.0, step=500.0, key="rl_c",
                                     help="Syndic, entretien, taxe de services communaux, assurance.")
        vacance = c2[1].number_input("Mois sans locataire par an", 0.0, 12.0, 1.0, 0.5, key="rl_v")
        x = S.rentabilite_locative(prix, frais, loyer, charges, vacance)
        conseils = [("Rentabilité nette correcte pour de l'immobilier résidentiel." if x["rentabilite_nette"] >= 0.05
                     else "Rentabilité nette faible : négociez le prix, ou comparez avec un placement sans gestion."),
                    "Les loyers sont soumis à l'IR (revenus fonciers) : faites calculer l'impôt réel avant de décider."]
        return rapport(nom, categorie_de(nom), {"Prix d'achat": dh(prix), "Frais d'acquisition": dh(frais),
                                                "Loyer mensuel": dh(loyer), "Charges annuelles": dh(charges),
                                                "Vacance locative": f"{vacance:g} mois/an"},
                       {"Loyers encaissés par an": dh(x["loyers_annuels"]), "Rentabilité brute": pc(x["rentabilite_brute"]),
                        "Rentabilité nette (avant impôt)": pc(x["rentabilite_nette"]),
                        "Années pour amortir l'achat": f"{x['annees_pour_rembourser']} ans" if x["annees_pour_rembourser"] else "jamais"},
                       ["Rentabilité brute = loyer × 12 ÷ (prix + frais).",
                        "Rentabilité nette = (loyers encaissés − charges) ÷ (prix + frais)."],
                       ["Mathématiques financières de l'investissement locatif",
                        "Loi n° 67-12 régissant les rapports contractuels entre bailleurs et locataires (habitation)"],
                       conseils=conseils)
    if nom == "Énergie solaire (photovoltaïque)":
        kwc = c[0].number_input("Puissance installée (kWc)", 0.0, value=5.0, step=0.5, key="pvs_k")
        prod = c[1].number_input("Productible (kWh/kWc/an)", 500.0, 2500.0, 1800.0, 50.0, key="pvs_p",
                                 help="Selon la région et l'orientation : demandez l'étude de l'installateur.")
        prix = c[2].number_input("Prix du kWh évité (DH)", 0.0, value=1.2, step=0.05, key="pvs_px")
        cout = st.number_input("Coût de l'installation (DH)", 0.0, value=60_000.0, step=5_000.0, key="pvs_c")
        x = S.photovoltaique(kwc, prod, prix, cout)
        conseils = [f"Retour sur investissement en {x['retour_sur_investissement_ans']} ans" if x["retour_sur_investissement_ans"]
                    else "Pas de retour sur 25 ans : revoyez le dimensionnement ou le prix.",
                    "Dimensionnez sur votre consommation de jour : l'énergie autoconsommée vaut plus que l'énergie injectée.",
                    "Cadre légal de l'autoproduction : loi n° 82-21 relative à l'autoproduction d'énergie électrique."]
        return rapport(nom, categorie_de(nom), {"Puissance": f"{kwc:g} kWc", "Productible": f"{prod:g} kWh/kWc/an",
                                                "Prix du kWh évité": dh(prix), "Coût": dh(cout)},
                       {"Production la 1re année": f"{x['production_an1']:,.0f} kWh".replace(",", " "),
                        "Économie la 1re année": dh(x["economie_an1"]),
                        "Retour sur investissement": f"{x['retour_sur_investissement_ans']} ans" if x["retour_sur_investissement_ans"] else "au-delà de 25 ans",
                        "Gain net sur 25 ans": dh(x["gain_total"])},
                       ["Production = puissance × productible, diminuée de 0,5 % par an (vieillissement des panneaux).",
                        "Économie = production × prix du kWh évité ; gain cumulé = économies − coût d'installation."],
                       ["Loi n° 82-21 relative à l'autoproduction d'énergie électrique", "Physique : énergie = puissance × temps"],
                       tableau=x["tableau"], conseils=conseils)
    if nom == "Croissance et projection (TCAM)":
        v0 = c[0].number_input("Valeur de départ", 0.0, value=1_000_000.0, step=50_000.0, key="cr_v0")
        v1 = c[1].number_input("Valeur d'arrivée", 0.0, value=1_500_000.0, step=50_000.0, key="cr_v1")
        n = c[2].number_input("Nombre d'années", 1, 50, 4, key="cr_n")
        x = S.croissance(v0, v1, n)
        conseils = ["Une projection prolonge le passé : confrontez-la au marché, aux capacités de production et au "
                    "financement avant d'en faire un budget."]
        return rapport(nom, categorie_de(nom), {"Valeur de départ": f"{v0:,.0f}".replace(",", " "),
                                                "Valeur d'arrivée": f"{v1:,.0f}".replace(",", " "), "Années": n},
                       {"Taux de croissance annuel moyen": pc(x["tcam"])},
                       ["TCAM = (valeur d'arrivée ÷ valeur de départ)^(1 ÷ années) − 1.",
                        "Projection : valeur × (1 + TCAM) chaque année."],
                       ["Statistiques descriptives (taux de croissance composé)"], tableau=x["tableau"], conseils=conseils)
    from .espace_simulations_plus import construire_plus
    return construire_plus(nom, memoire, c)
