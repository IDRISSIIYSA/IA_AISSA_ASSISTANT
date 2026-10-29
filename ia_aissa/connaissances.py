"""
Base de connaissances marocaines d'IA AISSA : règles, barèmes et calculateurs exacts.

Les taux ci-dessous ont été vérifiés le 29/10/2026 auprès de sources secondaires (cabinets,
presse économique) pour l'exercice 2026 (LF 2025 et LF 2026, circulaire DGI n° 737).
Ils doivent être confirmés avec le Code Général des Impôts publié par la DGI avant tout usage
réel. Mettez-les à jour à chaque nouvelle loi de finances.
"""

MISE_A_JOUR = "29/10/2026 (exercice 2026)"

# ==========================================
# Fiscalité
# ==========================================
# IR annuel (LF 2025, inchangé en LF 2026) : (plafond de la tranche, taux, somme à déduire)
BAREME_IR = [
    (40_000, 0.00, 0),
    (60_000, 0.10, 4_000),
    (80_000, 0.20, 10_000),
    (100_000, 0.30, 18_000),
    (180_000, 0.34, 22_000),
    (float("inf"), 0.37, 27_400),
]

# IS proportionnel (convergence LF 2023 achevée en 2026), hors établissements de crédit et assurances
SEUIL_IS = 100_000_000
TAUX_IS_NORMAL, TAUX_IS_GRANDES = 0.20, 0.35

# TVA 2026 : deux taux (20 % et 10 %) + exonérations
TAUX_TVA = {"20 %": 0.20, "10 %": 0.10, "Exonéré": 0.0}

# Paie
CNSS_SALARIE, PLAFOND_CNSS_MENSUEL = 0.0448, 6_000
AMO_SALARIE = 0.0226
CNSS_EMPLOYEUR, AMO_EMPLOYEUR = 0.0898, 0.0411   # hors allocations familiales et taxe de formation
FRAIS_PRO = [(78_000, 0.35), (float("inf"), 0.25)]  # selon le salaire brut imposable annuel
PLAFOND_FRAIS_PRO_ANNUEL = 35_000

# Création d'entreprise
CAPITAL_MIN_SA, CAPITAL_MIN_SA_APE = 300_000, 3_000_000
ACTIONNAIRES_MIN_SA, ASSOCIES_MAX_SARL = 5, 50
PLAFOND_AE = {"commerce": 500_000, "services": 200_000}
TAUX_AE = {"commerce": 0.005, "services": 0.01}


def calculer_ir(revenu_net_imposable_annuel):
    r = max(0.0, float(revenu_net_imposable_annuel))
    for plafond, taux, deduction in BAREME_IR:
        if r <= plafond:
            ir = max(0.0, r * taux - deduction)
            return {"revenu_net_imposable": r, "taux_marginal": taux, "somme_a_deduire": deduction,
                    "ir_annuel": round(ir, 2), "ir_mensuel": round(ir / 12, 2),
                    "taux_moyen": round(ir / r, 4) if r else 0.0}


def tranche_ir(revenu):
    return next(i for i, (plafond, _, _) in enumerate(BAREME_IR) if revenu <= plafond)


def calculer_is(benefice_fiscal):
    b = float(benefice_fiscal)
    if b <= 0:
        return {"benefice_fiscal": b, "taux": 0.0, "is": 0.0,
                "remarque": "Déficit : pas d'IS, mais la cotisation minimale sur le chiffre d'affaires reste due."}
    taux = TAUX_IS_GRANDES if b >= SEUIL_IS else TAUX_IS_NORMAL
    return {"benefice_fiscal": b, "taux": taux, "is": round(b * taux, 2),
            "remarque": "Taux proportionnel appliqué à tout le bénéfice (hors banques et assurances)."}


def calculer_tva(montant, taux, montant_est_ttc=False):
    t = float(taux)
    ht = montant / (1 + t) if montant_est_ttc else float(montant)
    return {"ht": round(ht, 2), "taux": t, "tva": round(ht * t, 2), "ttc": round(ht * (1 + t), 2)}


def calculer_paie(salaire_brut_mensuel):
    brut = float(salaire_brut_mensuel)
    cnss = min(brut, PLAFOND_CNSS_MENSUEL) * CNSS_SALARIE
    amo = brut * AMO_SALARIE
    taux_fp = next(t for plafond, t in FRAIS_PRO if brut * 12 <= plafond)
    frais_pro = min(brut * taux_fp, PLAFOND_FRAIS_PRO_ANNUEL / 12)
    net_imposable = brut - cnss - amo - frais_pro
    ir = calculer_ir(net_imposable * 12)["ir_mensuel"]
    return {
        "salaire_brut": round(brut, 2), "cnss_salarie": round(cnss, 2), "amo_salarie": round(amo, 2),
        "frais_professionnels": round(frais_pro, 2), "net_imposable": round(net_imposable, 2),
        "ir": ir, "salaire_net": round(brut - cnss - amo - ir, 2),
        "charges_patronales": round(min(brut, PLAFOND_CNSS_MENSUEL) * CNSS_EMPLOYEUR + brut * AMO_EMPLOYEUR, 2),
        "remarque": "Sans charges de famille, ni allocations familiales et taxe de formation professionnelle patronales.",
    }


def calculer_van(investissement, flux, taux):
    van = -float(investissement) + sum(f / (1 + taux) ** (i + 1) for i, f in enumerate(flux))
    return {"van": round(van, 2), "decision": "Accepter le projet" if van > 0 else "Rejeter le projet"}


def seuil_rentabilite(prix, cout_variable_unitaire, charges_fixes):
    marge = prix - cout_variable_unitaire
    if marge <= 0:
        return {"seuil_en_quantite": None, "remarque": "Le prix ne couvre pas le coût variable : jamais rentable."}
    q = charges_fixes / marge
    return {"marge_sur_cout_variable_unitaire": round(marge, 2), "seuil_en_quantite": round(q, 2),
            "seuil_en_chiffre_affaires": round(q * prix, 2)}


# ==========================================
# Plan Comptable Marocain (CGNC) : comptes et formulations d'opérations
# ==========================================
PCM = {
    "6111": ("Achats de marchandises", ["achat de marchandises destinées à la revente", "achat de marchandises",
             "acquisition d'articles destinés à être revendus en l'état", "achat de stock de marchandises pour le magasin"]),
    "6121": ("Achats de matières premières", ["achat de matières premières", "achat de matière première pour l'usine",
             "achat de tissu pour la confection", "achat d'acier pour la fabrication"]),
    "6125": ("Achats non stockés de matières et fournitures", ["facture d'électricité", "facture d'eau",
             "achat de fournitures de bureau", "consommation d'eau et d'électricité", "achat de petit outillage"]),
    "6131": ("Locations et charges locatives", ["loyer du local commercial", "location du bureau",
             "paiement du loyer mensuel", "location d'un entrepôt"]),
    "6133": ("Entretien et réparations", ["réparation de la machine", "entretien du matériel",
             "maintenance des équipements", "réparation du véhicule de service"]),
    "6134": ("Primes d'assurances", ["prime d'assurance", "assurance incendie des locaux",
             "assurance du parc automobile", "renouvellement de la police d'assurance"]),
    "6136": ("Rémunérations d'intermédiaires et honoraires", ["honoraires de l'expert-comptable",
             "honoraires de l'avocat", "frais de notaire", "commission versée à un intermédiaire"]),
    "6142": ("Transports", ["frais de transport sur ventes", "transport de marchandises par un transporteur",
             "frais de livraison payés au transporteur"]),
    "6143": ("Déplacements, missions et réceptions", ["billet d'avion pour une mission",
             "frais d'hôtel lors d'une mission", "repas d'affaires avec un client", "frais de déplacement du commercial"]),
    "6144": ("Publicité, publications et relations publiques", ["campagne publicitaire",
             "annonce publicitaire dans un journal", "publicité sur les réseaux sociaux", "impression de catalogues publicitaires"]),
    "6145": ("Frais postaux et de télécommunications", ["facture de téléphone", "abonnement internet",
             "frais d'envoi postal", "recharge téléphonique"]),
    "6147": ("Services bancaires", ["frais de tenue de compte", "commission bancaire sur virement",
             "frais de carte bancaire"]),
    "6161": ("Impôts et taxes directs", ["paiement de la taxe professionnelle", "taxe de services communaux",
             "règlement de la taxe professionnelle annuelle"]),
    "6171": ("Rémunérations du personnel", ["salaires du personnel", "paie du mois des employés",
             "prime de rendement des employés", "heures supplémentaires des ouvriers"]),
    "6174": ("Charges sociales", ["cotisations patronales cnss", "part patronale amo",
             "charges sociales patronales du mois"]),
    "6193": ("Dotations d'exploitation aux amortissements", ["dotation aux amortissements des machines",
             "amortissement annuel du matériel", "dotation aux amortissements du mobilier"]),
    "6311": ("Intérêts des emprunts et dettes", ["intérêts de l'emprunt bancaire", "intérêts sur crédit",
             "agios sur découvert bancaire"]),
    "7111": ("Ventes de marchandises", ["vente de marchandises", "vente de marchandises à un client",
             "revente d'articles achetés"]),
    "7121": ("Ventes de biens produits", ["vente de produits finis", "vente de la production de l'usine",
             "vente de produits fabriqués"]),
    "7124": ("Ventes de services produits", ["prestation de services facturée", "facturation d'une mission de conseil",
             "facture de maintenance à un client"]),
    "7381": ("Intérêts et produits assimilés", ["intérêts perçus sur dépôt à terme",
             "intérêts créditeurs du compte bancaire"]),
    "1111": ("Capital social", ["apport en capital des associés", "constitution du capital social",
             "augmentation de capital en numéraire"]),
    "1481": ("Emprunts auprès des établissements de crédit", ["obtention d'un emprunt bancaire",
             "crédit d'investissement accordé par la banque", "déblocage d'un prêt bancaire"]),
    "2321": ("Bâtiments", ["achat d'un bâtiment", "acquisition d'un local commercial", "construction d'un entrepôt"]),
    "2332": ("Matériel et outillage", ["achat d'une machine de production", "acquisition d'un tour industriel",
             "achat de matériel industriel"]),
    "2340": ("Matériel de transport", ["achat d'un camion", "acquisition d'un véhicule utilitaire",
             "achat d'une voiture de service"]),
    "2351": ("Mobilier de bureau", ["achat de bureaux et chaises", "acquisition de mobilier de bureau",
             "achat d'armoires de rangement"]),
    "2355": ("Matériel informatique", ["achat d'ordinateurs", "acquisition d'un serveur informatique",
             "achat d'imprimantes"]),
    "3421": ("Clients", ["encaissement d'une créance client", "règlement reçu d'un client"]),
    "4411": ("Fournisseurs", ["paiement d'un fournisseur", "règlement d'une facture fournisseur"]),
}

# ==========================================
# TVA 2026 : régime par type d'opération
# ==========================================
TVA_OPERATIONS = {
    "20 %": ["vente d'électricité", "location de compteur d'électricité", "vente de vêtements", "vente de meubles",
             "vente d'appareils électroménagers", "honoraires de conseil", "location de voitures",
             "vente de matériel informatique", "prestations de publicité", "vente de téléphones"],
    "10 %": ["hébergement à l'hôtel", "restauration", "opérations bancaires", "transport urbain de voyageurs",
             "transport routier de voyageurs", "énergie électrique d'origine renouvelable",
             "eau à usage industriel", "sucre raffiné", "voiture économique", "panneaux photovoltaïques",
             "chauffe-eau solaire"],
    "Exonéré": ["médicaments", "eau à usage domestique", "matières fertilisantes", "fournitures scolaires",
                "conserves de sardines", "lait en poudre", "savon de ménage", "pain", "lait",
                "pâtes alimentaires courtes non cuites"],
}

# ==========================================
# Juridique : quel texte de loi s'applique ?
# ==========================================
TEXTES_DE_LOI = {
    "Code du travail (loi 65-99)": ["licenciement d'un salarié", "durée légale du travail", "congé annuel payé",
                                    "contrat de travail à durée déterminée", "heures supplémentaires du salarié",
                                    "période d'essai d'un employé", "délégués du personnel"],
    "Code de commerce (loi 15-95)": ["inscription au registre de commerce", "fonds de commerce",
                                     "lettre de change et chèque", "obligations du commerçant",
                                     "difficultés de l'entreprise et redressement judiciaire"],
    "Délais de paiement (loi 69-21)": ["retard de paiement d'un client professionnel",
                                       "délai de paiement maximal entre entreprises", "amende pour retard de paiement"],
    "Sociétés anonymes (loi 17-95)": ["conseil d'administration", "assemblée générale des actionnaires",
                                      "commissaire aux comptes de la société anonyme", "émission d'actions"],
    "SARL et autres sociétés (loi 5-96)": ["parts sociales d'une sarl", "gérant de sarl", "cession de parts sociales",
                                           "sarl à associé unique", "société en nom collectif"],
    "Code général des impôts": ["déclaration de la tva", "impôt sur les sociétés", "impôt sur le revenu",
                                "droits d'enregistrement", "contrôle fiscal"],
    "Protection du consommateur (loi 31-08)": ["garantie d'un produit vendu", "droit de rétractation",
                                               "clause abusive dans un contrat", "publicité mensongère"],
    "Données personnelles (loi 09-08)": ["traitement des données personnelles des clients",
                                         "déclaration à la cndp", "fichier clients et vie privée"],
    "Baux commerciaux (loi 49-16)": ["renouvellement du bail commercial", "éviction du locataire commerçant",
                                     "loyer du local commercial et révision"],
    "Auto-entrepreneur (loi 114-13)": ["statut d'auto-entrepreneur", "plafond de chiffre d'affaires auto-entrepreneur",
                                       "inscription au registre national de l'auto-entrepreneur"],
}

# ==========================================
# Intelligence artificielle : quel type d'apprentissage ?
# ==========================================
TYPES_IA = {
    "Apprentissage supervisé": ["prédire le prix d'un appartement à partir d'exemples étiquetés",
                                "classer des emails en spam ou non spam avec des exemples annotés",
                                "prévoir les ventes à partir de l'historique", "détecter une fraude à partir de cas connus"],
    "Apprentissage non supervisé": ["regrouper des clients similaires sans étiquettes", "segmentation de la clientèle",
                                    "détecter des anomalies sans exemples connus", "réduire la dimension des données"],
    "Apprentissage par renforcement": ["un agent apprend par essais et récompenses", "apprendre à jouer seul contre lui-même",
                                       "robot qui apprend à marcher par récompense", "optimiser une stratégie par essais et erreurs"],
    "IA générative": ["rédiger un email automatiquement", "générer une image à partir d'un texte",
                      "résumer un rapport", "traduire un document", "assistant conversationnel qui répond aux questions"],
}


def resume_connaissances():
    """Texte de référence donné à l'assistant conversationnel."""
    lignes = [f"Base de connaissances IA AISSA — mise à jour {MISE_A_JOUR}.",
              "Barème IR annuel (tranche ≤ plafond : taux, somme à déduire) :"]
    lignes += [f"  ≤ {p:,.0f} : {t:.0%}, {d:,} DH" if p != float("inf") else f"  au-delà : {t:.0%}, {d:,} DH"
               for p, t, d in BAREME_IR]
    lignes += [
        f"IS proportionnel : {TAUX_IS_NORMAL:.0%} si bénéfice < {SEUIL_IS:,} DH, {TAUX_IS_GRANDES:.0%} au-delà "
        "(régimes spécifiques pour banques/assurances).",
        "TVA 2026 : taux normal 20 %, taux réduit 10 %, exonérations ; " +
        "; ".join(f"{k} : {', '.join(v)}" for k, v in TVA_OPERATIONS.items()),
        f"Paie : CNSS salarié {CNSS_SALARIE:.2%} plafonnée à {PLAFOND_CNSS_MENSUEL} DH/mois, AMO salarié {AMO_SALARIE:.2%} "
        f"non plafonnée, frais professionnels 35 % (brut annuel ≤ 78 000) ou 25 %, plafond {PLAFOND_FRAIS_PRO_ANNUEL:,} DH/an.",
        f"Sociétés : SA ≥ {ACTIONNAIRES_MIN_SA} actionnaires, capital ≥ {CAPITAL_MIN_SA:,} DH "
        f"({CAPITAL_MIN_SA_APE:,} DH avec appel public à l'épargne) ; SARL 1 à {ASSOCIES_MAX_SARL} associés, "
        "capital librement fixé ; auto-entrepreneur : CA ≤ 500 000 DH (commerce, industrie, artisanat) ou "
        "200 000 DH (services), impôt de 0,5 % / 1 % du CA.",
        "Création d'entreprise : certificat négatif (OMPIC), statuts, dépôt du capital, enregistrement, "
        "inscription au registre de commerce, identifiant fiscal et ICE, affiliation CNSS "
        "(démarches regroupées auprès des Centres Régionaux d'Investissement).",
        "Plan comptable marocain (CGNC) : classes 1 financement permanent, 2 actif immobilisé, 3 actif circulant, "
        "4 passif circulant, 5 trésorerie, 6 charges, 7 produits, 8 résultats. Comptes usuels : " +
        "; ".join(f"{c} {n}" for c, (n, _) in PCM.items()),
        "Textes de loi : " + "; ".join(TEXTES_DE_LOI),
    ]
    return "\n".join(lignes)
