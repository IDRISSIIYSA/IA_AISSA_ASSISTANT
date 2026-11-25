"""
Mes obligations : ce que je dois payer, déclarer et liquider, quand, et sur quelle base légale ; plus la feuille de
route du débutant, d'IA AISSA qui guide, contrôle et oriente pas à pas.

Délais vérifiés le 30/10/2026 dans le Code général des impôts (CGI) et les textes cités ; chaque échéance porte sa
référence. Les cas particuliers (zones d'accélération industrielle, exportateurs, exercice décalé, régimes sectoriels)
sont signalés comme non traités.
"""

import calendar
import datetime


from . import connaissances as K
from .reseaux import Paresseux

pd = Paresseux("pandas")              # au premier tableau : pas au démarrage

FORMES = ["Société (SARL, SARL AU, SA)", "Personne physique — résultat net réel ou simplifié",
          "Personne physique — auto-entrepreneur"]
SEUIL_TVA_MENSUELLE = 1_000_000          # CGI, art. 108 : déclaration mensuelle à partir de 1 000 000 DH de CA
# Retenues à la source sur loyers et honoraires versés à des personnes physiques (CGI 2026, lu le 21/11/2026) : à opérer
# par les sociétés et les personnes au résultat net réel ou simplifié (art. 157 et 160 bis), versées avant la fin du
# mois suivant (art. 174-IV et V).
SEUIL_RAS_LOYERS = 40_000                # art. 160 bis : pas de retenue si le loyer brut annuel ≤ 40 000 DH
SEUIL_TAUX_LOYERS = 120_000              # art. 73-II-B-5° (10 %) et C-4° (15 %) : selon le loyer brut annuel
TAUX_RAS_HONORAIRES = 0.10               # art. 73-II-B-8° : honoraires HT versés à des personnes au réel ou simplifié


def taux_ras_loyer(loyer_annuel_brut):
    """Taux de la retenue sur les loyers versés à un propriétaire personne physique (0 si dispense)."""
    if loyer_annuel_brut <= SEUIL_RAS_LOYERS:
        return 0.0
    return 0.10 if loyer_annuel_brut < SEUIL_TAUX_LOYERS else 0.15


def fin_de_mois(annee, mois):
    return datetime.date(annee, mois, calendar.monthrange(annee, mois)[1])


def mois_suivant(annee, mois):
    return (annee + 1, 1) if mois == 12 else (annee, mois + 1)


def calendrier(forme, annee, debut_activite, ca_annuel_ht, salaries, masse_brute_mensuelle, is_exercice_precedent,
               tva_mensuelle_estimee=0.0, aujourdhui=None, loyer_mensuel=0.0, honoraires_mensuels=0.0):
    """Toutes les échéances de l'année : date limite, obligation, montant estimé, base légale, statut.
    loyer_mensuel : loyer brut versé à un propriétaire personne physique ; honoraires_mensuels : honoraires HT versés à
    des personnes physiques au résultat net réel ou simplifié (retenues à la source, sauf pour l'auto-entrepreneur)."""
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
    # Retenues à la source sur loyers et honoraires (sociétés et personnes au réel ou simplifié)
    if not ae and (loyer_mensuel or honoraires_mensuels):
        taux_loyer = taux_ras_loyer(loyer_mensuel * 12)
        for m in range(1, 13):
            if datetime.date(annee, m, 1) < debut_activite.replace(day=1):
                continue
            a, ms = mois_suivant(annee, m)
            if taux_loyer:
                ajouter(fin_de_mois(a, ms), "Impôt", f"Retenue à la source sur loyers de {m:02d}/{annee} "
                        f"({taux_loyer * 100:.0f} % du loyer brut) : versement", round(loyer_mensuel * taux_loyer, 2),
                        "CGI, art. 160 bis, 73-II et 174-IV")
            if honoraires_mensuels:
                ajouter(fin_de_mois(a, ms), "Impôt", f"Retenue à la source sur honoraires de {m:02d}/{annee} "
                        "(10 % HT, prestataires personnes physiques) : versement",
                        round(honoraires_mensuels * TAUX_RAS_HONORAIRES, 2), "CGI, art. 157, 73-II-B-8° et 174-V")
        if taux_loyer:
            ajouter(datetime.date(annee, 2, 28 + calendar.isleap(annee)), "Déclaration",
                    f"Déclaration annuelle des loyers versés en {annee - 1} et des retenues (avant le 1er mars)", 0.0,
                    "CGI, art. 154 bis")
        if honoraires_mensuels:
            ajouter(fin_de_mois(annee, 3) if societe else datetime.date(annee, 4, 30), "Déclaration",
                    f"Déclaration des honoraires versés en {annee - 1} (avec la déclaration "
                    f"{'du résultat fiscal' if societe else 'du revenu global'})", 0.0, "CGI, art. 151")
    # Taxe professionnelle : déclarations des éléments imposables (loi 47-06, art. 13 — version consolidée du 03/07/2025)
    if not ae and annee > debut_activite.year:
        if annee == debut_activite.year + 1:
            ajouter(datetime.date(annee, 1, 31), "Déclaration", "Taxe professionnelle : déclaration récapitulative des "
                    "éléments imposables (terrains, constructions, matériel, outillage, prix de revient) par établissement",
                    0.0, "Loi 47-06, art. 13 (au plus tard le 31 janvier de l'année qui suit le début d'activité)")
        else:
            ajouter(datetime.date(annee, 1, 31), "Déclaration", f"Taxe professionnelle : déclaration des modifications "
                    f"des éléments imposables faites en {annee - 1} (seulement si locaux, matériel ou outillage ont "
                    "changé)", 0.0, "Loi 47-06, art. 13 (au plus tard le 31 janvier de l'année qui suit la modification)")
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
                    f"du trimestre {t}/{annee} (ou chaque mois, sur option)", round(ca_annuel_ht / 4 * 0.01, 2), "CGI, art. 42 bis, 73-III et 82 bis ; loi 114-13")
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
    exon_tp = annee - debut_activite.year < 5          # loi 47-06, art. 6-II-1° : 5 ans à compter de l'année du début
    lignes.append(("Taxe professionnelle", 0.0 if exon_tp else None, "Loi 47-06, art. 6-II-1° : exonérée 5 ans à compter "
                   f"de l'année du début d'activité (jusqu'en {debut_activite.year + 4})" if exon_tp else
                   "Loi 47-06, art. 9 : 10 %, 20 % ou 30 % de la valeur locative selon la classe (droit minimum de "
                   "300 à 1 200 DH en périmètre urbain) ; payée sur avis d'imposition (rôle, art. 10)"))
    lignes.append(("Taxe de services communaux", None, "Loi 47-06 : 10,5 % de la valeur locative (périmètre urbain)"))
    if salaries:
        brut = masse_brute_mensuelle / salaries
        patronal = (min(brut, K.PLAFOND_CNSS_MENSUEL) * K.CNSS_EMPLOYEUR + brut * (K.AMO_EMPLOYEUR
                    + K.ALLOCATIONS_FAMILIALES_EMPLOYEUR + K.TAXE_FORMATION_PROFESSIONNELLE)) * salaries * 12
        lignes.append(("Charges sociales patronales (CNSS, AMO, AF, TFP) sur l'année", round(patronal, 2),
                       "Dahir 1-72-184 ; loi 65-00"))
        lignes.append(("IR des salariés (retenu sur leur paie, reversé par vous)", round(K.calculer_paie(brut)["ir"] * salaries * 12, 2),
                       "CGI, art. 156 et 174"))
    def montant(v):
        return "selon votre activité" if v is None else f"{v:,.2f}".replace(",", " ").replace(".", ",").removesuffix(",00") + " DH"
    return pd.DataFrame([{"Impôt ou charge": a, "Montant annuel estimé": montant(b), "Base légale": c} for a, b, c in lignes])


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


# ==========================================
# Rappel dans le chat : « qu'est-ce que je dois payer ce mois-ci ? », à partir du profil enregistré
# ==========================================
import json as _json

CLE_PROFIL = "profil_obligations:{}"
CHAMPS_PROFIL = ("forme", "debut", "ca", "benefice", "salaries", "masse", "is_precedent", "tva_mensuelle", "loyer",
                 "honoraires")


def garder_profil(memoire, utilisateur, profil):
    """Retient le profil (seulement ce qui sert au calendrier) pour les rappels dans le chat."""
    propre = {k: profil[k] for k in CHAMPS_PROFIL if k in profil}
    propre["debut"] = str(propre.get("debut", ""))[:10]
    memoire.definir_reglage(CLE_PROFIL.format(utilisateur), _json.dumps(propre, ensure_ascii=False))


def profil_de(memoire, utilisateur):
    brut = memoire.reglage(CLE_PROFIL.format(utilisateur)) if memoire is not None else None
    return _json.loads(brut) if brut else None


CLE_PAYEES = "echeances_payees:{}"
GARDER_PAYEES_JOURS = 400            # au-delà, une échéance cochée est oubliée (la liste reste courte)
JOURS_RAPPEL_DISCRET = 5
# « j'ai payé la CNSS » → les obligations du calendrier qu'elle désigne
PAIEMENTS = [
    (r"\bcnss\b|damancom", r"^CNSS"),
    (r"\btva\b", r"^TVA"),
    (r"\bir\b.*salaire|retenue|salaires|\bir\b", r"^IR sur salaires|^IR : déclaration"),
    (r"acompte|\bis\b|impôt sur les sociétés|liquidation", r"^IS : acompte|^IS \d{4} : liquidation"),
    (r"auto[- ]?entrepreneur", r"^Auto-entrepreneur"),
    (r"9421|déclaration annuelle des (traitements|salaires)", r"^Déclaration annuelle des traitements"),
    (r"loyers?|foncier", r"^Retenue à la source sur loyers"),
    (r"honoraires?", r"^Retenue à la source sur honoraires"),
    (r"taxe professionnelle|patente|éléments imposables", r"^Taxe professionnelle"),
]


def cle_echeance(date, obligation):
    return f"{date.isoformat() if hasattr(date, 'isoformat') else date}|{obligation}"


def _liste_payees(memoire, utilisateur):
    brut = memoire.reglage(CLE_PAYEES.format(utilisateur)) if memoire is not None else None
    return _json.loads(brut) if brut else []                     # dans l'ordre où elles ont été cochées


def payees_de(memoire, utilisateur):
    return set(_liste_payees(memoire, utilisateur))


def rappel(profil, aujourdhui=None, horizon_jours=45, payees=frozenset()):
    """Échéances du mois en cours (et en retard de ce mois), puis celles des `horizon_jours` suivants ; les échéances
    cochées comme payées (`payees` : clés « AAAA-MM-JJ|obligation ») sont retirées.
    Renvoie {"ce_mois", "a_venir", "prochaine", "total_ce_mois", "payees": DataFrame des échéances du mois cochées}."""
    aujourdhui = aujourdhui or datetime.date.today()
    debut = datetime.date.fromisoformat(profil["debut"])
    salaries = int(profil.get("salaries") or 0)
    masse = float(profil.get("masse") or 0)
    tables = []
    for annee in (aujourdhui.year, aujourdhui.year + 1):          # décembre : les échéances de janvier aussi
        cal = calendrier(profil["forme"], annee, debut, float(profil.get("ca") or 0), salaries if masse else 0, masse,
                         float(profil.get("is_precedent") or 0), float(profil.get("tva_mensuelle") or 0), aujourdhui,
                         float(profil.get("loyer") or 0), float(profil.get("honoraires") or 0))
        tables.append(cal["tableau"])
    t = pd.concat(tables, ignore_index=True).drop_duplicates(subset=["Date limite", "Obligation"])
    dates = pd.to_datetime(t["Date limite"], format="%d/%m/%Y").dt.date
    cochee = pd.Series([cle_echeance(d, o) in payees for d, o in zip(dates, t["Obligation"])], index=t.index)
    deja = t[cochee & (dates >= aujourdhui.replace(day=1)) & (dates <= fin_de_mois(aujourdhui.year, aujourdhui.month))]
    t, dates = t[~cochee], dates[~cochee]
    ce_mois = t[(dates >= aujourdhui.replace(day=1)) & (dates <= fin_de_mois(aujourdhui.year, aujourdhui.month))]
    a_venir = t[(dates > fin_de_mois(aujourdhui.year, aujourdhui.month))
                & (dates <= aujourdhui + datetime.timedelta(days=horizon_jours))]
    t = t.assign(_date=dates)
    ce_mois = ce_mois.assign(_date=dates[ce_mois.index])
    a_venir = a_venir.assign(_date=dates[a_venir.index])
    futures = t[t["_date"] >= aujourdhui].sort_values("_date")
    prochaine = None
    if len(futures):
        ligne = futures.iloc[0].to_dict()
        ligne["jours"] = (ligne["_date"] - aujourdhui).days
        prochaine = ligne
    return {"ce_mois": ce_mois.sort_values("_date"), "a_venir": a_venir.sort_values("_date").drop(columns="_date"),
            "prochaine": prochaine, "total_ce_mois": float(ce_mois["Montant estimé"].sum()), "payees": deja}


def reponse_rappel(memoire, utilisateur, aujourdhui=None):
    """(texte, éléments) pour le chat : les échéances du mois, ou l'invitation à remplir son profil."""
    profil = profil_de(memoire, utilisateur)
    if not profil:
        return ("Pour te dire exactement ce que tu dois payer et déclarer, j'ai besoin de ton profil (statut, chiffre "
                "d'affaires, salariés…). Ouvre **Simulations → Mes impôts et déclarations (calendrier)**, remplis-le et "
                "clique sur « 💾 Retenir mon profil » : ensuite, demande-moi simplement « qu'est-ce que je dois payer ce "
                "mois-ci ? ».", [])
    aujourdhui = aujourdhui or datetime.date.today()
    r = rappel(profil, aujourdhui, payees=payees_de(memoire, utilisateur))
    dh = lambda v: f"{v:,.0f}".replace(",", " ") + " DH"
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
            "novembre", "décembre"][aujourdhui.month - 1]
    lignes = []
    for _, e in r["ce_mois"].iterrows():
        date = e["_date"]
        etat = "⚠️ date passée — déjà payée ?" if date < aujourdhui else f"dans {(date - aujourdhui).days} jour(s)"
        montant = f" — environ **{dh(e['Montant estimé'])}**" if e["Montant estimé"] else ""
        lignes.append(f"- **{date.strftime('%d/%m')}** ({etat}) : {e['Obligation']}{montant} _({e['Base légale']})_")
    texte = (f"Ton profil : {profil['forme'].lower()}, chiffre d'affaires {dh(float(profil.get('ca') or 0))}, "
             f"{int(profil.get('salaries') or 0)} salarié(s).\n\n")
    if lignes:
        texte += (f"**En {mois} {aujourdhui.year}**, tu dois :\n" + "\n".join(lignes)
                  + f"\n\nTotal estimé du mois : **{dh(r['total_ce_mois'])}**.")
    else:
        texte += f"Rien à payer ni à déclarer en {mois} {aujourdhui.year} d'après ton profil."
    if len(r["payees"]):
        texte += "\n\n✅ Déjà payé ce mois-ci : " + " ; ".join(r["payees"]["Obligation"]) + "."
    if lignes:
        texte += "\n\nUne échéance réglée ? Dis-moi « j'ai payé la CNSS » (ou la TVA, l'IR, l'acompte d'IS) : je ne te la rappellerai plus."
    p = r["prochaine"]
    if p:
        texte += (f"\n\n⏰ Prochaine échéance : **{p['_date'].strftime('%d/%m/%Y')}** "
                  f"(dans {p['jours']} jour(s)) — {p['Obligation']}.")
    texte += ("\n\nMontants estimés à partir de ton profil (taux 2026) ; un retard coûte une pénalité et une "
              "majoration. Ton profil a changé ? Mets-le à jour dans la simulation « Mes impôts et déclarations ».")
    elements = []
    if len(r["a_venir"]):
        elements.append({"type": "tableau", "titre": "📅 Les semaines suivantes", "donnees": r["a_venir"]})
    return texte, elements


def marquer_payee(memoire, utilisateur, texte, aujourdhui=None):
    """« j'ai payé la CNSS et la TVA » : pour chaque obligation nommée, coche l'échéance non payée la plus proche — la
    première à partir du début du mois (jusqu'à 31 jours après aujourd'hui), sinon la plus récente des 60 derniers
    jours. Renvoie (réponse, échéances cochées)."""
    profil = profil_de(memoire, utilisateur)
    if not profil:
        return reponse_rappel(memoire, utilisateur, aujourdhui)[0], []
    import re
    aujourdhui = aujourdhui or datetime.date.today()
    t = texte.lower()
    motifs = [o for q, o in PAIEMENTS if re.search(q, t)]
    if not motifs:
        return ("Laquelle as-tu payée ? Dis-moi par exemple « j'ai payé la CNSS », « la TVA », « l'IR sur salaires » "
                "ou « l'acompte d'IS ».", [])
    liste = _liste_payees(memoire, utilisateur)
    payees = set(liste)
    tables = [calendrier(profil["forme"], a, datetime.date.fromisoformat(profil["debut"]), float(profil.get("ca") or 0),
                         int(profil.get("salaries") or 0), float(profil.get("masse") or 0),
                         float(profil.get("is_precedent") or 0), float(profil.get("tva_mensuelle") or 0),
                         aujourdhui, float(profil.get("loyer") or 0),
                         float(profil.get("honoraires") or 0))["tableau"] for a in (aujourdhui.year - 1, aujourdhui.year, aujourdhui.year + 1)]
    t_ = pd.concat(tables, ignore_index=True).drop_duplicates(subset=["Date limite", "Obligation"])
    t_ = t_.assign(_date=pd.to_datetime(t_["Date limite"], format="%d/%m/%Y").dt.date).sort_values("_date")
    fenetre = t_[(t_["_date"] >= aujourdhui - datetime.timedelta(days=60))
                 & (t_["_date"] <= aujourdhui + datetime.timedelta(days=31))]
    debut_mois = aujourdhui.replace(day=1)
    cochees = []
    for motif in motifs:
        libres = [e for _, e in fenetre.iterrows() if re.search(motif, e["Obligation"])
                  and cle_echeance(e["_date"], e["Obligation"]) not in payees]
        actuelles = [e for e in libres if e["_date"] >= debut_mois]
        e = actuelles[0] if actuelles else (libres[-1] if libres else None)
        if e is not None:
            cle = cle_echeance(e["_date"], e["Obligation"])
            payees.add(cle)
            liste.append(cle)
            cochees.append(e)
    if not cochees:
        return ("Je ne trouve pas d'échéance non payée de ce type autour d'aujourd'hui dans ton calendrier : tout est "
                "déjà coché, ou ton profil ne la prévoit pas.", [])
    limite = (aujourdhui - datetime.timedelta(days=GARDER_PAYEES_JOURS)).isoformat()
    liste = [c for c in liste if c.split("|")[0] >= limite]
    memoire.definir_reglage(CLE_PAYEES.format(utilisateur), _json.dumps(liste, ensure_ascii=False))
    lignes = "\n".join(f"- ✅ **{e['_date'].strftime('%d/%m/%Y')}** : {e['Obligation']}" for e in cochees)
    return (f"C'est noté, je ne te les rappellerai plus :\n{lignes}\n\nUne erreur ? Dis-moi « annule mon dernier "
            "paiement ».", cochees)


def annuler_dernier_paiement(memoire, utilisateur):
    """Décoche la dernière échéance cochée."""
    liste = _liste_payees(memoire, utilisateur)
    if not liste:
        return "Aucune échéance n'est cochée comme payée."
    derniere = liste.pop()
    memoire.definir_reglage(CLE_PAYEES.format(utilisateur), _json.dumps(liste, ensure_ascii=False))
    date, obligation = derniere.split("|", 1)
    return f"D'accord, « {obligation} » ({datetime.date.fromisoformat(date).strftime('%d/%m/%Y')}) est de nouveau à payer."


def rappel_discret(memoire, utilisateur, aujourdhui=None):
    """Une ligne à l'ouverture quand une échéance non payée tombe dans moins de JOURS_RAPPEL_DISCRET jours (ou est
    passée ce mois-ci), sinon None. Rien sans profil enregistré."""
    profil = profil_de(memoire, utilisateur)
    if not profil:
        return None
    aujourdhui = aujourdhui or datetime.date.today()
    r = rappel(profil, aujourdhui, horizon_jours=JOURS_RAPPEL_DISCRET, payees=payees_de(memoire, utilisateur))
    proches = [e for _, e in r["ce_mois"].iterrows() if (e["_date"] - aujourdhui).days < JOURS_RAPPEL_DISCRET]
    proches += [e for _, e in r["a_venir"].assign(
        _date=pd.to_datetime(r["a_venir"]["Date limite"], format="%d/%m/%Y").dt.date).iterrows()
        if (e["_date"] - aujourdhui).days < JOURS_RAPPEL_DISCRET]
    if not proches:
        return None
    e = min(proches, key=lambda x: x["_date"])
    jours = (e["_date"] - aujourdhui).days
    quand = ("date passée" if jours < 0 else "aujourd'hui" if jours == 0 else "demain" if jours == 1
             else f"dans {jours} jours")
    autres = f" (+{len(proches) - 1} autre(s))" if len(proches) > 1 else ""
    return (f"⏰ {e['Obligation']} — {e['_date'].strftime('%d/%m')} ({quand}){autres}. "
            "Déjà réglée ? Dis « j'ai payé… ».")
