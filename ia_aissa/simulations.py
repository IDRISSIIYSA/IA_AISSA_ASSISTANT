"""
Les simulations d'IA AISSA : des calculs exacts, sans moteur externe, pour décider.

Crédit (échéancier), épargne et intérêts composés, amortissement linéaire ou dégressif (coefficients marocains),
rentabilité d'un investissement (VAN, TRI, délai de récupération), prix de vente et marges, trésorerie sur 12 mois,
risque de perte par la méthode de Monte-Carlo, auto-entrepreneur ; en plus de la paie, de l'IR, de l'IS, de la TVA,
du seuil de rentabilité, des droits de douane et du stock optimal (Wilson) de la base de connaissances.
"""

import numpy as np
import pandas as pd

from . import connaissances as K

# Coefficients de l'amortissement dégressif au Maroc (CGI) selon la durée d'amortissement
COEFFICIENTS_DEGRESSIFS = [(4, 1.5), (6, 2.0), (float("inf"), 3.0)]


MOIS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def ajouter_mois(date, n):
    """La même date n mois plus tard (le jour est ramené au dernier jour du mois s'il n'existe pas)."""
    import calendar
    import datetime
    m = date.month - 1 + n
    annee, mois = date.year + m // 12, m % 12 + 1
    return datetime.date(annee, mois, min(date.day, calendar.monthrange(annee, mois)[1]))


def libelle_mois(date):
    return f"{MOIS_FR[date.month - 1]} {date.year}"


def echeancier_credit(capital, taux_annuel, duree_mois, date_deblocage=None, differe_mois=0, assurance_mensuelle=0.0):
    """Tableau d'amortissement d'un crédit à mensualités constantes, daté si la date de déblocage est donnée.

    Différé partiel : pendant les premiers mois, seuls les intérêts sont payés ; la mensualité constante est
    calculée sur les mois restants. Première échéance un mois après le déblocage."""
    t = taux_annuel / 12
    duree_mois, differe_mois = int(duree_mois), int(min(differe_mois, max(0, int(duree_mois) - 1)))
    n = duree_mois - differe_mois
    mensualite = capital / n if t == 0 else capital * t / (1 - (1 + t) ** -n)
    lignes, restant = [], float(capital)
    for mois in range(1, duree_mois + 1):
        interets = restant * t
        paye = interets if mois <= differe_mois else mensualite
        amorti = paye - interets
        restant = max(0.0, restant - amorti)
        ligne = {"Mois": mois}
        if date_deblocage is not None:
            echeance = ajouter_mois(date_deblocage, mois)
            ligne["Échéance"] = echeance.strftime("%d/%m/%Y")
            ligne["Année"] = echeance.year
        ligne.update({"Mensualité": round(paye, 2), "Intérêts": round(interets, 2), "Capital remboursé": round(amorti, 2),
                      "Capital restant dû": round(restant, 2)})
        if assurance_mensuelle:
            ligne["Assurance"] = round(assurance_mensuelle, 2)
            ligne["Total payé"] = round(paye + assurance_mensuelle, 2)
        lignes.append(ligne)
    tableau = pd.DataFrame(lignes)
    resultat = {"mensualite": round(mensualite, 2), "cout_total": round(tableau["Intérêts"].sum(), 2),
                "total_rembourse": round(tableau["Mensualité"].sum(), 2), "tableau": tableau}
    if date_deblocage is not None:
        resultat["premiere_echeance"] = tableau["Échéance"].iloc[0]
        resultat["derniere_echeance"] = tableau["Échéance"].iloc[-1]
        resultat["par_annee"] = (tableau.groupby("Année")[["Mensualité", "Intérêts", "Capital remboursé"]].sum().round(2)
                                 .reset_index())
    return resultat


def epargne(versement_mensuel, taux_annuel, annees, capital_initial=0.0, annee_debut=None):
    """Capital obtenu en épargnant chaque mois, intérêts composés mensuellement."""
    t, capital, lignes = taux_annuel / 12, float(capital_initial), []
    for annee in range(1, int(annees) + 1):
        for _ in range(12):
            capital = capital * (1 + t) + versement_mensuel
        verse = capital_initial + versement_mensuel * 12 * annee
        ligne = {"Année": annee}
        if annee_debut:
            ligne["Fin d'année"] = f"31/12/{int(annee_debut) + annee - 1}"
        ligne.update({"Total versé": round(verse, 2), "Capital": round(capital, 2),
                      "Intérêts gagnés": round(capital - verse, 2)})
        lignes.append(ligne)
    tableau = pd.DataFrame(lignes)
    return {"capital_final": round(capital, 2), "total_verse": round(capital_initial + versement_mensuel * 12 * annees, 2),
            "interets": round(capital - capital_initial - versement_mensuel * 12 * annees, 2), "tableau": tableau}


def amortissement(valeur, duree_ans, methode="lineaire", mois_mise_en_service=1, annee_mise_en_service=None,
                  valeur_residuelle=0.0):
    """Plan d'amortissement linéaire, ou dégressif avec passage au linéaire quand il devient plus avantageux.

    Point de départ : le premier jour du mois d'acquisition ou de mise en service (CGI, art. 10-I-F-1-b) ; la première
    annuité est donc calculée au prorata des mois, et le plan s'allonge d'un exercice si le bien n'est pas acquis en
    janvier. Exercices supposés calés sur l'année civile."""
    duree_ans, mois_mise_en_service = int(duree_ans), int(mois_mise_en_service)
    base = float(valeur) - float(valeur_residuelle)
    lignes, vnc, mois_restants = [], base, duree_ans * 12
    if methode == "degressif":
        coef = next(c for d, c in COEFFICIENTS_DEGRESSIFS if duree_ans <= d)
        taux = coef / duree_ans
    k = 0
    while mois_restants > 0 and vnc > 0.005:
        mois = min(13 - mois_mise_en_service if k == 0 else 12, mois_restants)
        lineaire = vnc * mois / mois_restants if methode == "degressif" else base * mois / (duree_ans * 12)
        dotation = max(vnc * taux * mois / 12, lineaire) if methode == "degressif" else lineaire
        dotation = min(dotation, vnc)
        vnc -= dotation
        mois_restants -= mois
        ligne = {"Année": k + 1}
        if annee_mise_en_service:
            ligne["Exercice"] = int(annee_mise_en_service) + k
        ligne.update({"Mois amortis": mois, "Dotation": round(dotation, 2),
                      "Cumul des amortissements": round(base - vnc, 2),
                      "Valeur nette comptable": round(vnc + float(valeur_residuelle), 2)})
        lignes.append(ligne)
        k += 1
    resultat = {"methode": methode, "tableau": pd.DataFrame(lignes), "exercices": len(lignes)}
    if methode == "degressif":
        resultat.update(coefficient=coef, taux=round(taux, 4))
    return resultat


def rentabilite_investissement(investissement, flux, taux_actualisation):
    """VAN, TRI (par dichotomie) et délai de récupération (non actualisé)."""
    van = K.calculer_van(investissement, flux, taux_actualisation)["van"]

    def van_a(t):
        return -investissement + sum(f / (1 + t) ** (i + 1) for i, f in enumerate(flux))
    tri = None
    bas, haut = -0.99, 10.0
    if van_a(bas) * van_a(haut) < 0:
        for _ in range(200):
            milieu = (bas + haut) / 2
            if van_a(bas) * van_a(milieu) <= 0:
                haut = milieu
            else:
                bas = milieu
        tri = round((bas + haut) / 2, 4)
    cumul, delai = -investissement, None
    for annee, f in enumerate(flux, 1):
        if cumul + f >= 0 and delai is None:
            delai = round(annee - 1 + (-cumul) / f, 2) if f else annee
        cumul += f
    return {"van": van, "tri": tri, "delai_recuperation_ans": delai,
            "decision": "Projet rentable" if van > 0 else "Projet non rentable à ce taux"}


def prix_de_vente(cout_de_revient, taux_marge_sur_cout=None, taux_de_marque=None, tva=0.2):
    """Prix de vente HT et TTC à partir d'un taux de marge (sur le coût) ou d'un taux de marque (sur le prix)."""
    if taux_de_marque is not None:
        ht = cout_de_revient / (1 - taux_de_marque)
    else:
        ht = cout_de_revient * (1 + (taux_marge_sur_cout or 0))
    marge = ht - cout_de_revient
    return {"prix_ht": round(ht, 2), "prix_ttc": round(ht * (1 + tva), 2), "marge": round(marge, 2),
            "taux_de_marge": round(marge / cout_de_revient, 4) if cout_de_revient else None,
            "taux_de_marque": round(marge / ht, 4) if ht else None}


def tresorerie(solde_initial, encaissements, decaissements, premier_mois=None):
    """Plan de trésorerie mois par mois : solde de fin de mois et premier mois à découvert (daté si premier_mois)."""
    lignes, solde = [], float(solde_initial)
    for mois, (e, d) in enumerate(zip(encaissements, decaissements), 1):
        solde += e - d
        ligne = {"Mois": mois}
        if premier_mois is not None:
            ligne["Période"] = libelle_mois(ajouter_mois(premier_mois.replace(day=1), mois - 1))
        ligne.update({"Encaissements": e, "Décaissements": d, "Flux net": round(e - d, 2),
                      "Solde fin de mois": round(solde, 2)})
        lignes.append(ligne)
    tableau = pd.DataFrame(lignes)
    negatifs = tableau[tableau["Solde fin de mois"] < 0]
    return {"solde_final": round(solde, 2), "solde_minimum": round(float(tableau["Solde fin de mois"].min()), 2),
            "premier_mois_a_decouvert": int(negatifs["Mois"].iloc[0]) if not negatifs.empty else None,
            "periode_decouvert": (negatifs["Période"].iloc[0] if "Période" in negatifs and not negatifs.empty else None),
            "besoin_maximal": round(max(0.0, -float(tableau["Solde fin de mois"].min())), 2), "tableau": tableau}


def risque_monte_carlo(ca_min, ca_max, taux_cv_min, taux_cv_max, charges_fixes, n=10_000, graine=0):
    """Résultat incertain : chiffre d'affaires et taux de coûts variables tirés au hasard dans leurs fourchettes
    (lois uniformes) ; probabilité de perte et fourchette du résultat."""
    rng = np.random.default_rng(graine)
    ca = rng.uniform(ca_min, ca_max, n)
    taux = rng.uniform(taux_cv_min, taux_cv_max, n)
    resultat = ca * (1 - taux) - charges_fixes
    return {"simulations": n, "resultat_moyen": round(float(resultat.mean()), 2),
            "probabilite_de_perte": round(float((resultat < 0).mean()), 4),
            "p5": round(float(np.percentile(resultat, 5)), 2), "p95": round(float(np.percentile(resultat, 95)), 2),
            "resultats": resultat}


def auto_entrepreneur(chiffre_affaires, activite="services"):
    """Impôt de l'auto-entrepreneur : 0,5 % (commerce, industrie, artisanat) ou 1 % (services) du chiffre d'affaires,
    dans la limite des plafonds (500 000 DH / 200 000 DH)."""
    activite = "commerce" if activite.startswith(("comm", "indus", "artis")) else "services"
    plafond, taux = K.PLAFOND_AE[activite], K.TAUX_AE[activite]
    return {"activite": activite, "impot": round(chiffre_affaires * taux, 2), "taux": taux, "plafond": plafond,
            "depasse_le_plafond": chiffre_affaires > plafond}


CATALOGUE = [
    ("💼", "Paie", "brut ↔ net, CNSS, AMO, IR, coût employeur"),
    ("🏦", "Crédit", "mensualité et tableau d'amortissement"),
    ("🐖", "Épargne", "intérêts composés, versements mensuels"),
    ("🏭", "Amortissement", "linéaire ou dégressif (coefficients marocains)"),
    ("📈", "Investissement", "VAN, TRI, délai de récupération"),
    ("⚖️", "Seuil de rentabilité", "quantité et chiffre d'affaires"),
    ("🏷️", "Prix de vente", "taux de marge, taux de marque, TTC"),
    ("💧", "Trésorerie", "plan sur 12 mois, premier mois à découvert"),
    ("🎲", "Risque (Monte-Carlo)", "probabilité de perte selon l'incertitude"),
    ("🧾", "Impôts", "TVA (due ou crédit), IS avec cotisation minimale, IR"),
    ("🧑‍💻", "Auto-entrepreneur", "impôt 0,5 % ou 1 % et plafonds"),
    ("🚢", "Douane", "droits d'importation et TVA à l'import"),
    ("📦", "Stock", "quantité économique de commande (Wilson)"),
]


# ==========================================
# Ressources humaines (Code du travail marocain, loi n° 65-99)
# ==========================================
def heures_supplementaires(taux_horaire, heures_jour, heures_nuit=0.0, heures_repos_jour=0.0, heures_repos_nuit=0.0):
    """Majoration (art. 201) : 25 % de 6 h à 21 h, 50 % de 21 h à 6 h ; le jour du repos hebdomadaire : 50 % et 100 %."""
    lignes = [("Jour ouvrable, 6 h – 21 h", heures_jour, 0.25), ("Jour ouvrable, 21 h – 6 h", heures_nuit, 0.50),
              ("Repos hebdomadaire, 6 h – 21 h", heures_repos_jour, 0.50),
              ("Repos hebdomadaire, 21 h – 6 h", heures_repos_nuit, 1.00)]
    tableau = pd.DataFrame([{"Période": p, "Heures": h, "Majoration": f"{m:.0%}",
                             "Montant": round(h * taux_horaire * (1 + m), 2)} for p, h, m in lignes if h])
    return {"total": round(float(tableau["Montant"].sum()) if len(tableau) else 0.0, 2), "tableau": tableau}


def indemnite_licenciement(salaire_horaire_moyen, annees):
    """Art. 53 : 96 h de salaire par année pour les 5 premières années, 144 h de la 6e à la 10e, 192 h de la 11e à la
    15e, 240 h au-delà (hors faute grave)."""
    tranches = [(5, 96), (10, 144), (15, 192), (float("inf"), 240)]
    heures, debut, detail = 0.0, 0, []
    for fin, h in tranches:
        n = max(0.0, min(annees, fin) - debut)
        if n > 0:
            detail.append({"Années": f"{debut + 1} à {int(min(annees, fin)) if fin != float('inf') else int(annees)}",
                           "Nombre d'années": n, "Heures par année": h, "Heures": n * h})
            heures += n * h
        debut = fin
        if annees <= fin:
            break
    return {"heures": heures, "indemnite": round(heures * salaire_horaire_moyen, 2), "tableau": pd.DataFrame(detail)}


def conges_payes(mois_de_service, annees_anciennete=0):
    """Art. 231 et 241 : 1,5 jour ouvrable par mois de service, plus 1,5 jour par période de 5 ans d'ancienneté,
    dans la limite de 30 jours ouvrables."""
    base = 1.5 * min(mois_de_service, 12)
    bonus = 1.5 * (annees_anciennete // 5)
    return {"jours": min(30.0, base + bonus), "base": base, "anciennete": bonus}


# ==========================================
# Banque et finance
# ==========================================
def capacite_emprunt(revenu_mensuel, charges_credits_existants, taux_annuel, duree_mois, taux_endettement=0.40):
    """Mensualité maximale = revenu × taux d'endettement − crédits en cours ; capital empruntable correspondant."""
    mensualite = max(0.0, revenu_mensuel * taux_endettement - charges_credits_existants)
    t = taux_annuel / 12
    capital = mensualite * duree_mois if t == 0 else mensualite * (1 - (1 + t) ** -duree_mois) / t
    return {"mensualite_max": round(mensualite, 2), "capital_max": round(capital, 2)}


def besoin_fonds_roulement(stocks, creances_clients, dettes_fournisseurs, chiffre_affaires_ht):
    """BFR = stocks + créances clients − dettes fournisseurs ; exprimé aussi en jours de chiffre d'affaires."""
    bfr = stocks + creances_clients - dettes_fournisseurs
    return {"bfr": round(bfr, 2), "jours_de_ca": round(bfr / chiffre_affaires_ht * 360, 1) if chiffre_affaires_ht else None}


# ==========================================
# Technique et bâtiment
# ==========================================
def consommation_electrique(puissance_watts, heures_par_jour, jours, prix_kwh):
    kwh = puissance_watts / 1000 * heures_par_jour * jours
    return {"kwh": round(kwh, 2), "cout": round(kwh * prix_kwh, 2)}


def beton(longueur, largeur, epaisseur, dosage_ciment_kg=350):
    """Volume de béton et quantités indicatives pour 1 m³ de béton courant dosé à 350 kg : environ 400 L de sable,
    800 L de gravier et 175 L d'eau (dosages usuels de chantier)."""
    volume = longueur * largeur * epaisseur
    return {"volume_m3": round(volume, 3), "ciment_kg": round(volume * dosage_ciment_kg, 1),
            "sacs_ciment_50kg": int(-(-volume * dosage_ciment_kg // 50)), "sable_m3": round(volume * 0.4, 3),
            "gravier_m3": round(volume * 0.8, 3), "eau_litres": round(volume * 175, 1)}


def peinture(surface_m2, couches=2, rendement_m2_par_litre=10.0):
    litres = surface_m2 * couches / rendement_m2_par_litre
    return {"litres": round(litres, 2)}


def carrelage(surface_m2, longueur_carreau_cm, largeur_carreau_cm, chutes=0.10):
    surface_carreau = longueur_carreau_cm * largeur_carreau_cm / 10_000
    a_commander = surface_m2 * (1 + chutes)
    return {"surface_a_commander_m2": round(a_commander, 2), "carreaux": int(-(-a_commander // surface_carreau))}


def paie_complete(salaire_base, anciennete_ans=0, personnes_a_charge=0, deduction_par_personne_an=500.0,
                  indemnites_exonerees=0.0, heures_mois=K.HEURES_LEGALES_MOIS):
    """Bulletin complet : prime d'ancienneté (art. 350), CNSS/AMO, frais professionnels, IR avec charges de famille
    (au plus 6 personnes), toutes les charges patronales (CNSS, allocations familiales, AMO, formation
    professionnelle), contrôle du SMIG."""
    taux_prime = K.taux_prime_anciennete(anciennete_ans)
    prime = salaire_base * taux_prime
    brut = salaire_base + prime
    cnss = min(brut, K.PLAFOND_CNSS_MENSUEL) * K.CNSS_SALARIE
    amo = brut * K.AMO_SALARIE
    taux_fp = next(t for plafond, t in K.FRAIS_PRO if brut * 12 <= plafond)
    frais_pro = min(brut * taux_fp, K.PLAFOND_FRAIS_PRO_ANNUEL / 12)
    net_imposable = max(0.0, brut - cnss - amo - frais_pro)
    ir_brut = K.calculer_ir(net_imposable * 12)["ir_annuel"] / 12
    deduction_famille = min(personnes_a_charge, 6) * deduction_par_personne_an / 12
    ir = max(0.0, ir_brut - deduction_famille)
    net = brut - cnss - amo - ir + indemnites_exonerees
    patronal = {"CNSS (prestations, plafonnée)": min(brut, K.PLAFOND_CNSS_MENSUEL) * K.CNSS_EMPLOYEUR,
                "Allocations familiales": brut * K.ALLOCATIONS_FAMILIALES_EMPLOYEUR,
                "AMO": brut * K.AMO_EMPLOYEUR, "Formation professionnelle": brut * K.TAXE_FORMATION_PROFESSIONNELLE}
    total_patronal = sum(patronal.values())
    return {"salaire_base": salaire_base, "taux_prime": taux_prime, "prime_anciennete": round(prime, 2),
            "brut": round(brut, 2), "cnss": round(cnss, 2), "amo": round(amo, 2), "frais_pro": round(frais_pro, 2),
            "taux_frais_pro": taux_fp, "net_imposable": round(net_imposable, 2), "ir_avant_famille": round(ir_brut, 2),
            "deduction_famille": round(deduction_famille, 2), "ir": round(ir, 2),
            "indemnites_exonerees": indemnites_exonerees, "net": round(net, 2),
            "patronal": {k: round(v, 2) for k, v in patronal.items()}, "total_patronal": round(total_patronal, 2),
            "cout_employeur": round(brut + total_patronal + indemnites_exonerees, 2),
            "taux_horaire_base": round(salaire_base / heures_mois, 2),
            "sous_smig": salaire_base / heures_mois < K.SMIG_HORAIRE_2026}


# ==========================================
# Immobilier, énergie, statistiques
# ==========================================
def rentabilite_locative(prix_achat, frais_acquisition, loyer_mensuel, charges_annuelles, vacance_mois=1.0):
    loyers = loyer_mensuel * (12 - vacance_mois)
    cout = prix_achat + frais_acquisition
    return {"loyers_annuels": round(loyers, 2), "rentabilite_brute": round(loyer_mensuel * 12 / cout, 4) if cout else 0,
            "rentabilite_nette": round((loyers - charges_annuelles) / cout, 4) if cout else 0,
            "annees_pour_rembourser": round(cout / (loyers - charges_annuelles), 1) if loyers > charges_annuelles else None}


def photovoltaique(puissance_kwc, production_kwh_par_kwc, prix_kwh, cout_installation, perte_annuelle=0.005, annees=25):
    """Production annuelle = puissance × productible (kWh/kWc/an) ; économies actualisées sur la durée de vie."""
    lignes, cumul = [], -cout_installation
    for a in range(1, annees + 1):
        production = puissance_kwc * production_kwh_par_kwc * (1 - perte_annuelle) ** (a - 1)
        cumul += production * prix_kwh
        lignes.append({"Année": a, "Production (kWh)": round(production, 0), "Économie": round(production * prix_kwh, 2),
                       "Gain cumulé": round(cumul, 2)})
    tableau = pd.DataFrame(lignes)
    retour = tableau[tableau["Gain cumulé"] >= 0]
    return {"production_an1": round(puissance_kwc * production_kwh_par_kwc, 0),
            "economie_an1": round(puissance_kwc * production_kwh_par_kwc * prix_kwh, 2),
            "retour_sur_investissement_ans": int(retour["Année"].iloc[0]) if not retour.empty else None,
            "gain_total": round(cumul, 2), "tableau": tableau}


def croissance(valeur_debut, valeur_fin, annees, projection_annees=3):
    """Taux de croissance annuel moyen (TCAM) et projection au même rythme."""
    tcam = (valeur_fin / valeur_debut) ** (1 / annees) - 1 if valeur_debut > 0 and annees > 0 else 0.0
    projection = pd.DataFrame([{"Année": f"+{i}", "Valeur projetée": round(valeur_fin * (1 + tcam) ** i, 2)}
                               for i in range(1, projection_annees + 1)])
    return {"tcam": round(tcam, 4), "tableau": projection}


# ==========================================
# Fiscalité : dividendes, pénalités de retard
# ==========================================
# Retenue à la source sur les dividendes (CGI, art. 19-IV, 73-II et 247-XXXVII-C) : 15 % depuis la LF 2013, puis baisse
# progressive (LF 2023), calendrier décalé d'un an par la LF 2025 ; taux selon la date de mise en distribution.
RAS_DIVIDENDES = {**{a: 0.15 for a in range(2013, 2023)}, 2023: 0.1375, 2024: 0.125, 2025: 0.125, 2026: 0.1125,
                  2027: 0.10}


def retenue_dividendes(montant_brut, annee):
    if annee not in RAS_DIVIDENDES:
        raise ValueError(f"Taux de retenue sur dividendes {annee} non vérifié : je ne l'invente pas.")
    taux = RAS_DIVIDENDES[annee]
    return {"taux": taux, "retenue": round(montant_brut * taux, 2), "net": round(montant_brut * (1 - taux), 2)}


def penalites_retard(principal, mois_de_retard, jours_de_retard_total=None):
    """CGI, art. 208 : pénalité de 10 % (5 % si le retard ne dépasse pas 30 jours) et majoration de 5 % pour le premier
    mois de retard, plus 0,50 % par mois ou fraction de mois supplémentaire."""
    jours = jours_de_retard_total if jours_de_retard_total is not None else mois_de_retard * 30
    taux_penalite = 0.05 if jours <= 30 else 0.10
    mois = max(1, int(np.ceil(jours / 30))) if jours > 0 else 0
    taux_majoration = 0.05 + 0.005 * max(0, mois - 1) if mois else 0.0
    penalite, majoration = principal * taux_penalite * (jours > 0), principal * taux_majoration
    return {"mois": mois, "taux_penalite": taux_penalite if jours > 0 else 0.0, "penalite": round(penalite, 2),
            "taux_majoration": round(taux_majoration, 4), "majoration": round(majoration, 2),
            "total": round(principal + penalite + majoration, 2), "surcout": round(penalite + majoration, 2)}


# ==========================================
# RH : masse salariale, retraite CNSS
# ==========================================
def masse_salariale(effectif, salaire_base, anciennete_ans=0, mois_payes=12, augmentation=0.0, personnes_a_charge=0):
    """Coût annuel d'un effectif au même salaire (paie complète), avec une augmentation éventuelle."""
    avant = paie_complete(salaire_base, anciennete_ans, personnes_a_charge)
    apres = paie_complete(salaire_base * (1 + augmentation), anciennete_ans, personnes_a_charge)
    lignes = [{"Scénario": nom, "Brut mensuel": p["brut"], "Net mensuel": p["net"], "Coût employeur mensuel":
               p["cout_employeur"], "Coût annuel de l'effectif": round(p["cout_employeur"] * effectif * mois_payes, 2)}
              for nom, p in (("Actuel", avant), (f"Après +{augmentation:.1%}", apres))]
    return {"actuel": avant, "apres": apres, "cout_annuel": lignes[0]["Coût annuel de l'effectif"],
            "cout_annuel_apres": lignes[1]["Coût annuel de l'effectif"],
            "surcout": round(lignes[1]["Coût annuel de l'effectif"] - lignes[0]["Coût annuel de l'effectif"], 2),
            "gain_net_salarie": round((apres["net"] - avant["net"]) * mois_payes, 2), "tableau": pd.DataFrame(lignes)}


def pension_cnss(salaire_moyen_mensuel, jours_declares):
    """Pension de vieillesse CNSS : 50 % du salaire moyen (plafonné à 6 000 DH) pour 3 240 jours, + 1 % par tranche
    de 216 jours supplémentaires, au plus 70 %."""
    base = min(salaire_moyen_mensuel, K.PLAFOND_CNSS_MENSUEL)
    if jours_declares < 3240:
        return {"eligible": False, "base": base, "taux": 0.0, "pension": 0.0, "jours_manquants": 3240 - jours_declares}
    taux = min(0.70, 0.50 + 0.01 * ((jours_declares - 3240) // 216))
    jours_pour_70 = 3240 + 20 * 216
    return {"eligible": True, "base": base, "taux": taux, "pension": round(base * taux, 2), "jours_manquants": 0,
            "jours_pour_70": max(0, jours_pour_70 - jours_declares), "remplacement": round(base * taux / salaire_moyen_mensuel, 4)
            if salaire_moyen_mensuel else 0}


# ==========================================
# Comptabilité : ratios, coût de revient
# ==========================================
def ratios_financiers(actif_circulant, stocks, tresorerie, dettes_court_terme, capitaux_propres, dettes_financieres,
                      chiffre_affaires, resultat_net, total_actif):
    def div(a, b):
        return round(a / b, 4) if b else None
    r = {"Liquidité générale": (div(actif_circulant, dettes_court_terme), 1.0, "≥ 1 : l'actif à court terme couvre les dettes à court terme"),
         "Liquidité réduite": (div(actif_circulant - stocks, dettes_court_terme), 0.8, "≥ 0,8 sans compter les stocks"),
         "Liquidité immédiate": (div(tresorerie, dettes_court_terme), 0.2, "≥ 0,2 en trésorerie disponible"),
         "Autonomie financière": (div(capitaux_propres, total_actif), 0.3, "≥ 30 % de fonds propres"),
         "Endettement (gearing)": (div(dettes_financieres, capitaux_propres), 1.0, "≤ 1 : dettes financières ≤ fonds propres"),
         "Marge nette": (div(resultat_net, chiffre_affaires), 0.05, "≥ 5 % selon le secteur"),
         "Rentabilité des fonds propres (ROE)": (div(resultat_net, capitaux_propres), 0.10, "≥ 10 %")}
    lignes = []
    for nom, (v, seuil, norme) in r.items():
        bon = None if v is None else (v <= seuil if nom.startswith("Endettement") else v >= seuil)
        lignes.append({"Ratio": nom, "Valeur": v, "Repère": norme, "Appréciation": "—" if bon is None else ("✅" if bon else "⚠️")})
    return {"ratios": {k: v[0] for k, v in r.items()}, "faibles": [l["Ratio"] for l in lignes if l["Appréciation"] == "⚠️"],
            "tableau": pd.DataFrame(lignes)}


def cout_de_revient(matieres, main_oeuvre_directe, charges_indirectes, frais_distribution, quantite, prix_vente_unitaire):
    total = matieres + main_oeuvre_directe + charges_indirectes + frais_distribution
    unitaire = total / quantite if quantite else 0.0
    lignes = [{"Élément": n, "Montant": round(v, 2), "Part": round(v / total, 4) if total else 0}
              for n, v in (("Matières", matieres), ("Main-d'œuvre directe", main_oeuvre_directe),
                           ("Charges indirectes", charges_indirectes), ("Distribution", frais_distribution))]
    return {"total": round(total, 2), "unitaire": round(unitaire, 2), "marge_unitaire": round(prix_vente_unitaire - unitaire, 2),
            "taux_marge": round((prix_vente_unitaire - unitaire) / prix_vente_unitaire, 4) if prix_vente_unitaire else 0,
            "poste_principal": max(lignes, key=lambda l: l["Montant"])["Élément"], "tableau": pd.DataFrame(lignes)}


# ==========================================
# Banque : TEG, leasing ou crédit
# ==========================================
def taux_effectif_global(capital, taux_nominal, duree_mois, frais_dossier=0.0, assurance_mensuelle=0.0):
    """TEG : taux annuel qui égalise le capital reçu net de frais et les mensualités réellement payées (assurance comprise)."""
    m = echeancier_credit(capital, taux_nominal, duree_mois)["mensualite"] + assurance_mensuelle
    recu = capital - frais_dossier

    def ecart(t):
        i = t / 12
        return sum(m / (1 + i) ** k for k in range(1, duree_mois + 1)) - recu
    bas, haut = 0.0, 1.0
    for _ in range(100):
        milieu = (bas + haut) / 2
        bas, haut = (milieu, haut) if ecart(milieu) > 0 else (bas, milieu)
    return {"mensualite_totale": round(m, 2), "teg": round((bas + haut) / 2, 4), "cout_total": round(m * duree_mois - recu, 2)}


def leasing_ou_credit(prix_ht, loyer_mensuel_ht, duree_mois, valeur_residuelle, taux_credit, taux_is, taux_actualisation):
    """Coût actualisé après impôt : loyers déductibles (leasing) contre amortissement linéaire et intérêts (crédit)."""
    i = taux_actualisation / 12
    acte = lambda mois: 1 / (1 + i) ** mois
    leasing = sum(loyer_mensuel_ht * (1 - taux_is) * acte(k) for k in range(1, duree_mois + 1)) + valeur_residuelle * acte(duree_mois)
    e = echeancier_credit(prix_ht, taux_credit, duree_mois)["tableau"]
    amort_mensuel = prix_ht / duree_mois
    credit = sum((row["Mensualité"] - (row["Intérêts"] + amort_mensuel) * taux_is) * acte(k)
                 for k, row in enumerate(e.to_dict("records"), start=1))
    return {"leasing": round(leasing, 2), "credit": round(credit, 2), "meilleur": "Leasing" if leasing < credit else "Crédit",
            "ecart": round(abs(leasing - credit), 2)}


# ==========================================
# Finance : valorisation, effet de levier
# ==========================================
def valorisation_dcf(flux_annuels, taux_actualisation, croissance_infinie, dette_nette):
    """Valeur d'entreprise = flux actualisés + valeur terminale (Gordon-Shapiro) ; valeur des titres = VE − dette nette."""
    actualises = [f / (1 + taux_actualisation) ** (k + 1) for k, f in enumerate(flux_annuels)]
    terminale = flux_annuels[-1] * (1 + croissance_infinie) / (taux_actualisation - croissance_infinie) \
        if taux_actualisation > croissance_infinie else float("nan")
    terminale_act = terminale / (1 + taux_actualisation) ** len(flux_annuels)
    ve = sum(actualises) + terminale_act
    tableau = pd.DataFrame([{"Année": k + 1, "Flux": f, "Flux actualisé": round(a, 2)}
                            for k, (f, a) in enumerate(zip(flux_annuels, actualises))])
    return {"valeur_entreprise": round(ve, 2), "valeur_terminale_actualisee": round(terminale_act, 2),
            "part_terminale": round(terminale_act / ve, 4) if ve else 0, "valeur_titres": round(ve - dette_nette, 2),
            "tableau": tableau}


def effet_de_levier(resultat_exploitation, actif_economique, dette, taux_interet, taux_is):
    """ROE = [ROA + (ROA − i) × D/CP] × (1 − IS)."""
    cp = actif_economique - dette
    roa = resultat_exploitation / actif_economique if actif_economique else 0
    roe = (roa + (roa - taux_interet) * (dette / cp)) * (1 - taux_is) if cp > 0 else None
    return {"rentabilite_economique": round(roa, 4), "capitaux_propres": cp, "levier": round(dette / cp, 2) if cp > 0 else None,
            "rentabilite_financiere": round(roe, 4) if roe is not None else None, "favorable": roa > taux_interet}


# ==========================================
# Technique : câble électrique, pompe
# ==========================================
SECTIONS_NORMALISEES = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240]


def section_cable(puissance_w, tension_v, longueur_m, chute_max=0.03, triphase=False, cuivre=True, cos_phi=1.0):
    """Section minimale par la chute de tension : S = b × ρ × L × I ÷ ΔU (b = 2 en monophasé, 1 en triphasé ; ρ cuivre
    0,0225, aluminium 0,036 Ω·mm²/m en service)."""
    rho = 0.0225 if cuivre else 0.036
    courant = puissance_w / ((3 ** 0.5 if triphase else 1) * tension_v * cos_phi)
    b = 1 if triphase else 2
    s_min = b * rho * longueur_m * courant * cos_phi / (chute_max * tension_v)
    s = next((x for x in SECTIONS_NORMALISEES if x >= s_min), None)
    chute = b * rho * longueur_m * courant * cos_phi / s / tension_v if s else None
    return {"courant": round(courant, 2), "section_calculee": round(s_min, 2), "section_normalisee": s,
            "chute_reelle": round(chute, 4) if chute else None}


def puissance_pompe(debit_m3h, hauteur_m, rendement=0.6, heures_jour=8, prix_kwh=1.2):
    """P hydraulique = ρ × g × Q × H ; P absorbée = P hydraulique ÷ rendement."""
    p_hydr = 1000 * 9.81 * debit_m3h / 3600 * hauteur_m
    p_abs = p_hydr / rendement if rendement else 0
    energie = p_abs / 1000 * heures_jour * 365
    return {"p_hydraulique_kw": round(p_hydr / 1000, 3), "p_absorbee_kw": round(p_abs / 1000, 3),
            "energie_an_kwh": round(energie, 0), "cout_an": round(energie * prix_kwh, 2)}


# ==========================================
# Bâtiment : acier, maçonnerie
# ==========================================
def ferraillage(barres):
    """barres : [(diamètre en mm, nombre, longueur unitaire en m)] ; masse linéique = d² ÷ 162 kg/m (acier 7 850 kg/m³)."""
    lignes = [{"Diamètre (mm)": d, "Nombre": n, "Longueur unitaire (m)": l, "Longueur totale (m)": round(n * l, 2),
               "kg/m": round(d * d / 162, 3), "Masse (kg)": round(n * l * d * d / 162, 2)} for d, n, l in barres]
    return {"masse": round(sum(l["Masse (kg)"] for l in lignes), 2), "tableau": pd.DataFrame(lignes)}


def maconnerie(surface_m2, ouvertures_m2, longueur_bloc_cm=40, hauteur_bloc_cm=20, joint_cm=1, perte=0.05):
    nette = max(0.0, surface_m2 - ouvertures_m2)
    par_m2 = 10_000 / ((longueur_bloc_cm + joint_cm) * (hauteur_bloc_cm + joint_cm))
    blocs = int(np.ceil(nette * par_m2 * (1 + perte)))
    mortier = nette * 0.02                   # ≈ 20 L de mortier par m² pour des blocs de 20 cm
    return {"surface_nette": round(nette, 2), "par_m2": round(par_m2, 2), "blocs": blocs, "mortier_m3": round(mortier, 3),
            "ciment_sacs": int(np.ceil(mortier * 300 / 50))}


# ==========================================
# Immobilier : frais d'acquisition, acheter ou louer
# ==========================================
def frais_acquisition(prix, taux_enregistrement=0.04, taux_conservation=0.015, frais_fixes=0.0, honoraires_notaire_ttc=0.0):
    enreg, conserv = prix * taux_enregistrement, prix * taux_conservation
    total = enreg + conserv + frais_fixes + honoraires_notaire_ttc
    return {"enregistrement": round(enreg, 2), "conservation": round(conserv, 2), "total": round(total, 2),
            "part": round(total / prix, 4) if prix else 0, "cout_complet": round(prix + total, 2)}


def acheter_ou_louer(prix, frais, apport, taux_credit, duree_ans, loyer_mensuel, hausse_loyer, valorisation_bien,
                     rendement_placement, charges_proprietaire_an=0.0):
    """Patrimoine comparé après la durée : propriétaire (valeur du bien) ou locataire (apport et économies placés)."""
    capital = max(0.0, prix + frais - apport)
    mensualite = echeancier_credit(capital, taux_credit, duree_ans * 12)["mensualite"] if capital else 0.0
    placement, lignes = apport, []
    for a in range(1, duree_ans + 1):
        loyer = loyer_mensuel * 12 * (1 + hausse_loyer) ** (a - 1)
        effort_proprio = mensualite * 12 + charges_proprietaire_an
        placement = placement * (1 + rendement_placement) + (effort_proprio - loyer)
        lignes.append({"Année": a, "Loyer payé": round(loyer, 2), "Effort propriétaire": round(effort_proprio, 2),
                       "Valeur du bien": round(prix * (1 + valorisation_bien) ** a, 2),
                       "Placement du locataire": round(placement, 2)})
    bien = prix * (1 + valorisation_bien) ** duree_ans
    return {"mensualite": round(mensualite, 2), "patrimoine_proprietaire": round(bien, 2),
            "patrimoine_locataire": round(placement, 2), "meilleur": "Acheter" if bien >= placement else "Louer",
            "tableau": pd.DataFrame(lignes)}


# ==========================================
# Énergie : chauffe-eau solaire, groupe électrogène
# ==========================================
def chauffe_eau_solaire(litres_jour, temperature_froide, temperature_chaude, couverture_solaire, prix_kwh, cout_installation,
                        rendement_appoint=0.95):
    """Énergie = m × c × ΔT (c = 1,163 Wh/kg/°C) ; économie = part couverte par le soleil."""
    besoin = litres_jour * 1.163 * (temperature_chaude - temperature_froide) / 1000 * 365 / rendement_appoint
    economie = besoin * couverture_solaire * prix_kwh
    return {"besoin_kwh_an": round(besoin, 0), "economie_an": round(economie, 2),
            "retour_ans": round(cout_installation / economie, 1) if economie else None}


def groupe_electrogene(puissance_kva, charge, heures_jour, jours_an, prix_gasoil, consommation_l_kwh=0.28, cos_phi=0.8):
    kw = puissance_kva * cos_phi * charge
    litres = kw * consommation_l_kwh * heures_jour * jours_an
    kwh = kw * heures_jour * jours_an
    return {"puissance_kw": round(kw, 2), "litres_an": round(litres, 0), "cout_an": round(litres * prix_gasoil, 2),
            "cout_kwh": round(litres * prix_gasoil / kwh, 2) if kwh else 0}


# ==========================================
# Statistiques : tendance, échantillon
# ==========================================
def tendance_lineaire(valeurs, periodes_a_prevoir=3):
    """Moindres carrés : y = a × t + b ; coefficient de détermination R²."""
    y = np.array(valeurs, dtype=float)
    t = np.arange(1, len(y) + 1)
    a, b = np.polyfit(t, y, 1)
    ajuste = a * t + b
    ss_res, ss_tot = ((y - ajuste) ** 2).sum(), ((y - y.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    futur = [{"Période": int(len(y) + k), "Prévision": round(a * (len(y) + k) + b, 2)} for k in range(1, periodes_a_prevoir + 1)]
    return {"pente": round(a, 4), "ordonnee": round(b, 4), "r2": round(r2, 4), "tableau": pd.DataFrame(futur)}


Z_CONFIANCE = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}


def taille_echantillon(marge, confiance=0.95, proportion=0.5, population=None):
    """n = z² p (1 − p) ÷ e², corrigé pour une population finie : n ÷ (1 + (n − 1) ÷ N)."""
    z = Z_CONFIANCE[confiance]
    n0 = z * z * proportion * (1 - proportion) / (marge * marge)
    n = n0 / (1 + (n0 - 1) / population) if population else n0
    return {"z": z, "n_infini": int(np.ceil(n0)), "n": int(np.ceil(n))}


def base_pour_net(net_vise, anciennete_ans=0, personnes_a_charge=0, deduction_par_personne_an=500.0,
                  indemnites_exonerees=0.0):
    """Calcul à l'envers du bulletin complet : le salaire de base qui donne exactement le net voulu (dichotomie)."""
    bas, haut = 0.0, max(1_000.0, net_vise * 3)
    for _ in range(80):
        milieu = (bas + haut) / 2
        net = paie_complete(milieu, anciennete_ans, personnes_a_charge, deduction_par_personne_an, indemnites_exonerees)["net"]
        bas, haut = (milieu, haut) if net < net_vise else (bas, milieu)
    return round(haut, 2)


# ==========================================
# RH : préavis et solde de tout compte
# ==========================================
# Décret n° 2-04-469 du 29 décembre 2004 (BO n° 5280 du 6 janvier 2005) : préavis minimal de rupture d'un CDI.
PREAVIS = {"Cadre ou assimilé": [(1, "1 mois", 1.0), (5, "2 mois", 2.0), (float("inf"), "3 mois", 3.0)],
           "Employé ou ouvrier": [(1, "8 jours", 8 / 26), (5, "1 mois", 1.0), (float("inf"), "2 mois", 2.0)]}


def preavis(categorie, anciennete_ans):
    """Durée minimale du préavis (texte) et sa valeur en mois de salaire (8 jours = 8/26 de mois)."""
    return next((texte, mois) for plafond, texte, mois in PREAVIS[categorie] if anciennete_ans < plafond)


def solde_de_tout_compte(salaire_brut, categorie, anciennete_ans, motif, preavis_effectue, jours_travailles_mois,
                         jours_conges_restants, heures_mois=K.HEURES_LEGALES_MOIS):
    """Ce qui est dû au départ : salaire du mois au prorata, congés non pris, préavis non effectué, indemnité légale."""
    lignes = []
    jour = salaire_brut / 26                                  # 26 jours ouvrables par mois
    lignes.append(("Salaire du dernier mois (prorata)", round(jour * min(jours_travailles_mois, 26), 2), "imposable",
                   "Jours travaillés × salaire ÷ 26"))
    lignes.append(("Indemnité compensatrice de congés payés", round(jour * jours_conges_restants, 2), "imposable",
                   "Code du travail, art. 251 : congés acquis non pris"))
    texte_preavis, mois_preavis = preavis(categorie, anciennete_ans)
    if motif == "Licenciement (hors faute grave)" and not preavis_effectue:
        lignes.append((f"Indemnité compensatrice de préavis ({texte_preavis})", round(salaire_brut * mois_preavis, 2),
                       "imposable", "Code du travail, art. 51 ; décret 2-04-469"))
    if motif == "Licenciement (hors faute grave)" and anciennete_ans >= 0.5:
        legale = indemnite_licenciement(salaire_brut / heures_mois, anciennete_ans)
        lignes.append(("Indemnité légale de licenciement", legale["indemnite"], "exonérée d'IR (limite légale)",
                       "Code du travail, art. 52 et 53 ; CGI, art. 57-7°"))
    tableau = pd.DataFrame([{"Élément": a, "Montant brut": b, "Traitement fiscal": c, "Base": d} for a, b, c, d in lignes])
    imposable = float(tableau[tableau["Traitement fiscal"] == "imposable"]["Montant brut"].sum())
    return {"tableau": tableau, "total": round(float(tableau["Montant brut"].sum()), 2), "imposable": round(imposable, 2),
            "exonere": round(float(tableau["Montant brut"].sum()) - imposable, 2), "preavis": texte_preavis,
            "mois_preavis": mois_preavis}


# ==========================================
# Fiscalité : profit foncier (vente d'un bien immobilier)
# ==========================================
SEUIL_PETITES_CESSIONS = 140_000          # CGI, art. 63 : cessions annuelles n'excédant pas 140 000 DH
PLAFOND_RESIDENCE_PRINCIPALE = 4_000_000  # au-delà, minimum de 3 % sur la fraction excédentaire (art. 144-II)


def profit_foncier(prix_cession, frais_cession, prix_acquisition, frais_acquisition_reels, depenses_investissement,
                   coefficient, residence_principale_5_ans=False, total_cessions_annee=None):
    """TPI = max(20 % du profit net, 3 % du prix de cession) ; frais d'acquisition : réels ou forfait de 15 %."""
    forfait = prix_acquisition * 0.15
    frais_acq = max(frais_acquisition_reels or 0.0, forfait)
    cout = (prix_acquisition + frais_acq + depenses_investissement) * coefficient
    profit = (prix_cession - frais_cession) - cout
    ir20, cm = max(profit, 0.0) * 0.20, prix_cession * 0.03
    total_annee = prix_cession if total_cessions_annee is None else total_cessions_annee
    if total_annee <= SEUIL_PETITES_CESSIONS:
        regime, du = "Exonérée : cessions de l'année ≤ 140 000 DH (art. 63)", 0.0
    elif residence_principale_5_ans and prix_cession <= PLAFOND_RESIDENCE_PRINCIPALE:
        regime, du = "Exonérée : résidence principale occupée au moins 5 ans (art. 63-II-B)", 0.0
    elif residence_principale_5_ans:
        regime, du = ("Résidence principale au-delà de 4 000 000 DH : 3 % sur la fraction excédentaire (art. 144-II)",
                      round((prix_cession - PLAFOND_RESIDENCE_PRINCIPALE) * 0.03, 2))
    else:
        regime = "20 % du profit net" if ir20 >= cm else "Cotisation minimale : 3 % du prix de cession"
        du = max(ir20, cm)
    return {"frais_acquisition": round(frais_acq, 2), "forfait_15": frais_acq == forfait, "cout_reevalue": round(cout, 2),
            "profit_net": round(profit, 2), "ir_20": round(ir20, 2), "cotisation_minimale": round(cm, 2),
            "tpi": round(du, 2), "regime": regime, "net_vendeur": round(prix_cession - frais_cession - du, 2)}


# ==========================================
# Banque : remboursement anticipé
# ==========================================
def remboursement_anticipe(capital, taux_annuel, duree_mois, mois_ecoules, montant, indemnite_mois_interets=1.0,
                           reduire="la durée"):
    """Remboursement anticipé total ou partiel après `mois_ecoules` échéances : intérêts économisés, indemnité
    (en mois d'intérêts sur le capital remboursé, selon le contrat), nouvelle mensualité ou nouvelle durée."""
    t = taux_annuel / 12
    e = echeancier_credit(capital, taux_annuel, duree_mois)
    m = e["mensualite"]
    restant = float(e["tableau"]["Capital restant dû"].iloc[mois_ecoules - 1]) if mois_ecoules else float(capital)
    rembourse = min(montant, restant)
    indemnite = rembourse * t * indemnite_mois_interets
    interets_prevus = float(e["tableau"]["Intérêts"].iloc[mois_ecoules:].sum())
    reste = restant - rembourse
    mois_restants = duree_mois - mois_ecoules
    if reste <= 0.005:
        nouvelle_mensualite, nouveaux_mois, interets_apres = 0.0, 0, 0.0
    elif reduire == "la durée":
        nouvelle_mensualite = m
        nouveaux_mois = int(np.ceil(-np.log(1 - reste * t / m) / np.log(1 + t))) if t else int(np.ceil(reste / m))
        interets_apres = float(echeancier_credit(reste, taux_annuel, nouveaux_mois)["tableau"]["Intérêts"].sum())
    else:
        nouveaux_mois = mois_restants
        n = echeancier_credit(reste, taux_annuel, mois_restants)
        nouvelle_mensualite, interets_apres = n["mensualite"], float(n["tableau"]["Intérêts"].sum())
    economie = interets_prevus - interets_apres
    return {"capital_restant": round(restant, 2), "rembourse": round(rembourse, 2), "indemnite": round(indemnite, 2),
            "interets_prevus": round(interets_prevus, 2), "interets_apres": round(interets_apres, 2),
            "economie": round(economie, 2), "gain_net": round(economie - indemnite, 2), "mensualite": m,
            "nouvelle_mensualite": round(nouvelle_mensualite, 2), "nouveaux_mois": nouveaux_mois,
            "mois_restants": mois_restants}
