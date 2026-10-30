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


def echeancier_credit(capital, taux_annuel, duree_mois):
    """Tableau d'amortissement d'un crédit à mensualités constantes."""
    t = taux_annuel / 12
    mensualite = capital / duree_mois if t == 0 else capital * t / (1 - (1 + t) ** -duree_mois)
    lignes, restant = [], float(capital)
    for mois in range(1, int(duree_mois) + 1):
        interets = restant * t
        amorti = mensualite - interets
        restant = max(0.0, restant - amorti)
        lignes.append({"Mois": mois, "Mensualité": round(mensualite, 2), "Intérêts": round(interets, 2),
                       "Capital remboursé": round(amorti, 2), "Capital restant dû": round(restant, 2)})
    tableau = pd.DataFrame(lignes)
    return {"mensualite": round(mensualite, 2), "cout_total": round(tableau["Intérêts"].sum(), 2),
            "total_rembourse": round(mensualite * duree_mois, 2), "tableau": tableau}


def epargne(versement_mensuel, taux_annuel, annees, capital_initial=0.0):
    """Capital obtenu en épargnant chaque mois, intérêts composés mensuellement."""
    t, capital, lignes = taux_annuel / 12, float(capital_initial), []
    for annee in range(1, int(annees) + 1):
        for _ in range(12):
            capital = capital * (1 + t) + versement_mensuel
        verse = capital_initial + versement_mensuel * 12 * annee
        lignes.append({"Année": annee, "Total versé": round(verse, 2), "Capital": round(capital, 2),
                       "Intérêts gagnés": round(capital - verse, 2)})
    tableau = pd.DataFrame(lignes)
    return {"capital_final": round(capital, 2), "total_verse": round(capital_initial + versement_mensuel * 12 * annees, 2),
            "interets": round(capital - capital_initial - versement_mensuel * 12 * annees, 2), "tableau": tableau}


def amortissement(valeur, duree_ans, methode="lineaire"):
    """Plan d'amortissement linéaire, ou dégressif avec passage au linéaire quand il devient plus avantageux."""
    duree_ans = int(duree_ans)
    lignes, vnc = [], float(valeur)
    if methode == "degressif":
        coef = next(c for d, c in COEFFICIENTS_DEGRESSIFS if duree_ans <= d)
        taux = coef / duree_ans
    for annee in range(1, duree_ans + 1):
        restantes = duree_ans - annee + 1
        if methode == "degressif":
            dotation = max(vnc * taux, vnc / restantes)        # bascule au linéaire en fin de plan
        else:
            dotation = valeur / duree_ans
        dotation = min(dotation, vnc)
        vnc -= dotation
        lignes.append({"Année": annee, "Dotation": round(dotation, 2), "Valeur nette comptable": round(vnc, 2)})
    resultat = {"methode": methode, "tableau": pd.DataFrame(lignes)}
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


def tresorerie(solde_initial, encaissements, decaissements):
    """Plan de trésorerie mois par mois : solde de fin de mois et premier mois à découvert."""
    lignes, solde = [], float(solde_initial)
    for mois, (e, d) in enumerate(zip(encaissements, decaissements), 1):
        solde += e - d
        lignes.append({"Mois": mois, "Encaissements": e, "Décaissements": d, "Solde fin de mois": round(solde, 2)})
    tableau = pd.DataFrame(lignes)
    negatifs = tableau[tableau["Solde fin de mois"] < 0]
    return {"solde_final": round(solde, 2), "solde_minimum": round(float(tableau["Solde fin de mois"].min()), 2),
            "premier_mois_a_decouvert": int(negatifs["Mois"].iloc[0]) if not negatifs.empty else None,
            "tableau": tableau}


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
