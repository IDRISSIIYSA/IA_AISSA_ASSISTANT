"""
Les impôts décortiqués : IR, IS, TVA, état 9421, déclaration du revenu global, revenus fonciers (loyers), documents et
attestations de régularité. Pour chacun : qui est concerné, base, taux par exercice, cas par secteur d'activité,
déclarations et délais, paiement et liquidation, sanctions, références ; plus les passages du CGI qu'IA AISSA a lus.

Délais et taux vérifiés le 30/10/2026 (CGI et cabinets cités). Les listes sectorielles indiquent les cas les plus
courants : la liste complète est dans les articles cités.
"""

import pandas as pd

from . import baremes as B

SECTEURS = ["Tous secteurs (droit commun)", "Commerce et distribution", "Industrie", "Services et professions libérales",
            "Banques et assurances", "Hôtellerie et restauration", "Agriculture", "Immobilier et promotion immobilière",
            "Export"]


def taux_ir_par_exercice():
    return pd.DataFrame([{"Exercices": f"{p['de']}–{p['a']}", "Tranches": " ; ".join(
        ("au-delà" if t[0] == float("inf") else f"≤ {t[0]:,.0f}".replace(",", " ")) + f" : {t[1]:.0%}" for t in p["bareme"]),
        "Loi": p["loi"]} for p in B.IR])


def taux_tva_par_exercice():
    return pd.DataFrame([{"Exercices": f"{p['de']}–{p['a']}", "Taux normal": f"{p['taux']['normal']:.0%}",
                          "Taux réduits": ", ".join(f"{t:.0%}" if isinstance(t, float) else t for t in p["taux"]["réduits"]),
                          "Remarque": p["remarque"]} for p in B.TVA])


def taux_is_par_exercice():
    return pd.DataFrame([{"Exercices": f"{p['de']}–{p['a']}", **{k: f"{v:.0%}" for k, v in p["taux"].items()},
                          "Cotisation minimale": f"{p['cotisation_minimale']['taux']:.2%} (min. 3 000 DH)"} for p in B.IS])


# Pour chaque impôt : sections (titre, lignes) ; par secteur : {secteur: ligne}
FICHES = {
    "IR décortiqué": {
        "question": "impôt sur le revenu barème article 73 revenu global",
        "sections": [
            ("Qui est concerné", ["Les personnes physiques résidentes au Maroc sur tous leurs revenus, et les non-résidents "
                                  "sur leurs revenus de source marocaine (CGI, art. 23)."]),
            ("Les catégories de revenus", ["Revenus professionnels (réel, simplifié, CPU, auto-entrepreneur) ; revenus "
                                           "agricoles ; salaires et pensions ; revenus et profits fonciers ; revenus et "
                                           "profits de capitaux mobiliers (CGI, art. 22)."]),
            ("Base imposable", ["Salaires : brut − cotisations sociales − frais professionnels (35 % jusqu'à 78 000 DH "
                                "par an, 25 % au-delà, plafond 35 000 DH ; art. 59).",
                                "Revenus professionnels au réel : bénéfice comptable corrigé des réintégrations et "
                                "déductions fiscales (art. 33 à 37).",
                                "Revenu global : somme des revenus nets catégoriels, moins les déductions de l'art. 28 "
                                "(retraite complémentaire, intérêts du logement principal, dons)."]),
            ("Calcul", ["IR = revenu net imposable × taux de la tranche − somme à déduire ; puis réduction pour "
                        "charges de famille (art. 74), au plus 6 personnes."]),
            ("Déclarations et délais", ["Salariés : retenue à la source par l'employeur chaque mois (art. 156), versée "
                                        "avant la fin du mois suivant (art. 174).",
                                        "Revenu global : avant le 1er mai pour les revenus professionnels au réel ou "
                                        "simplifié ; avant le 1er mars pour les salaires, revenus fonciers et de capitaux "
                                        "sans revenu professionnel (art. 82-I) ; CPU : avant le 1er avril (art. 82 quater)."]),
            ("Dispensés de déclaration", ["Salarié d'un seul employeur, sans autre revenu, IR retenu à la source ; revenus "
                                          "soumis à un prélèvement libératoire (art. 86)."]),
            ("Sanctions", ["Retard ou défaut de déclaration : art. 184 ; paiement tardif : pénalité et majorations de "
                           "l'art. 208 (voir la simulation « Pénalités de retard »)."]),
        ],
        "secteurs": {
            "Services et professions libérales": "Cotisation minimale de 6 % pour les professions libérales listées "
                                                 "(CGI, art. 144-I-D) ; facturation avec ICE obligatoire.",
            "Agriculture": "Revenus agricoles imposables au-delà du seuil de chiffre d'affaires fixé par l'art. 47 ; "
                           "l'exonération de déclaration de l'art. 86-1° est supprimée depuis 2023.",
            "Commerce et distribution": "Choix entre réel, simplifié, CPU (petits commerçants) ou auto-entrepreneur selon "
                                        "les plafonds de chiffre d'affaires (art. 39, 40, 41).",
        },
        "tableau": taux_ir_par_exercice,
        "simulations": ["IR (impôt sur le revenu)", "Bulletin de paie complet", "Revenus fonciers (loyers)"],
        "references": ["CGI, art. 22 à 86 (IR), 144 (minimum), 156 et 174 (retenue à la source)"],
    },
    "IS décortiqué": {
        "question": "impôt sur les sociétés taux article 19 cotisation minimale",
        "sections": [
            ("Qui est concerné", ["Les sociétés (SARL, SA, SNC ayant opté…), les établissements publics à caractère "
                                  "lucratif, les succursales de sociétés étrangères (CGI, art. 2)."]),
            ("Base imposable", ["Résultat fiscal = résultat comptable + réintégrations (charges non déductibles, "
                                "amendes, amortissements excédentaires, part non déductible des véhicules) − "
                                "déductions (produits exonérés, dividendes reçus, abattements) (art. 8 à 12)."]),
            ("Calcul", ["IS = résultat fiscal × taux de l'exercice ; IS dû = le plus élevé de l'IS et de la cotisation "
                        "minimale (0,25 % des produits, au moins 3 000 DH ; art. 144), sauf les 36 premiers mois."]),
            ("Déclarations et délais", ["Déclaration du résultat fiscal et liasse fiscale dans les 3 mois suivant la "
                                        "clôture (art. 20-I), sur SIMPL-IS."]),
            ("Paiement et liquidation", ["4 acomptes de 25 % de l'IS de l'exercice précédent, avant la fin des 3e, 6e, "
                                         "9e et 12e mois (art. 170-I) ; liquidation dans les 3 mois suivant la clôture : "
                                         "complément payé, ou excédent imputé sur les acomptes suivants (art. 170-IV)."]),
            ("Sanctions", ["Défaut ou retard de déclaration : art. 184 ; paiement tardif : art. 208 ; défaut de "
                           "présentation de la comptabilité : art. 191."]),
        ],
        "secteurs": {
            "Banques et assurances": "Taux de 40 % (CGI, art. 19) pour les établissements de crédit, Bank Al-Maghrib, "
                                     "la CDG et les entreprises d'assurances et de réassurance.",
            "Industrie": "Convergence vers le taux unique de 20 % (LF 2023) ; régimes d'incitation des zones "
                         "d'accélération industrielle à vérifier dans l'art. 6.",
            "Export": "Les anciens taux réduits des exportateurs convergent vers 20 % (LF 2023) ; vérifiez le régime "
                      "transitoire de l'exercice (art. 247).",
            "Immobilier et promotion immobilière": "Logement social et conventions avec l'État : exonérations "
                                                   "spécifiques sous conditions (art. 7 et 247).",
            "Commerce et distribution": "Taux réduits de cotisation minimale pour certains produits de base "
                                        "(produits pétroliers, gaz, beurre, huile, sucre, farine, eau, électricité ; "
                                        "art. 144-I-D).",
        },
        "tableau": taux_is_par_exercice,
        "simulations": ["IS (impôt sur les sociétés)", "Mes impôts et déclarations (calendrier)"],
        "references": ["CGI, art. 2 à 20 (IS), 144 (cotisation minimale), 170 (acomptes et liquidation)"],
    },
    "TVA décortiquée": {
        "question": "taxe sur la valeur ajoutée taux article 99 déduction",
        "sections": [
            ("Qui est concerné", ["Les opérations de nature industrielle, commerciale, artisanale ou relevant de "
                                  "l'exercice d'une profession libérale, réalisées au Maroc (CGI, art. 87 et 89)."]),
            ("Principe", ["TVA à payer = TVA collectée sur les ventes − TVA déductible sur les achats et investissements "
                          "(art. 101) ; si le résultat est négatif, c'est un crédit de TVA reporté (art. 101-4°)."]),
            ("Régime de déclaration", ["Mensuel si le chiffre d'affaires de l'année précédente atteint 1 000 000 DH, "
                                       "trimestriel sinon et l'année du début d'activité (art. 108)."]),
            ("Délais", ["Déclaration et paiement avant la fin du mois suivant le mois ou le trimestre (art. 110 et 111), "
                        "par télédéclaration (art. 155)."]),
            ("Conditions de déduction", ["Facture conforme (ICE du fournisseur et du client), paiement justifié ; "
                                         "les paiements en espèces au-delà des seuils légaux ne sont pas déductibles "
                                         "(art. 106)."]),
            ("Sanctions", ["Retard : art. 184 et 208 ; facture fictive : sanctions pénales de l'art. 192."]),
        ],
        "secteurs": {
            "Banques et assurances": "Opérations de banque et de crédit : taux de 10 % (art. 99) ; assurances : hors "
                                     "champ, soumises à la taxe sur les contrats d'assurance.",
            "Hôtellerie et restauration": "Hébergement et restauration : taux de 10 % (art. 99).",
            "Services et professions libérales": "Taux normal de 20 % en principe ; certaines professions judiciaires "
                                                 "et juridiques à 10 % (art. 99) : vérifiez la vôtre.",
            "Export": "Exportations exonérées avec droit à déduction (art. 92) : demandez le remboursement du crédit "
                      "de TVA (art. 103).",
            "Agriculture": "Produits agricoles non transformés : exonérés sans droit à déduction (art. 91) ; matériel "
                           "agricole : régime particulier (art. 92).",
            "Commerce et distribution": "Produits de première nécessité exonérés (pain, lait, farine…, art. 91) ; petits "
                                        "commerçants sous le seuil légal : exonérés (art. 91-II).",
            "Immobilier et promotion immobilière": "Logement social : exonération sous conditions (art. 92) ; "
                                                   "livraison à soi-même de construction : art. 89-I.",
        },
        "tableau": taux_tva_par_exercice,
        "simulations": ["TVA due ou crédit de TVA", "Prix de vente et marges"],
        "references": ["CGI, art. 87 à 125 (TVA)", "Réforme des taux : lois de finances 2024 à 2026"],
    },
    "État 9421 (traitements et salaires)": {
        "question": "déclaration des traitements et salaires article 79",
        "sections": [
            ("Qui est concerné", ["Tout employeur (société, personne physique, association, administration) qui verse "
                                  "des salaires, pensions ou indemnités (CGI, art. 79)."]),
            ("Contenu", ["Pour chaque salarié : identité, CIN, numéro CNSS, période, salaire brut, avantages en nature, "
                         "indemnités (exonérées ou non), cotisations retenues, frais professionnels, revenu net "
                         "imposable, charges de famille, IR retenu ; totaux de l'entreprise."]),
            ("Délai", ["Avant le 1er mars de l'année suivante, par télédéclaration (art. 79 et 155) : le 28 ou "
                       "29 février au plus tard."]),
            ("Contrôle de cohérence", ["Le total de l'IR de l'état doit égaler la somme des 12 versements mensuels de "
                                       "retenue à la source : tout écart doit être régularisé avant le dépôt."]),
            ("Sanctions", ["Défaut, retard ou déclaration incomplète : amende de l'art. 200, après la procédure de "
                           "l'art. 230 ter (lettre de l'administration, 30 jours pour régulariser)."]),
        ],
        "secteurs": {},
        "tableau": None,
        "simulations": ["État 9421 (préparation)", "Bulletin de paie complet"],
        "references": ["CGI, art. 79 (déclaration des traitements et salaires), 156 et 174, 200 et 230 ter"],
    },
    "Déclaration du revenu global (personnes physiques)": {
        "question": "déclaration annuelle du revenu global article 82",
        "sections": [
            ("Qui doit déclarer", ["Les professionnels au réel ou au simplifié ; les titulaires de revenus fonciers ; "
                                   "les salariés ayant plusieurs employeurs, d'autres revenus ou des déductions non "
                                   "appliquées par l'employeur ; les titulaires de revenus agricoles imposables "
                                   "(CGI, art. 82)."]),
            ("Qui est dispensé", ["Salarié d'un seul employeur sans autre revenu ; revenus soumis à un prélèvement "
                                  "libératoire (dividendes, intérêts, loyers à l'option de 20 %) ; certains "
                                  "retraités (art. 86)."]),
            ("Délais", ["Avant le 1er mai : revenus professionnels au réel ou simplifié, même avec d'autres revenus "
                        "(une seule déclaration).", "Avant le 1er mars : salaires, revenus fonciers et revenus de "
                        "capitaux mobiliers, sans revenu professionnel.", "CPU : déclaration du chiffre d'affaires "
                        "avant le 1er avril (art. 82 quater).", "Profit immobilier : déclaration et paiement dans les "
                        "30 jours de la cession (art. 83 et 173)."]),
            ("Liquidation", ["IR du revenu global − retenues à la source et versements déjà faits = solde à payer, ou "
                             "excédent restitué d'office (art. 241 bis)."]),
            ("Comment", ["En ligne sur SIMPL-IR (site de la DGI), avec un état explicatif en cas de résultat nul ou "
                         "déficitaire ; un résultat nul répété expose à l'art. 198 bis."]),
        ],
        "secteurs": {},
        "tableau": taux_ir_par_exercice,
        "simulations": ["IR (impôt sur le revenu)", "Revenus fonciers (loyers)"],
        "references": ["CGI, art. 82, 82 quater, 83, 86, 173, 198 bis, 241 bis"],
    },
    "Revenus fonciers (loyers) décortiqués": {
        "question": "revenus fonciers loyers abattement article 64 retenue",
        "sections": [
            ("Qui est concerné", ["Le propriétaire personne physique qui loue un immeuble bâti ou non bâti (CGI, art. 61)."]),
            ("Base", ["Loyers bruts encaissés + charges payées par le locataire pour le propriétaire ; abattement de "
                      "40 % pour l'imposition au barème (art. 64-II)."]),
            ("Locataire personne morale ou professionnel", ["Il retient à la source 10 % (loyers bruts annuels < "
                                                            "120 000 DH) ou 15 % (≥ 120 000 DH) et la verse avant la "
                                                            "fin du mois suivant (art. 73-II, 160 bis, 174-IV) ; "
                                                            "dispense si les loyers versés au même propriétaire ne "
                                                            "dépassent pas 40 000 DH par an.",
                                                            "Depuis la LF 2023, cette retenue n'est plus libératoire : "
                                                            "elle s'impute sur l'IR au barème, l'excédent est restitué "
                                                            "(art. 73, 241 bis)."]),
            ("Option libératoire", ["Depuis la LF 2025 : prélèvement de 20 % sur le brut, libératoire (art. 64-IV et "
                                    "73-II-F-12°)."]),
            ("Déclaration", ["Revenu global avant le 1er mars de l'année suivante (avant le 1er mai si vous avez aussi "
                             "des revenus professionnels au réel ou simplifié) (art. 82-I)."]),
            ("Justificatifs", ["Contrats de bail enregistrés, quittances, relevés bancaires des loyers, attestations "
                               "de retenue délivrées par le locataire."]),
        ],
        "secteurs": {},
        "tableau": None,
        "simulations": ["Revenus fonciers (loyers)", "Rentabilité locative"],
        "references": ["CGI, art. 61 à 64, 73-II, 82, 160 bis, 174-IV, 241 bis ; Loi n° 67-12 (baux d'habitation)"],
    },
    "Documents et attestations de régularité": {
        "question": "attestation de régularité fiscale",
        "sections": [
            ("Attestations à demander", ["Attestation de régularité fiscale : en ligne sur SIMPL (DGI), délivrée si "
                                         "toutes les déclarations sont déposées et les impôts payés ; exigée pour les "
                                         "marchés publics, les aides, certains financements.",
                                         "Attestation de régularité de la CNSS (situation régulière) : sur Damancom.",
                                         "Attestation d'inscription à la taxe professionnelle, identifiant fiscal et "
                                         "ICE : SIMPL et portail de l'ICE.",
                                         "Extrait du registre de commerce (modèle J) : tribunal de commerce ou portail "
                                         "de l'OMPIC.", "Attestation de chiffre d'affaires et de dépôt de la liasse "
                                         "fiscale : SIMPL."]),
            ("Dossier permanent (à garder tant que l'entreprise existe)", [
                "Statuts et modifications, PV des assemblées, registre de commerce, identifiant fiscal, ICE, taxe "
                "professionnelle, affiliation CNSS, bail ou titre du local, contrats importants, polices d'assurance."]),
            ("Dossier annuel (un classeur ou dossier numérique par exercice)", [
                "1. Ventes : factures émises numérotées sans trou, avec ICE ; avoirs.",
                "2. Achats et frais : factures fournisseurs conformes, avec preuve de paiement (chèque, virement).",
                "3. Banque : relevés mensuels et rapprochements bancaires.",
                "4. TVA : déclarations, accusés de réception, quittances de paiement, par mois ou trimestre.",
                "5. Paie : contrats, bulletins, BDS et quittances CNSS, versements de l'IR, état 9421.",
                "6. IS ou IR : acomptes, liasse fiscale, déclaration du résultat, liquidation.",
                "7. Immobilisations : factures d'achat, plan d'amortissement, cessions.",
                "8. Courriers de l'administration et réponses, avec dates."]),
            ("Combien de temps garder", ["10 ans : documents comptables et pièces justificatives (CGI, art. 211 ; "
                                         "loi 9-88, art. 22). L'administration peut contrôler les 4 derniers "
                                         "exercices non prescrits (art. 232), davantage en cas de déficit reporté."]),
            ("Pour rester régulier", ["Déposer chaque déclaration même sans montant à payer ; payer à la date ; "
                                      "garder la preuve de chaque dépôt et paiement ; vérifier chaque trimestre sur "
                                      "SIMPL qu'aucune déclaration ne manque ; demander l'attestation de régularité "
                                      "avant d'en avoir besoin."]),
        ],
        "secteurs": {},
        "tableau": None,
        "simulations": ["Mes impôts et déclarations (calendrier)", "Feuille de route du débutant"],
        "references": ["CGI, art. 145 (tenue de la comptabilité et factures), 155 (télédéclaration), 211 "
                       "(conservation), 232 (prescription)", "Loi n° 9-88 relative aux obligations comptables",
                       "Dahir 1-72-184 (CNSS)"],
    },
}


def revenus_fonciers(loyers_bruts_annuels, autres_revenus_nets, annee, retenue_par_locataire=True, memoire=None):
    """Barème avec abattement de 40 % sur le revenu global (part due aux loyers), comparé à l'option libératoire de 20 %."""
    net_foncier = loyers_bruts_annuels * 0.60
    avec = B.ir_annee(autres_revenus_nets + net_foncier, annee, memoire)["ir_annuel"]
    sans = B.ir_annee(autres_revenus_nets, annee, memoire)["ir_annuel"] if autres_revenus_nets > 0 else 0.0
    ir_loyers = round(avec - sans, 2)
    taux_ras = 0.10 if loyers_bruts_annuels < 120_000 else 0.15
    dispense = loyers_bruts_annuels <= 40_000
    ras = 0.0 if not retenue_par_locataire or dispense else round(loyers_bruts_annuels * taux_ras, 2)
    option = round(loyers_bruts_annuels * 0.20, 2) if annee >= 2025 and retenue_par_locataire else None
    return {"net_foncier": round(net_foncier, 2), "ir_loyers": ir_loyers, "taux_ras": taux_ras, "ras": ras,
            "dispense": dispense, "solde": round(ir_loyers - ras, 2), "option_20": option,
            "meilleur": ("option libératoire de 20 %" if option is not None and option < ir_loyers else "barème")}


def etat_9421(lignes, annee, memoire=None):
    """lignes : [(nom, salaire brut annuel, cotisations CNSS et AMO annuelles, personnes à charge, IR retenu)].
    Recalcule le net imposable et l'IR de chaque salarié et signale les écarts avec l'IR retenu."""
    from . import connaissances as K
    sorties = []
    for nom, brut, cotis, pac, ir_retenu in lignes:
        taux_fp = next(t for plafond, t in K.FRAIS_PRO if brut <= plafond)
        frais = min(brut * taux_fp, K.PLAFOND_FRAIS_PRO_ANNUEL)
        net_imp = max(0.0, brut - cotis - frais)
        ir = B.ir_annee(net_imp, annee, memoire)["ir_annuel"]
        ir = max(0.0, ir - min(int(pac), 6) * 500)
        sorties.append({"Salarié": nom, "Brut annuel": round(brut, 2), "Cotisations": round(cotis, 2),
                        "Frais professionnels": round(frais, 2), "Net imposable": round(net_imp, 2),
                        "Personnes à charge": int(pac), "IR recalculé": round(ir, 2), "IR retenu": round(ir_retenu, 2),
                        "Écart": round(ir_retenu - ir, 2)})
    t = pd.DataFrame(sorties)
    return {"tableau": t, "total_brut": round(float(t["Brut annuel"].sum()), 2) if len(t) else 0.0,
            "total_ir": round(float(t["IR recalculé"].sum()), 2) if len(t) else 0.0,
            "ecarts": t[t["Écart"].abs() > 1]["Salarié"].tolist() if len(t) else []}
