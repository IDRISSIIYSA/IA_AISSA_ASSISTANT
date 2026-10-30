"""
Études de projets et business plans : comptes de résultat prévisionnels, plan de financement, trésorerie, rentabilité
(VAN, TRI), capacité de remboursement (DSCR), seuil de rentabilité, scénarios de sensibilité.

Méthode des états prévisionnels du Plan comptable marocain (CGNC, loi n° 9-88), IS de l'année (CGI, art. 19 et 144),
amortissements au prorata (CGI, art. 10).
"""

import pandas as pd

from . import connaissances as K
from . import simulations as S


def is_de_l_annee(resultat, chiffre_affaires, mois_depuis_creation):
    """IS dû : barème de l'IS et cotisation minimale, dont la société est exonérée ses 36 premiers mois (CGI, art. 144)."""
    x = K.calculer_is_du(max(resultat, 0.0), chiffre_affaires)
    if mois_depuis_creation <= 36:
        return x["is"]
    return x["is_du"]


def business_plan(ca_annee1, croissance_ca, taux_couts_variables, charges_fixes, hausse_charges_fixes, investissement,
                  duree_amortissement, apport, emprunt, taux_emprunt, duree_emprunt_ans, delai_clients_jours,
                  delai_fournisseurs_jours, stock_jours, taux_actualisation, annee_debut=2026, mois_debut=1, annees=5,
                  subvention=0.0, frais_etablissement=0.0):
    """Business plan sur `annees` exercices calés sur l'année civile, démarrage au mois `mois_debut` de `annee_debut`."""
    import datetime
    mois_actifs = 13 - int(mois_debut)
    credit = S.echeancier_credit(emprunt, taux_emprunt, duree_emprunt_ans * 12,
                                 datetime.date(int(annee_debut), int(mois_debut), 1)) if emprunt else None
    par_annee = credit["par_annee"].set_index("Année") if credit else None
    amort = S.amortissement(investissement, duree_amortissement, "lineaire", mois_debut, annee_debut)["tableau"]
    amort = amort.set_index("Exercice")["Dotation"] if investissement else pd.Series(dtype=float)
    cr, fin, tres_cumul, bfr_prec, mois_creation = [], [], apport + emprunt + subvention - investissement - frais_etablissement, 0.0, 0
    for k in range(annees):
        annee = int(annee_debut) + k
        prorata = mois_actifs / 12 if k == 0 else 1.0
        ca = ca_annee1 * (1 + croissance_ca) ** k * prorata
        cv = ca * taux_couts_variables
        cf = charges_fixes * (1 + hausse_charges_fixes) ** k * prorata + (frais_etablissement if k == 0 else 0.0)
        ebe = ca - cv - cf
        dot = float(amort.get(annee, 0.0))
        interets = float(par_annee.loc[annee, "Intérêts"]) if par_annee is not None and annee in par_annee.index else 0.0
        capital = float(par_annee.loc[annee, "Capital remboursé"]) if par_annee is not None and annee in par_annee.index else 0.0
        rai = ebe - dot - interets
        mois_creation += 12 if k else mois_actifs
        impot = is_de_l_annee(rai, ca, mois_creation)
        rn = rai - impot
        caf = rn + dot
        ca_an, achats = ca / prorata, cv / prorata         # BFR sur l'activité annuelle ; coûts variables = achats
        bfr = (ca_an * 1.2 * delai_clients_jours + achats * stock_jours - achats * 1.2 * delai_fournisseurs_jours) / 360
        bfr = max(bfr, 0.0) if ca else 0.0
        variation_bfr = bfr - bfr_prec
        bfr_prec = bfr
        tres_cumul += caf - variation_bfr - capital
        annuite = interets + capital
        dscr = (caf + interets) / annuite if annuite else None
        cr.append({"Exercice": annee, "Chiffre d'affaires": round(ca, 2), "Coûts variables": round(cv, 2),
                   "Marge sur coûts variables": round(ca - cv, 2), "Charges fixes": round(cf, 2),
                   "EBE": round(ebe, 2), "Dotations aux amortissements": round(dot, 2), "Charges d'intérêts": round(interets, 2),
                   "Résultat avant impôt": round(rai, 2), "IS": round(impot, 2), "Résultat net": round(rn, 2),
                   "CAF": round(caf, 2)})
        fin.append({"Exercice": annee, "CAF": round(caf, 2), "Variation du BFR": round(variation_bfr, 2),
                    "Remboursement du capital": round(capital, 2), "Trésorerie de fin d'exercice": round(tres_cumul, 2),
                    "BFR": round(bfr, 2), "DSCR": round(dscr, 2) if dscr is not None else None})
    resultats, financement = pd.DataFrame(cr), pd.DataFrame(fin)
    besoins = investissement + frais_etablissement + (financement["BFR"].iloc[0] if annees else 0.0)
    ressources = apport + emprunt + subvention
    flux = [float(c["EBE"] - c["IS"] - f["Variation du BFR"]) for c, f in zip(cr, fin)]
    flux[-1] += float(financement["BFR"].iloc[-1]) + max(0.0, investissement - float(amort.sum()))   # BFR et VNC récupérés
    rent = S.rentabilite_investissement(investissement + frais_etablissement, flux, taux_actualisation)
    taux_mcv = 1 - taux_couts_variables
    seuil = charges_fixes / taux_mcv if taux_mcv > 0 else None
    negatifs = financement[financement["Trésorerie de fin d'exercice"] < 0]
    dscr_min = financement["DSCR"].dropna().min() if financement["DSCR"].notna().any() else None
    return {"compte_de_resultat": resultats, "plan_de_financement": financement, "besoins_initiaux": round(besoins, 2),
            "ressources_initiales": round(ressources, 2), "ecart_financement": round(ressources - besoins, 2),
            "part_apport": round(apport / besoins, 4) if besoins else None, "van": rent["van"], "tri": rent["tri"],
            "delai_recuperation": rent["delai_recuperation_ans"], "seuil_rentabilite": round(seuil, 2) if seuil else None,
            "point_mort_jours": round(seuil / ca_annee1 * 360) if seuil and ca_annee1 else None,
            "dscr_min": round(float(dscr_min), 2) if dscr_min is not None else None,
            "premier_exercice_negatif": int(negatifs["Exercice"].iloc[0]) if not negatifs.empty else None,
            "tresorerie_min": round(float(financement["Trésorerie de fin d'exercice"].min()), 2),
            "resultat_cumule": round(float(resultats["Résultat net"].sum()), 2), "mensualite": credit["mensualite"] if credit else 0.0,
            "flux": flux}


SCENARIOS = [("Référence", 0.0, 0.0), ("Ventes −10 %", -0.10, 0.0), ("Ventes −20 %", -0.20, 0.0),
             ("Coûts variables +10 %", 0.0, 0.10), ("Pessimiste (ventes −15 %, coûts +10 %)", -0.15, 0.10),
             ("Optimiste (ventes +15 %)", 0.15, 0.0)]


def sensibilite(parametres):
    """Le même business plan sous plusieurs scénarios : ce qui casse le projet, et à partir de quand."""
    lignes = []
    for nom, d_ca, d_cv in SCENARIOS:
        p = dict(parametres, ca_annee1=parametres["ca_annee1"] * (1 + d_ca),
                 taux_couts_variables=min(0.99, parametres["taux_couts_variables"] * (1 + d_cv)))
        bp = business_plan(**p)
        lignes.append({"Scénario": nom, "VAN": bp["van"], "TRI": bp["tri"], "Résultat net cumulé": bp["resultat_cumule"],
                       "Trésorerie la plus basse": bp["tresorerie_min"], "DSCR minimal": bp["dscr_min"],
                       "Verdict": "✅ tient" if bp["van"] > 0 and bp["tresorerie_min"] >= 0 else "⚠️ fragile"})
    # Baisse des ventes qui annule la VAN (par dichotomie)
    bas, haut = -0.95, 0.0
    if business_plan(**parametres)["van"] > 0:
        for _ in range(40):
            m = (bas + haut) / 2
            ok = business_plan(**dict(parametres, ca_annee1=parametres["ca_annee1"] * (1 + m)))["van"] > 0
            bas, haut = (bas, m) if ok else (m, haut)
        baisse_critique = round(-haut, 4)
    else:
        baisse_critique = None
    return {"tableau": pd.DataFrame(lignes), "baisse_critique_des_ventes": baisse_critique}


def plan_de_financement_initial(besoins, ressources):
    """besoins / ressources : {libellé: montant}. Équilibre et structure du financement de départ."""
    tb, tr = sum(besoins.values()), sum(ressources.values())
    lignes = ([{"Nature": "Besoin", "Poste": k, "Montant": v, "Part": round(v / tb, 4) if tb else 0} for k, v in besoins.items()]
              + [{"Nature": "Ressource", "Poste": k, "Montant": v, "Part": round(v / tr, 4) if tr else 0}
                 for k, v in ressources.items()])
    return {"total_besoins": round(tb, 2), "total_ressources": round(tr, 2), "ecart": round(tr - tb, 2),
            "tableau": pd.DataFrame(lignes)}
