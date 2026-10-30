"""
Mes obligations : ce que je dois payer, déclarer et liquider, quand, et sur quelle base légale ; plus la feuille de
route du débutant, d'IA AISSA qui guide, contrôle et oriente pas à pas.

Délais vérifiés le 30/10/2026 dans le Code général des impôts (CGI) et les textes cités ; chaque échéance porte sa
référence. Les cas particuliers (zones d'accélération industrielle, exportateurs, exercice décalé, régimes sectoriels)
sont signalés comme non traités.
"""

import calendar
import datetime

import pandas as pd

from . import connaissances as K

FORMES = ["Société (SARL, SARL AU, SA)", "Personne physique — résultat net réel ou simplifié",
          "Personne physique — auto-entrepreneur"]
SEUIL_TVA_MENSUELLE = 1_000_000          # CGI, art. 108 : déclaration mensuelle à partir de 1 000 000 DH de CA


def fin_de_mois(annee, mois):
    return datetime.date(annee, mois, calendar.monthrange(annee, mois)[1])


def mois_suivant(annee, mois):
    return (annee + 1, 1) if mois == 12 else (annee, mois + 1)


def calendrier(forme, annee, debut_activite, ca_annuel_ht, salaries, masse_brute_mensuelle, is_exercice_precedent,
               tva_mensuelle_estimee=0.0, aujourdhui=None):
    """Toutes les échéances de l'année : date limite, obligation, montant estimé, base légale, statut."""
    aujourdhui = aujourdhui or datetime.date.today()
    ev = []

    def ajouter(date, type_, obligation, montant, base):
        ev.append({"Date limite": date, "Type": type_, "Obligation": obligation, "Montant estimé": montant,
                   "Base légale": base})

    societe, ae = forme.startswith("Société"), forme.endswith("auto-entrepreneur")
    premiere_annee = debut_activite.year == annee
    # Salaires : IR retenu à la source et CNSS / AMO
    if salaries:
        paie = K.calculer_paie(masse_brute_mensuelle / salaries)
        ir_mois = round(paie["ir"] * salaries, 2)
        cnss_mois = round(min(masse_brute_mensuelle / salaries, K.PLAFOND_CNSS_MENSUEL) * salaries
                          * (K.CNSS_SALARIE + K.CNSS_EMPLOYEUR)
                          + masse_brute_mensuelle * (K.AMO_SALARIE + K.AMO_EMPLOYEUR + K.ALLOCATIONS_FAMILIALES_EMPLOYEUR
                                                     + K.TAXE_FORMATION_PROFESSIONNELLE), 2)
        for m in range(1, 13):
            if datetime.date(annee, m, 1) < debut_activite.replace(day=1):
                continue
            a, ms = mois_suivant(annee, m)
            ajouter(datetime.date(a, ms, 10), "Social", f"CNSS : déclaration et paiement des salaires de "
                    f"{m:02d}/{annee} (BDS sur Damancom)", cnss_mois,
                    "Dahir 1-72-184 (régime de sécurité sociale) ; loi 65-00 (AMO)")
            ajouter(fin_de_mois(a, ms), "Impôt", f"IR sur salaires de {m:02d}/{annee} : versement de la retenue à la source",
                    ir_mois, "CGI, art. 156 et 174")
        ajouter(datetime.date(annee, 2, 28 + calendar.isleap(annee)), "Déclaration",
                f"Déclaration annuelle des traitements et salaires {annee - 1} (état 9421)", 0.0, "CGI, art. 79")
    # TVA
    if not ae:
        mensuelle = ca_annuel_ht >= SEUIL_TVA_MENSUELLE and not premiere_annee
        periodes = range(1, 13) if mensuelle else (3, 6, 9, 12)
        for m in periodes:
            if fin_de_mois(annee, m) < debut_activite:
                continue
            a, ms = mois_suivant(annee, m)
            ajouter(fin_de_mois(a, ms), "Impôt", f"TVA {'du mois ' + f'{m:02d}' if mensuelle else 'du trimestre ' + str((m + 2) // 3)}"
                    f"/{annee} : déclaration et paiement (SIMPL-TVA)", round(tva_mensuelle_estimee * (1 if mensuelle else 3), 2),
                    "CGI, art. 108, 110 et 111")
    # IS ou IR professionnel
    if societe:
        if not premiere_annee and is_exercice_precedent:
            acompte = round(max(is_exercice_precedent, K.MINIMUM_CM) * 0.25, 2)
            for m in (3, 6, 9, 12):
                ajouter(fin_de_mois(annee, m), "Impôt", f"IS : acompte provisionnel n° {m // 3} (25 % de l'IS {annee - 1})",
                        acompte, "CGI, art. 170-I")
        ajouter(fin_de_mois(annee, 3), "Déclaration", f"IS : déclaration du résultat fiscal {annee - 1} et états de "
                f"synthèse (liasse fiscale)", 0.0, "CGI, art. 20-I ; loi 9-88 (comptabilité)")
        ajouter(fin_de_mois(annee, 3), "Liquidation", f"IS {annee - 1} : liquidation (IS dû − acomptes versés : "
                "complément à payer, ou excédent imputé sur les acomptes suivants)", 0.0, "CGI, art. 170-IV")
        ajouter(fin_de_mois(annee, 6), "Juridique", f"Assemblée générale d'approbation des comptes {annee - 1} (6 mois "
                "après la clôture), puis dépôt des états de synthèse au greffe", 0.0, "Loi 5-96 (SARL) ; loi 17-95 (SA)")
    elif ae:
        for t, m in enumerate((3, 6, 9, 12), 1):
            a, ms = mois_suivant(annee, m)
            ajouter(fin_de_mois(a, ms), "Impôt", f"Auto-entrepreneur : déclaration et paiement du chiffre d'affaires "
                    f"du trimestre {t}/{annee} (ou chaque mois, sur option)", round(ca_annuel_ht / 4 * 0.01, 2), "CGI, art. 41, 73-III et 82 bis ; loi 114-13")
    else:
        ajouter(datetime.date(annee, 4, 30), "Déclaration", f"IR : déclaration du revenu global {annee - 1} (revenus "
                "professionnels au réel ou simplifié, avant le 1er mai, SIMPL-IR), et paiement du solde", 0.0,
                "CGI, art. 82-I et 173")
    tableau = pd.DataFrame(ev).sort_values("Date limite").reset_index(drop=True)
    if tableau.empty:
        return {"tableau": tableau, "prochaine": None, "en_retard": 0, "total_estime": 0.0}
    tableau["Statut"] = ["⏰ passée" if d < aujourdhui else ("🔴 dans moins de 15 jours" if (d - aujourdhui).days < 15
                         else "🟢 à venir") for d in tableau["Date limite"]]
    a_venir = tableau[tableau["Date limite"] >= aujourdhui]
    prochaine = a_venir.iloc[0].to_dict() if not a_venir.empty else None
    tableau["Date limite"] = [d.strftime("%d/%m/%Y") for d in tableau["Date limite"]]
    if prochaine:
        prochaine["jours"] = (prochaine["Date limite"] - aujourdhui).days
        prochaine["Date limite"] = prochaine["Date limite"].strftime("%d/%m/%Y")
    return {"tableau": tableau, "prochaine": prochaine, "total_estime": round(float(tableau["Montant estimé"].sum()), 2),
            "nombre": len(tableau)}


def ce_que_je_paie(forme, ca_annuel_ht, benefice, debut_activite, annee, salaries, masse_brute_mensuelle):
    """La liste de mes impôts et taxes, avec leur montant estimé et leur base légale."""
    mois = (annee - debut_activite.year) * 12 + 12 - debut_activite.month + 1
    lignes = []
    if forme.startswith("Société"):
        x = K.calculer_is_du(benefice, ca_annuel_ht)
        du = x["is"] if mois <= 36 else x["is_du"]
        lignes.append(("Impôt sur les sociétés (IS)", du, "CGI, art. 19 ; cotisation minimale art. 144 "
                       + ("(exonérée : moins de 36 mois)" if mois <= 36 else f"(retenu : {x['retenu']})")))
        lignes.append(("TVA (collectée − déductible, reversée à l'État)", None, "CGI, art. 87 et suivants : taux 20 % et 10 %"))
    elif forme.endswith("auto-entrepreneur"):
        lignes.append(("Impôt de l'auto-entrepreneur (1 % services, 0,5 % commerce et artisanat)", round(ca_annuel_ht * 0.01, 2),
                       "CGI, art. 73-III ; plafonds 200 000 DH (services) et 500 000 DH (commerce)"))
        lignes.append(("AMO des travailleurs non salariés", None, "Loi 98-15 : cotisation forfaitaire selon la catégorie"))
    else:
        from . import baremes as B
        try:
            ir = B.ir_annee(max(benefice, 0), min(annee, 2026))["ir_annuel"]
        except ValueError:
            ir = None
        lignes.append(("IR sur le revenu professionnel (barème)", ir, "CGI, art. 73-I ; minimum d'imposition art. 144"))
        lignes.append(("TVA (si assujetti)", None, "CGI, art. 87 et suivants"))
    exon_tp = mois <= 60
    lignes.append(("Taxe professionnelle", 0.0 if exon_tp else None, "Loi 47-06, art. 6 : exonérée 5 ans à compter du début "
                   "d'activité" if exon_tp else "Loi 47-06 : 10 %, 20 % ou 30 % de la valeur locative selon la classe"))
    lignes.append(("Taxe de services communaux", None, "Loi 47-06 : 10,5 % de la valeur locative (périmètre urbain)"))
    if salaries:
        brut = masse_brute_mensuelle / salaries
        patronal = (min(brut, K.PLAFOND_CNSS_MENSUEL) * K.CNSS_EMPLOYEUR + brut * (K.AMO_EMPLOYEUR
                    + K.ALLOCATIONS_FAMILIALES_EMPLOYEUR + K.TAXE_FORMATION_PROFESSIONNELLE)) * salaries * 12
        lignes.append(("Charges sociales patronales (CNSS, AMO, AF, TFP) sur l'année", round(patronal, 2),
                       "Dahir 1-72-184 ; loi 65-00"))
        lignes.append(("IR des salariés (retenu sur leur paie, reversé par vous)", round(K.calculer_paie(brut)["ir"] * salaries * 12, 2),
                       "CGI, art. 156 et 174"))
    return pd.DataFrame([{"Impôt ou charge": a, "Montant annuel estimé": b, "Base légale": c} for a, b, c in lignes])


FEUILLE_DE_ROUTE = [
    ("1. Choisir son statut", "Auto-entrepreneur (simple, plafonné), personne physique au réel, ou société (SARL, SARL AU). "
     "Comparez avec la simulation « Auto-entrepreneur » et « IS ».", "Loi 114-13 (auto-entrepreneur) ; loi 5-96 (SARL)"),
    ("2. Créer l'entreprise en ligne", "Certificat négatif (nom), statuts, domiciliation, immatriculation au registre du "
     "commerce, identifiant fiscal, ICE, taxe professionnelle et CNSS : en une démarche sur la plateforme électronique "
     "de création d'entreprise (CRI).", "Loi 88-17 (création d'entreprise par voie électronique) ; loi 89-21 (domiciliation)"),
    ("3. Ouvrir un compte bancaire professionnel", "Séparez strictement l'argent de l'entreprise et le vôtre : c'est la "
     "première chose que vérifie un contrôleur.", "Loi 5-96 (SARL) ; bonne pratique de contrôle interne"),
    ("4. Adhérer aux télédéclarations", "SIMPL (impôts, site de la DGI) et Damancom (CNSS) : les déclarations et "
     "paiements se font en ligne.", "CGI, art. 155 (télédéclaration et télépaiement)"),
    ("5. Tenir une comptabilité", "Factures numérotées avec ICE, journal, grand livre, états de synthèse annuels ; un "
     "expert-comptable ou un comptable agréé est fortement conseillé.", "Loi 9-88 (obligations comptables) ; CGI, art. 145"),
    ("6. Déclarer les salariés", "Immatriculer chaque salarié à la CNSS dès l'embauche, bulletin de paie chaque mois, "
     "contrat écrit.", "Dahir 1-72-184 (immatriculation à la CNSS) ; Code du travail (loi 65-99)"),
    ("7. Suivre le calendrier", "Chaque mois : CNSS (avant le 10), IR salaires et TVA (fin du mois suivant). Chaque "
     "trimestre : TVA trimestrielle, acomptes d'IS. Chaque année : liasse fiscale, état 9421, assemblée générale.",
     "CGI, art. 20, 79, 108-111, 170 ; dahir 1-72-184"),
    ("8. Garder les justificatifs 10 ans", "Factures, contrats, relevés : l'administration peut contrôler les exercices "
     "non prescrits.", "CGI, art. 211 (conservation des documents)"),
]
