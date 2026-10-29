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


# ==========================================
# Histoire du Maroc : les dynasties
# ==========================================
DYNASTIES = {
    "Idrissides (788-974)": ["arrivée d'idriss ier à volubilis", "fondation de fès", "idriss ii fait de fès sa capitale",
                             "première dynastie musulmane du maroc", "moulay idriss zerhoun", "construction de la mosquée al quaraouiyine par fatima al fihriya"],
    "Almoravides (1040-1147)": ["fondation de marrakech", "youssef ibn tachfine", "bataille de zallaqa en 1086",
                                "abdallah ibn yassin et le ribat", "empire du sahara jusqu'à l'andalousie au xie siècle"],
    "Almohades (1121-1269)": ["ibn toumert et le mouvement almohade", "abd al mumin unifie le maghreb",
                              "construction de la koutoubia", "tour hassan à rabat sous yacoub al mansour",
                              "bataille d'alarcos en 1195", "défaite de las navas de tolosa en 1212"],
    "Mérinides (1244-1465)": ["médersa bou inania de fès", "médersa attarine", "fondation de fès jdid",
                              "nécropole du chellah", "voyages d'ibn battuta sous abou inan", "ibn khaldoun à la cour de fès"],
    "Saadiens (1549-1659)": ["bataille des trois rois en 1578", "bataille d'oued el makhazen", "ahmed al mansour",
                             "palais el badi", "tombeaux saadiens de marrakech", "expédition vers tombouctou en 1591"],
    "Alaouites (depuis 1631)": ["moulay ismaïl fait de meknès sa capitale", "moulay rachid unifie le pays",
                                "indépendance du maroc en 1956 avec mohammed v", "marche verte de 1975 sous hassan ii",
                                "intronisation de mohammed vi en 1999", "manifeste de l'indépendance de 1944"],
}

# ==========================================
# Sciences : quelle discipline ?
# ==========================================
DISCIPLINES = {
    "Physique": ["loi d'ohm et résistance électrique", "chute libre et gravitation", "vitesse de la lumière",
                 "énergie cinétique d'un corps", "lois de newton sur le mouvement", "optique et réfraction"],
    "Chimie": ["réaction acide base et ph", "tableau périodique des éléments", "oxydoréduction",
               "molécule d'eau et liaison covalente", "concentration molaire d'une solution", "combustion du méthane"],
    "Biologie (SVT)": ["photosynthèse des plantes", "division cellulaire et mitose", "adn et génétique",
                       "système immunitaire et anticorps", "digestion chez l'homme", "évolution des espèces"],
    "Mathématiques": ["théorème de pythagore", "dérivée d'une fonction", "équation du second degré",
                      "probabilités et loi binomiale", "suites arithmétiques et géométriques", "intégrale et calcul d'aire"],
    "Géologie": ["tectonique des plaques", "formation des roches sédimentaires", "séisme et faille",
                 "volcan et magma", "chaîne de l'atlas et orogenèse", "fossiles et datation des couches"],
    "Astronomie": ["système solaire et planètes", "phases de la lune", "étoiles et galaxies",
                   "éclipse de soleil", "big bang et expansion de l'univers", "trou noir"],
}

# ==========================================
# Épistémologie : quel penseur ?
# ==========================================
EPISTEMOLOGUES = {
    "Karl Popper (falsifiabilité)": ["une théorie scientifique doit pouvoir être réfutée", "critère de falsifiabilité",
                                     "conjectures et réfutations", "la science progresse par élimination des erreurs"],
    "Thomas Kuhn (paradigmes)": ["révolutions scientifiques", "changement de paradigme", "science normale et anomalies",
                                "structure des révolutions scientifiques"],
    "Gaston Bachelard (obstacle épistémologique)": ["obstacle épistémologique", "rupture avec l'opinion commune",
                                                    "la formation de l'esprit scientifique", "l'opinion pense mal"],
    "René Descartes (rationalisme)": ["doute méthodique", "je pense donc je suis", "discours de la méthode",
                                      "la raison comme source de la connaissance"],
    "David Hume (empirisme)": ["problème de l'induction", "la connaissance vient de l'expérience",
                               "habitude et causalité", "empirisme sceptique"],
    "Auguste Comte (positivisme)": ["loi des trois états", "positivisme", "état théologique métaphysique et positif",
                                    "classification des sciences"],
    "Paul Feyerabend (anarchisme épistémologique)": ["contre la méthode", "tout est bon en science",
                                                     "anarchisme épistémologique", "pluralisme méthodologique"],
    "Ibn Khaldoun (méthode historique)": ["critique des récits historiques", "la muqaddima",
                                          "asabiyya et cycles des dynasties", "science de la civilisation umran"],
}

# ==========================================
# Marketing : le mix marketing (4P)
# ==========================================
MIX_MARKETING = {
    "Produit": ["caractéristiques et qualité du produit", "design et emballage", "gamme de produits",
                "marque et nom du produit", "garantie et service après-vente", "lancement d'une nouvelle version"],
    "Prix": ["fixation du prix de vente", "remise et promotion tarifaire", "prix psychologique à 99",
             "politique de prix d'écrémage", "prix de pénétration", "conditions de paiement"],
    "Distribution (Place)": ["choix des points de vente", "vente en ligne et e-commerce", "réseau de grossistes",
                             "franchise et distributeurs", "couverture géographique", "gestion des canaux de distribution"],
    "Communication (Promotion)": ["publicité à la télévision", "campagne sur les réseaux sociaux", "relations presse",
                                  "salon professionnel", "marketing d'influence", "parrainage et sponsoring"],
}

# ==========================================
# Commerce international : Incoterms 2020
# ==========================================
INCOTERMS = {
    "EXW (à l'usine)": ["le vendeur met la marchandise à disposition dans ses locaux", "l'acheteur s'occupe de tout dès l'usine",
                        "ex works marchandise non chargée"],
    "FCA (franco transporteur)": ["remise au transporteur désigné par l'acheteur", "vendeur dédouane à l'export et remet au transporteur",
                                  "free carrier tous modes"],
    "FAS (franco le long du navire)": ["marchandise livrée le long du navire au port d'embarquement",
                                       "free alongside ship sur le quai"],
    "FOB (franco à bord)": ["marchandise livrée à bord du navire au port d'embarquement", "free on board",
                            "risque transféré quand la marchandise est à bord au départ"],
    "CFR (coût et fret)": ["vendeur paie le fret maritime jusqu'au port de destination sans assurance",
                           "cost and freight"],
    "CIF (coût assurance fret)": ["vendeur paie fret maritime et assurance jusqu'au port de destination",
                                  "cost insurance freight maritime"],
    "CPT (port payé jusqu'à)": ["vendeur paie le transport jusqu'à destination tous modes sans assurance",
                                "carriage paid to"],
    "CIP (port payé assurance comprise)": ["vendeur paie transport et assurance jusqu'à destination tous modes",
                                           "carriage and insurance paid to couverture maximale"],
    "DAP (rendu au lieu de destination)": ["livré au lieu de destination prêt à être déchargé non dédouané à l'import",
                                           "delivered at place"],
    "DPU (rendu au lieu de destination déchargé)": ["livré et déchargé au lieu de destination",
                                                    "delivered at place unloaded déchargement par le vendeur"],
    "DDP (rendu droits acquittés)": ["vendeur livre dédouané droits et taxes payés chez l'acheteur",
                                     "delivered duty paid le vendeur supporte tout"],
}

# ==========================================
# Transit et douane au Maroc : documents et procédures
# ==========================================
TRANSIT = {
    "DUM (Déclaration Unique de Marchandises)": ["déclaration en douane des marchandises importées",
                                                 "déposer la déclaration en détail à la douane", "déclaration unique de marchandises"],
    "BADR (système informatique de la douane)": ["dédouanement électronique de la douane marocaine",
                                                 "système informatique de dédouanement", "dépôt de la déclaration en ligne sur badr"],
    "Connaissement (Bill of Lading)": ["titre de transport maritime", "document de transport par bateau représentant la marchandise",
                                       "bill of lading du transporteur maritime"],
    "LTA (Lettre de Transport Aérien)": ["document de transport par avion", "air waybill du fret aérien"],
    "Lettre de voiture CMR": ["document de transport routier international par camion", "transport par route vers l'europe"],
    "Certificat d'origine (EUR.1)": ["prouver l'origine pour bénéficier de l'accord préférentiel",
                                     "certificat de circulation pour exonération de droits avec l'union européenne", "origine préférentielle"],
    "Facture commerciale": ["document indiquant la valeur de la marchandise vendue", "prix et conditions de vente pour la douane"],
    "Liste de colisage": ["détail des colis poids et contenu de chaque carton", "packing list"],
}


def calculer_droits_import(valeur_caf, taux_droit_importation, taux_tva=0.20):
    """Droits et taxes à l'import (simplifié) : droit d'importation sur la valeur CAF, puis TVA à l'import
    sur (valeur CAF + droit). D'autres taxes peuvent s'ajouter selon le produit (TPI, TIC…)."""
    di = valeur_caf * taux_droit_importation
    tva = (valeur_caf + di) * taux_tva
    return {"valeur_caf": round(valeur_caf, 2), "droit_importation": round(di, 2), "tva_import": round(tva, 2),
            "total_droits_et_taxes": round(di + tva, 2), "cout_total_dedouane": round(valeur_caf + di + tva, 2),
            "remarque": "Vérifier le taux exact du produit dans le tarif douanier (ADII) et les taxes spécifiques."}


def quantite_wilson(demande_annuelle, cout_passation_commande, cout_stockage_unitaire_annuel):
    q = (2 * demande_annuelle * cout_passation_commande / cout_stockage_unitaire_annuel) ** 0.5
    n = demande_annuelle / q
    return {"quantite_economique": round(q, 1), "commandes_par_an": round(n, 2),
            "cout_total_gestion": round(n * cout_passation_commande + q / 2 * cout_stockage_unitaire_annuel, 2)}


# ==========================================
# Carte des sciences : les quatre grandes familles
# ==========================================
FAMILLES_SCIENCES = {
    "Sciences formelles": ["logique et raisonnement déductif", "algèbre et théorie des nombres", "géométrie et analyse",
                           "algorithmes et structures de données", "informatique théorique et calculabilité",
                           "statistiques et probabilités", "théorie des systèmes complexes", "théorie des graphes"],
    "Sciences naturelles": ["mécanique et thermodynamique", "physique quantique", "chimie organique",
                            "astronomie et cosmologie", "géologie et météorologie", "océanographie",
                            "microbiologie et bactéries", "génétique et hérédité", "zoologie et botanique",
                            "écologie des écosystèmes"],
    "Sciences humaines et sociales": ["économie et gestion des entreprises", "comptabilité et contrôle de gestion",
                                      "psychologie du comportement individuel", "sociologie des organisations",
                                      "science politique et gouvernance", "anthropologie des cultures",
                                      "histoire des civilisations", "linguistique et communication"],
    "Sciences appliquées": ["génie mécanique électrique et civil", "ingénierie aéronautique", "médecine clinique et chirurgie",
                            "pharmacie et santé publique", "agronomie et production alimentaire",
                            "technologie des aliments", "énergies renouvelables", "recyclage et valorisation des déchets"],
}

# ==========================================
# Droit marocain : civil, pénal, bancaire
# ==========================================
DROIT_MAROCAIN = {
    "DOC — Dahir des obligations et contrats (1913)": ["formation et validité d'un contrat", "responsabilité civile délictuelle",
                                                       "vice du consentement et nullité du contrat", "contrat de vente civile",
                                                       "prescription des obligations", "dommages et intérêts pour inexécution"],
    "Code de la famille — Moudawana (loi 70-03)": ["mariage et acte de mariage", "divorce et répudiation", "garde des enfants",
                                                   "pension alimentaire", "héritage et succession", "tutelle légale"],
    "Code pénal (1962)": ["vol et escroquerie", "abus de confiance", "faux et usage de faux", "corruption d'un agent public",
                          "infraction et peine d'emprisonnement", "chèque sans provision poursuites pénales"],
    "Loi bancaire 103-12 (établissements de crédit)": ["agrément d'une banque par bank al-maghrib",
                                                       "contrôle prudentiel des établissements de crédit",
                                                       "banques participatives", "protection de la clientèle bancaire",
                                                       "établissement de paiement"],
    "Loi 43-05 (blanchiment de capitaux)": ["blanchiment d'argent", "déclaration de soupçon",
                                            "vigilance sur l'origine des fonds", "lutte contre le financement du terrorisme"],
}

# ==========================================
# Droit comparé
# ==========================================
SYSTEMES_JURIDIQUES = {
    "Droit français (tradition civiliste)": ["code civil de 1804 code napoléon", "conseil d'état et cour de cassation française",
                                             "constitution de la ve république", "droit codifié d'inspiration romaine"],
    "Droit musulman (fiqh)": ["coran sunna ijmâ et qiyâs sources du droit", "écoles malikite hanafite chafiite hanbalite",
                              "fatwa d'un mufti", "maqasid al charia finalités de la loi"],
    "Droits des pays arabes (codes modernes)": ["code civil égyptien de 1948 rédigé par sanhouri",
                                                "codes civils inspirés du modèle de sanhouri",
                                                "mixte de droit civil européen et de fiqh", "codification moderne des pays arabes"],
    "Droit marocain": ["dahir des obligations et contrats", "constitution marocaine de 2011", "rite malékite et moudawana",
                       "cour de cassation du royaume"],
    "Common law": ["règle du précédent stare decisis", "jurisprudence anglaise et américaine", "jury populaire au civil",
                   "droit non codifié des juges"],
}

# ==========================================
# Fiscalité complète : quel impôt ?
# ==========================================
QUEL_IMPOT = {
    "IS (impôt sur les sociétés)": ["bénéfice annuel d'une sarl", "résultat fiscal d'une société anonyme", "impôt sur le bénéfice de la société"],
    "IR (impôt sur le revenu)": ["salaire d'un employé", "loyer perçu d'un appartement", "bénéfice d'un commerçant personne physique",
                                 "plus-value sur la vente d'un terrain par un particulier"],
    "TVA": ["vente facturée à un client", "prestation de services facturée", "taxe sur le chiffre d'affaires collectée"],
    "Droits d'enregistrement": ["achat d'un terrain par acte notarié", "cession de parts sociales", "constitution de société et enregistrement des statuts"],
    "Taxe professionnelle": ["impôt local sur l'activité selon la valeur locative du local", "exercice d'une activité commerciale dans un local"],
    "Taxe de services communaux": ["taxe sur les services de la commune liée au local", "assainissement et voirie communale"],
    "Retenue à la source": ["dividendes versés aux associés", "intérêts versés à un prêteur", "honoraires versés à un non résident"],
    "Cotisation minimale": ["société en déficit paie un minimum sur son chiffre d'affaires", "minimum d'impôt même sans bénéfice"],
}

# ==========================================
# Gestion d'entreprise : quelle fonction ?
# ==========================================
FONCTIONS_ENTREPRISE = {
    "Direction générale": ["fixer la vision et les objectifs", "arbitrer entre les directions", "représenter l'entreprise"],
    "Finance et comptabilité": ["tenir la comptabilité", "gérer la trésorerie", "établir le budget annuel"],
    "Ressources humaines": ["recruter un collaborateur", "établir la paie", "former les salariés"],
    "Production": ["planifier la fabrication", "contrôler la qualité des produits", "maintenir les machines"],
    "Commercial et marketing": ["prospecter de nouveaux clients", "fixer la politique de prix", "lancer une campagne publicitaire"],
    "Achats et logistique": ["négocier avec les fournisseurs", "gérer les stocks", "organiser les livraisons"],
    "Juridique": ["rédiger les contrats", "gérer les litiges", "veiller à la conformité réglementaire"],
}

# ==========================================
# Stratégie et management stratégique
# ==========================================
OUTILS_STRATEGIQUES = {
    "SWOT": ["forces faiblesses opportunités menaces", "diagnostic interne et externe de l'entreprise"],
    "PESTEL": ["facteurs politiques économiques sociaux technologiques écologiques et légaux", "analyse du macro-environnement"],
    "5 forces de Porter": ["pouvoir de négociation des clients et des fournisseurs", "menace des nouveaux entrants et des substituts",
                           "intensité concurrentielle du secteur"],
    "Matrice BCG": ["portefeuille d'activités vedettes vaches à lait dilemmes et poids morts",
                    "croissance du marché et part de marché relative"],
    "Chaîne de valeur": ["activités principales et de soutien créatrices de valeur", "décomposer l'entreprise en activités"],
    "Stratégies génériques de Porter": ["domination par les coûts", "différenciation de l'offre", "stratégie de focalisation sur une niche"],
    "Matrice d'Ansoff": ["pénétration de marché développement de produits", "diversification et développement de marché"],
}

# ==========================================
# Banque : quelle opération ?
# ==========================================
OPERATIONS_BANCAIRES = {
    "Crédit": ["prêt immobilier", "crédit de trésorerie à une entreprise", "découvert autorisé", "crédit à la consommation"],
    "Dépôts et épargne": ["ouverture d'un compte courant", "dépôt à terme", "compte d'épargne rémunéré"],
    "Moyens de paiement": ["virement bancaire", "carte bancaire", "chèque", "lettre de change et effet de commerce"],
    "Change et international": ["achat de devises", "crédit documentaire à l'import", "remise documentaire", "transfert vers l'étranger"],
    "Marchés de capitaux": ["introduction en bourse", "émission d'obligations", "gestion d'opcvm", "achat d'actions à la bourse de casablanca"],
    "Réglementation prudentielle": ["ratio de solvabilité bâle", "exigence de fonds propres", "supervision par bank al-maghrib", "ratio de liquidité"],
}

# ==========================================
# Statistiques : quelle notion ?
# ==========================================
NOTIONS_STATISTIQUES = {
    "Moyenne": ["somme des valeurs divisée par leur nombre", "valeur moyenne d'une série"],
    "Médiane": ["valeur qui partage la série en deux moitiés", "valeur centrale peu sensible aux valeurs extrêmes"],
    "Écart-type et variance": ["dispersion autour de la moyenne", "mesurer la variabilité des données"],
    "Corrélation": ["lien entre deux variables", "coefficient entre moins un et un"],
    "Régression": ["prévoir une variable à partir d'une autre", "droite des moindres carrés"],
    "Test d'hypothèse": ["hypothèse nulle et seuil de signification", "p-valeur et rejet de l'hypothèse"],
    "Intervalle de confiance": ["fourchette contenant le vrai paramètre à 95 %", "marge d'erreur d'un sondage"],
    "Loi normale": ["courbe en cloche de gauss", "distribution symétrique autour de la moyenne"],
}

# ==========================================
# Faits économiques et sociaux
# ==========================================
FAITS_ECONOMIQUES = {
    "Croissance économique": ["augmentation du pib réel", "hausse de la production de richesses sur longue période"],
    "Inflation": ["hausse générale et durable des prix", "perte de pouvoir d'achat de la monnaie"],
    "Chômage": ["personnes sans emploi qui en cherchent un", "taux de chômage des jeunes diplômés"],
    "Mondialisation": ["intensification des échanges internationaux", "firmes multinationales et délocalisations"],
    "Développement durable": ["répondre aux besoins présents sans compromettre les générations futures", "transition écologique"],
    "Inégalités sociales": ["écart de revenus entre riches et pauvres", "coefficient de gini", "mobilité sociale"],
    "Politique budgétaire": ["dépenses publiques et déficit de l'état", "loi de finances et relance par l'investissement public"],
    "Exode rural et urbanisation": ["migration des campagnes vers les villes", "croissance des villes et habitat"],
}

# ==========================================
# Visa et voyage : quelle pièce du dossier ?
# ==========================================
DOSSIER_VISA = {
    "Identité": ["passeport valide encore trois mois après le retour", "photos d'identité récentes", "copie de la carte nationale"],
    "Justificatifs financiers": ["relevés bancaires des trois derniers mois", "attestation de revenus", "preuve de moyens de subsistance"],
    "Hébergement": ["réservation d'hôtel", "attestation d'accueil chez un proche", "contrat de location sur place"],
    "Assurance voyage": ["assurance médicale de voyage couvrant au moins 30 000 euros", "assurance rapatriement"],
    "Motif du voyage": ["lettre d'invitation d'une entreprise", "ordre de mission", "inscription dans une université étrangère",
                        "réservation de circuit touristique"],
    "Situation professionnelle": ["attestation de travail", "autorisation de congé", "registre de commerce du demandeur"],
    "Transport": ["réservation du billet d'avion aller-retour", "itinéraire du voyage"],
}
TYPES_VISA = "Visa Schengen de court séjour (type C : 90 jours au plus sur 180), visa national de long séjour (type D), visa de transit aéroportuaire (type A)."


# ==========================================
# Matières scolaires marocaines (primaire, collège, lycée)
# ==========================================
REGIONS_MAROC = {
    "Tanger-Tétouan-Al Hoceïma": ["tanger", "tétouan", "al hoceïma", "larache", "chefchaouen", "ksar el kébir"],
    "Oriental": ["oujda", "nador", "berkane", "taourirt", "jerada", "figuig"],
    "Fès-Meknès": ["fès", "meknès", "taza", "ifrane", "sefrou", "taounate"],
    "Rabat-Salé-Kénitra": ["rabat", "salé", "kénitra", "témara", "khémisset", "sidi kacem"],
    "Béni Mellal-Khénifra": ["béni mellal", "khénifra", "khouribga", "azilal", "fquih ben salah"],
    "Casablanca-Settat": ["casablanca", "mohammedia", "settat", "el jadida", "berrechid", "benslimane"],
    "Marrakech-Safi": ["marrakech", "safi", "essaouira", "el kelâa des sraghna", "youssoufia", "chichaoua"],
    "Drâa-Tafilalet": ["errachidia", "ouarzazate", "zagora", "tinghir", "midelt"],
    "Souss-Massa": ["agadir", "taroudant", "tiznit", "inezgane", "chtouka aït baha"],
    "Guelmim-Oued Noun": ["guelmim", "tan-tan", "sidi ifni", "assa"],
    "Laâyoune-Sakia El Hamra": ["laâyoune", "boujdour", "tarfaya", "es-semara"],
    "Dakhla-Oued Ed-Dahab": ["dakhla", "aousserd"],
}
SYSTEMES_CORPS = {
    "Système digestif": ["estomac", "intestin grêle", "foie", "œsophage", "pancréas", "côlon"],
    "Système respiratoire": ["poumons", "trachée", "bronches", "alvéoles pulmonaires", "diaphragme"],
    "Système circulatoire": ["cœur", "artères", "veines", "capillaires sanguins", "globules rouges"],
    "Système nerveux": ["cerveau", "moelle épinière", "neurones", "nerfs", "cervelet"],
    "Appareil urinaire": ["reins", "vessie", "uretères", "néphrons"],
    "Système locomoteur": ["os", "muscles", "articulations", "tendons", "squelette"],
}
UNITES_SI = {
    "Newton (N)": ["force", "poids d'un corps", "force de frottement"],
    "Joule (J)": ["énergie", "travail d'une force", "énergie cinétique", "quantité de chaleur"],
    "Watt (W)": ["puissance", "puissance électrique d'un appareil"],
    "Volt (V)": ["tension électrique", "différence de potentiel"],
    "Ampère (A)": ["intensité du courant électrique", "courant dans un circuit"],
    "Ohm (Ω)": ["résistance électrique", "résistance d'un conducteur ohmique"],
    "Pascal (Pa)": ["pression", "pression atmosphérique", "pression d'un gaz"],
    "Mole (mol)": ["quantité de matière", "nombre de moles d'un réactif"],
    "Mètre par seconde (m/s)": ["vitesse", "vitesse moyenne d'un mobile"],
    "Kilogramme (kg)": ["masse", "masse d'un objet"],
}
NATURE_MOTS = {
    "Nom": ["la maison", "un enfant", "le cahier", "la liberté", "une ville", "le soleil", "les élèves", "un professeur"],
    "Verbe": ["manger", "il court", "nous chantons", "elles finissaient", "tu écriras", "aller", "vous parlez", "je suis venu"],
    "Adjectif": ["grand", "magnifique", "rapide", "heureuse", "verte", "intelligents", "difficile", "petite"],
    "Adverbe": ["rapidement", "souvent", "très", "hier", "lentement", "toujours", "jamais", "doucement"],
    "Préposition": ["dans", "avec", "pour", "sans", "sous", "chez", "entre", "vers"],
    "Pronom": ["je", "nous", "celui-ci", "lequel", "eux", "le mien", "quelqu'un", "personne"],
}
NAHW_ARABE = {
    "اسم": ["المدرسة", "الكتاب", "التلميذ", "مدينة", "القلم", "المعلمون", "الشمس", "بيت", "الحرية", "مكتبة"],
    "فعل": ["كتب", "يكتب", "اكتب", "ذهب", "يذهبون", "سافرت", "يدرس", "قرأ", "سيلعب", "تعلمنا"],
    "حرف": ["في", "من", "إلى", "على", "عن", "لم", "لن", "هل", "ثم", "لكن"],
}
TEMPS_ANGLAIS = {
    "Present simple": ["she works every day", "they play football on sundays", "he likes coffee", "i live in rabat"],
    "Present continuous": ["she is working now", "they are playing outside", "i am reading a book", "we are studying"],
    "Past simple": ["she worked yesterday", "they played last week", "i visited fes in 2020", "he went home"],
    "Present perfect": ["she has worked here since 2019", "i have never seen snow", "they have finished", "he has just arrived"],
    "Future (will)": ["she will work tomorrow", "i will call you later", "they will travel next year", "it will rain"],
}
PHILOSOPHES = {
    "Socrate": ["connais-toi toi-même", "maïeutique", "je sais que je ne sais rien"],
    "Platon": ["allégorie de la caverne", "monde des idées", "la république et le philosophe roi"],
    "Aristote": ["juste milieu", "syllogisme et logique", "l'homme est un animal politique"],
    "Al-Farabi": ["la cité vertueuse", "le second maître après aristote"],
    "Ibn Sina (Avicenne)": ["argument de l'homme volant", "canon de la médecine", "distinction entre essence et existence"],
    "Ibn Rochd (Averroès)": ["discours décisif sur l'accord entre religion et philosophie", "commentateur d'aristote"],
    "Descartes": ["cogito ergo sum", "dualisme de l'âme et du corps", "doute méthodique"],
    "Kant": ["impératif catégorique", "critique de la raison pure", "agis selon la maxime universelle"],
    "Nietzsche": ["dieu est mort", "le surhomme", "volonté de puissance"],
    "Sartre": ["l'existence précède l'essence", "l'homme est condamné à être libre", "l'enfer c'est les autres"],
}
MATIERES_SCOLAIRES = {
    "Mathématiques": ["résoudre une équation", "calculer l'aire d'un triangle", "simplifier une fraction",
                      "étudier les variations d'une fonction", "calculer une probabilité"],
    "Physique-chimie": ["mesurer la tension dans un circuit", "équilibrer une équation chimique",
                        "calculer la vitesse d'un mobile", "étudier la réfraction de la lumière"],
    "SVT": ["décrire la digestion", "observer une cellule au microscope", "expliquer la photosynthèse",
            "étudier la transmission des caractères héréditaires"],
    "Français": ["conjuguer un verbe au passé simple", "analyser un poème", "rédiger un texte argumentatif",
                 "accorder le participe passé"],
    "Arabe": ["إعراب الجملة", "تحليل قصيدة", "كتابة إنشاء", "تصريف الفعل"],
    "Anglais": ["write an email in english", "use the present perfect", "english vocabulary about travel"],
    "Histoire-géographie": ["étudier la dynastie des almohades", "lire une carte du relief du maroc",
                            "analyser la seconde guerre mondiale", "étudier le climat et les régions"],
    "Éducation islamique": ["التربية الإسلامية", "étudier les piliers de l'islam", "sourate et tafsir"],
    "Philosophie": ["disserter sur la liberté", "la notion de vérité", "analyser un texte philosophique sur l'état"],
    "Informatique": ["écrire un algorithme", "programmer en python", "utiliser un tableur", "structure d'un ordinateur"],
}


# ==========================================
# Lycée et université
# ==========================================
EPOQUES = {
    "Antiquité (jusqu'en 476)": ["construction des pyramides d'égypte", "démocratie athénienne", "empire romain",
                                 "royaume de maurétanie et juba ii", "volubilis cité romaine", "carthage et les guerres puniques"],
    "Moyen Âge (476-1492)": ["naissance de l'islam en 622", "fondation de fès", "croisades", "maison de la sagesse de bagdad",
                             "al-andalus et cordoue", "construction de la koutoubia"],
    "Époque moderne (1492-1789)": ["découverte de l'amérique par christophe colomb", "imprimerie de gutenberg diffusée",
                                   "renaissance italienne", "bataille des trois rois", "règne de moulay ismaïl", "réforme protestante"],
    "Époque contemporaine (depuis 1789)": ["révolution française", "révolution industrielle", "première guerre mondiale",
                                           "seconde guerre mondiale", "indépendance du maroc en 1956", "chute du mur de berlin"],
}
OEUVRES_FR = {
    "La Boîte à merveilles (Ahmed Sefrioui)": ["sidi mohammed enfant dans la médina de fès", "le msid et lalla zoubida",
                                               "souvenirs d'enfance d'un garçon de six ans à fès"],
    "Antigone (Jean Anouilh)": ["fille d'œdipe qui veut enterrer son frère polynice", "elle refuse la loi de créon",
                                "tragédie moderne jouée en 1944"],
    "Le Dernier Jour d'un condamné (Victor Hugo)": ["un condamné à mort écrit son journal avant l'exécution",
                                                    "plaidoyer contre la peine de mort", "bicêtre et la conciergerie"],
    "Il était une fois un vieux couple heureux (Mohammed Khaïr-Eddine)": ["un vieux couple dans un village du sud marocain",
                                                                         "le vieux poète et sa femme dans la montagne du souss"],
    "Le Cid (Pierre Corneille)": ["rodrigue doit venger l'honneur de son père", "chimène et le dilemme cornélien"],
    "Les Misérables (Victor Hugo)": ["jean valjean ancien forçat", "cosette et les thénardier", "javert le policier"],
}
ADAB_ARABE = {
    "المتنبي": ["الخيل والليل والبيداء تعرفني", "شاعر العصر العباسي ومدح سيف الدولة", "أبو الطيب المتنبي"],
    "أحمد شوقي": ["أمير الشعراء", "مصرع كليوباترا", "الشوقيات"],
    "طه حسين": ["عميد الأدب العربي", "كتاب الأيام", "في الشعر الجاهلي"],
    "نجيب محفوظ": ["الثلاثية بين القصرين", "جائزة نوبل للآداب", "زقاق المدق"],
    "جبران خليل جبران": ["كتاب النبي", "الأجنحة المتكسرة", "أدب المهجر والرابطة القلمية"],
    "محمد شكري": ["الخبز الحافي", "الشطار", "طنجة في سيرته الذاتية"],
}
ECOLES_ECONOMIQUES = {
    "Classiques (Smith, Ricardo)": ["la main invisible du marché", "avantages comparatifs dans le commerce international",
                                    "division du travail et la manufacture d'épingles", "la richesse des nations"],
    "Néoclassiques (Walras, Marshall)": ["utilité marginale", "équilibre général des marchés", "concurrence pure et parfaite"],
    "Marxistes": ["plus-value et exploitation", "lutte des classes", "accumulation du capital", "le capital de marx"],
    "Keynésiens": ["demande effective", "effet multiplicateur de l'investissement", "relance budgétaire contre le chômage",
                   "théorie générale de l'emploi"],
    "Monétaristes (Friedman)": ["l'inflation est toujours un phénomène monétaire", "contrôle de la masse monétaire",
                                "taux de chômage naturel"],
    "Schumpeter": ["destruction créatrice", "l'entrepreneur innovateur", "cycles d'innovation"],
}
METHODES_COUTS = {
    "Coût complet (sections homogènes)": ["centres d'analyse et unités d'œuvre", "répartition primaire et secondaire des charges indirectes"],
    "Coûts variables (direct costing)": ["marge sur coût variable", "séparer charges fixes et variables"],
    "Imputation rationnelle": ["coefficient d'activité normale", "coût de sous-activité"],
    "Méthode ABC": ["activités et inducteurs de coûts", "activity based costing"],
    "Coûts standards": ["coût préétabli et analyse des écarts sur quantité et prix", "écart sur matière et sur main-d'œuvre"],
    "Coût marginal": ["coût de la dernière unité produite", "coût d'une commande supplémentaire"],
}
OUTILS_FINANCE = {
    "VAN": ["valeur actuelle nette des flux actualisés", "somme des flux actualisés moins l'investissement"],
    "TRI": ["taux de rentabilité interne", "taux qui annule la valeur actuelle nette"],
    "Délai de récupération": ["temps pour récupérer le capital investi", "payback"],
    "BFR": ["besoin en fonds de roulement", "stocks plus créances clients moins dettes fournisseurs"],
    "CMPC (WACC)": ["coût moyen pondéré du capital", "coût des fonds propres et de la dette pondéré"],
    "Effet de levier": ["l'endettement augmente la rentabilité des capitaux propres", "levier financier"],
    "Capacité d'autofinancement": ["caf", "ressource interne dégagée par l'activité"],
}
STRUCTURES_DONNEES = {
    "Pile (LIFO)": ["dernier entré premier sorti", "empiler et dépiler", "pile d'appels de fonctions"],
    "File (FIFO)": ["premier entré premier sorti", "file d'attente", "enfiler et défiler"],
    "Liste chaînée": ["chaque élément pointe vers le suivant", "insertion sans décaler les éléments"],
    "Arbre": ["racine nœuds et feuilles", "arbre binaire de recherche", "structure hiérarchique"],
    "Graphe": ["sommets et arêtes", "réseau routier et plus court chemin", "parcours en largeur"],
    "Table de hachage": ["clé et valeur avec fonction de hachage", "dictionnaire accès en temps constant"],
}
COMPLEXITES = {
    "O(1)": ["accès à un élément d'un tableau par son indice", "empiler un élément"],
    "O(log n)": ["recherche dichotomique dans un tableau trié", "recherche dans un arbre binaire équilibré"],
    "O(n)": ["parcours d'un tableau", "recherche séquentielle", "trouver le maximum d'une liste"],
    "O(n log n)": ["tri fusion", "tri rapide en moyenne", "tri par tas"],
    "O(n²)": ["tri à bulles", "tri par insertion dans le pire cas", "deux boucles imbriquées"],
}
BRANCHES_DROIT = {
    "Droit constitutionnel (public)": ["organisation des pouvoirs de l'état", "constitution et parlement", "élections législatives"],
    "Droit administratif (public)": ["contrat administratif et marché public", "recours contre une décision de l'administration",
                                     "fonction publique"],
    "Droit fiscal (public)": ["contentieux fiscal", "assiette et recouvrement de l'impôt"],
    "Droit civil (privé)": ["contrat entre particuliers", "propriété d'un bien", "responsabilité civile"],
    "Droit commercial (privé)": ["fonds de commerce", "sociétés commerciales", "effets de commerce"],
    "Droit du travail (privé)": ["licenciement abusif", "contrat de travail", "salaire minimum"],
    "Droit international": ["traités entre états", "conflit de lois entre pays", "droit de la mer"],
}
THEORIES_ORGANISATIONS = {
    "Taylor (organisation scientifique du travail)": ["chronométrage des tâches", "one best way", "division verticale du travail"],
    "Fayol (administration industrielle)": ["prévoir organiser commander coordonner contrôler", "quatorze principes d'administration"],
    "Weber (bureaucratie)": ["autorité rationnelle légale", "règles impersonnelles et hiérarchie"],
    "Mayo (relations humaines)": ["expériences de hawthorne", "importance du groupe et du climat social"],
    "Maslow (besoins)": ["pyramide des besoins", "besoin d'accomplissement de soi"],
    "Herzberg (motivation)": ["facteurs d'hygiène et facteurs moteurs", "enrichissement des tâches"],
    "Mintzberg (configurations)": ["sommet stratégique et centre opérationnel", "configurations structurelles et rôles du manager"],
}
AUTEURS_SCIENCES_SOCIALES = {
    "Émile Durkheim": ["le fait social", "le suicide étude sociologique", "solidarité mécanique et organique"],
    "Max Weber": ["éthique protestante et esprit du capitalisme", "idéal-type", "sociologie compréhensive"],
    "Pierre Bourdieu": ["habitus", "capital culturel", "la reproduction sociale"],
    "Sigmund Freud": ["l'inconscient", "le moi le ça et le surmoi", "interprétation des rêves"],
    "Jean Piaget": ["stades du développement de l'enfant", "assimilation et accommodation"],
    "Ivan Pavlov": ["conditionnement classique", "le chien et la cloche"],
}


def mensualite_credit(capital, taux_annuel, duree_mois):
    t = taux_annuel / 12
    m = capital / duree_mois if t == 0 else capital * t / (1 - (1 + t) ** -duree_mois)
    return {"mensualite": round(m, 2), "cout_total_credit": round(m * duree_mois - capital, 2)}


def statistiques_descriptives(valeurs):
    import statistics
    v = [float(x) for x in valeurs]
    return {"n": len(v), "moyenne": round(statistics.fmean(v), 4), "mediane": statistics.median(v),
            "ecart_type": round(statistics.stdev(v), 4) if len(v) > 1 else 0.0, "minimum": min(v), "maximum": max(v)}


def position_bcg(croissance_marche, part_marche_relative):
    forte_croissance, leader = croissance_marche >= 0.10, part_marche_relative >= 1
    return {(True, True): "Vedette", (False, True): "Vache à lait", (True, False): "Dilemme",
            (False, False): "Poids mort"}[(forte_croissance, leader)]


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
        "Dynasties marocaines : " + "; ".join(DYNASTIES),
        "Incoterms 2020 : " + "; ".join(f"{k} : {v[0]}" for k, v in INCOTERMS.items()),
        "Transit et douane : " + "; ".join(f"{k} : {v[0]}" for k, v in TRANSIT.items()),
        "Droit marocain : " + "; ".join(DROIT_MAROCAIN) + ". Systèmes juridiques comparés : " + "; ".join(SYSTEMES_JURIDIQUES),
        "Fiscalité — quel impôt : " + "; ".join(f"{k} : {', '.join(v)}" for k, v in QUEL_IMPOT.items()),
        "Visa : " + TYPES_VISA + " Pièces : " + "; ".join(DOSSIER_VISA),
        "Stratégie : " + "; ".join(OUTILS_STRATEGIQUES) + ". Matrice BCG : seuils 10 % de croissance et part relative 1.",
        "Marketing : mix 4P (produit, prix, distribution, communication) ; cycle de vie : lancement, croissance, "
        "maturité, déclin. Logistique : quantité économique de Wilson Q* = racine(2 × demande × coût de commande / "
        "coût de stockage unitaire).",
    ]
    return "\n".join(lignes)
