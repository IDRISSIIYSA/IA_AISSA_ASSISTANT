"""
Taux d'IS et de TVA exercice par exercice (2022 à 2026), recopiés des notes circulaires de la DGI (lues le 04/11/2026) :

- IS : note circulaire n° 733 relative à la loi de finances 2023, partie « Convergence progressive des taux d'IS
  vers les taux cibles » (article 247-XXXVII-A du CGI ; taux cibles : article 19-I). Depuis 2023, ce sont des taux
  proportionnels : le taux qui correspond au bénéfice net fiscal s'applique à TOUT le bénéfice (plus de barème
  progressif par tranches).
- TVA : note circulaire n° 735 relative à la loi de finances 2024, tableau « Produits ou opérations / taux avant et
  après la réforme » (articles 99 et 247-XXXXI-D du CGI) et exonérations généralisées (article 91).

Rien n'est inventé : un exercice ou un produit absent renvoie None. Les cas particuliers (sociétés conventionnées à
1,5 milliard de DH, sortie du taux de 35 % après trois exercices, période de consommation à cheval sur deux taux de
TVA…) sont signalés dans la réponse, pas calculés.
"""

SOURCE_IS = "DGI, note circulaire n° 733 (loi de finances 2023), art. 247-XXXVII-A et 19-I du CGI"
SOURCE_TVA = "DGI, note circulaire n° 735 (loi de finances 2024), art. 99, 91 et 247-XXXXI-D du CGI"
EXERCICES = (2022, 2023, 2024, 2025, 2026)
SEUIL_PETIT, SEUIL_MOYEN, SEUIL_GRAND = 300_000, 1_000_000, 100_000_000

# Taux d'IS par exercice (exercice ouvert à compter du 1er janvier de l'année), selon l'ancien taux de départ
_PETIT = {2022: .10, 2023: .125, 2024: .15, 2025: .175, 2026: .20}            # bénéfice ≤ 300 000 DH
_MOYEN = {a: .20 for a in EXERCICES}                                          # 300 001 à 1 000 000 DH
_31_BAS = {2022: .31, 2023: .2825, 2024: .255, 2025: .2275, 2026: .20}        # > 1 MDH et < 100 MDH
_31_HAUT = {2022: .31, 2023: .32, 2024: .33, 2025: .34, 2026: .35}            # ≥ 100 MDH
_INDUSTRIEL = {2022: .26, 2023: .245, 2024: .23, 2025: .215, 2026: .20}       # industriels, > 1 MDH et < 100 MDH
_ZAI_CFC = {2022: .15, 2023: .1625, 2024: .175, 2025: .1875, 2026: .20}        # zones d'accélération industrielle, CFC
_PLAFONNE_HAUT = {2022: .20, 2023: .2375, 2024: .275, 2025: .3125, 2026: .35}  # taux plafonné 20 %, ≥ 100 MDH
_CREDIT = {2022: .37, 2023: .3775, 2024: .385, 2025: .3925, 2026: .40}        # banques, BAM, CDG, assurances

CATEGORIES_IS = {
    "droit commun": "Sociétés de droit commun",
    "industriel": "Sociétés industrielles",
    "plafonné": "Taux plafonné de 20 % (exportatrices, hôtelières, minières, artisanales, enseignement privé, "
                "sportives, promoteurs immobiliers conventionnés, exploitations agricoles, externalisation de services)",
    "zai/cfc": "Zones d'accélération industrielle et statut Casablanca Finance City",
    "crédit/assurance": "Établissements de crédit, Bank Al-Maghrib, CDG, entreprises d'assurances et de réassurance",
}


def taux_is(benefice, exercice, categorie="droit commun"):
    """Taux d'IS (proportionnel) d'un exercice ouvert en `exercice`, pour un bénéfice net fiscal et une catégorie.
    Renvoie {"taux", "is", "regle", "source"} ou None si l'exercice n'est pas couvert (avant 2022, après 2026 :
    voir le CGI de l'année)."""
    if exercice not in EXERCICES or categorie not in CATEGORIES_IS:
        return None
    b = max(0.0, float(benefice))
    if categorie == "crédit/assurance":
        taux, regle = _CREDIT[exercice], "taux des établissements de crédit et des assurances"
    elif categorie == "zai/cfc":
        taux, regle = _ZAI_CFC[exercice], "taux spécifique ZAI / CFC (le taux de 35 % ne s'applique pas)"
    elif b >= SEUIL_GRAND:
        taux = (_PLAFONNE_HAUT if categorie == "plafonné" else _31_HAUT)[exercice]
        regle = "bénéfice ≥ 100 MDH"
    elif b > SEUIL_MOYEN:
        if categorie == "plafonné":
            taux, regle = .20, "taux plafonné de 20 % maintenu (bénéfice > 1 MDH et < 100 MDH)"
        elif categorie == "industriel":
            taux, regle = _INDUSTRIEL[exercice], "activité industrielle, bénéfice > 1 MDH et < 100 MDH"
        else:
            taux, regle = _31_BAS[exercice], "bénéfice > 1 MDH et < 100 MDH"
    elif b > SEUIL_PETIT:
        taux, regle = _MOYEN[exercice], "bénéfice de 300 001 à 1 000 000 DH"
    else:
        taux, regle = _PETIT[exercice], "bénéfice ≤ 300 000 DH"
    if exercice == 2022:
        regle += " (2022 : ancien barème, présenté ici en taux unique)"
    return {"taux": taux, "is": round(b * taux, 2), "regle": regle, "source": SOURCE_IS}


# TVA : produits dont le taux a changé avec la loi de finances 2024 (taux en vigueur au 1er janvier de l'année)
TVA_PAR_EXERCICE = {
    "énergie électrique": {2023: .14, 2024: .16, 2025: .18, 2026: .20},
    "électricité d'origine renouvelable (vente par les producteurs)": {2023: .14, 2024: .12, 2025: .10, 2026: .10},
    "location du compteur d'électricité": {2023: .07, 2024: .11, 2025: .15, 2026: .20},
    "transport urbain et transport routier de voyageurs et de marchandises": {2023: .14, 2024: .13, 2025: .12,
                                                                               2026: .10},
    "autres transports de voyageurs et de marchandises (hors ferroviaire)": {2023: .14, 2024: .16, 2025: .18,
                                                                             2026: .20},
    "eau des réseaux de distribution publique (usage autre que domestique), assainissement, location du compteur":
        {2023: .07, 2024: .10, 2025: .10, 2026: .10},
    "eau à usage domestique, assainissement et compteur d'eau du même usage": {2023: .07, 2024: 0.0, 2025: 0.0,
                                                                               2026: 0.0},
    "sucre raffiné ou aggloméré": {2023: .07, 2024: .08, 2025: .09, 2026: .10},
    "voiture économique (et ses intrants, montage)": {2023: .07, 2024: .10, 2025: .10, 2026: .10},
    "services des agents et courtiers d'assurances": {2023: .14, 2024: .12, 2025: .10, 2026: .10},
}
EXONERES_DEPUIS_2024 = ["produits pharmaceutiques", "fournitures scolaires (et leurs intrants)",
                        "eau à usage domestique (taux 0 % avec droit à déduction)",
                        "beurre dérivé du lait d'origine animale", "conserves de sardines", "lait en poudre",
                        "savon de ménage"]
MOTS_PRODUITS = {                       # mots d'une question → produit du tableau
    "renouvelable": "électricité d'origine renouvelable (vente par les producteurs)",
    "solaire": "électricité d'origine renouvelable (vente par les producteurs)",
    "compteur d'électricité": "location du compteur d'électricité",
    "compteur électrique": "location du compteur d'électricité",
    "électricité": "énergie électrique", "electricite": "énergie électrique", "kahraba": "énergie électrique",
    "transport urbain": "transport urbain et transport routier de voyageurs et de marchandises",
    "transport routier": "transport urbain et transport routier de voyageurs et de marchandises",
    "taxi": "transport urbain et transport routier de voyageurs et de marchandises",
    "autocar": "transport urbain et transport routier de voyageurs et de marchandises",
    "transport aérien": "autres transports de voyageurs et de marchandises (hors ferroviaire)",
    "transport maritime": "autres transports de voyageurs et de marchandises (hors ferroviaire)",
    "eau domestique": "eau à usage domestique, assainissement et compteur d'eau du même usage",
    "eau potable": "eau à usage domestique, assainissement et compteur d'eau du même usage",
    "sucre": "sucre raffiné ou aggloméré", "voiture économique": "voiture économique (et ses intrants, montage)",
    "courtier": "services des agents et courtiers d'assurances",
    "courtage": "services des agents et courtiers d'assurances",
}


def taux_tva(produit, exercice):
    """Taux de TVA d'un produit du tableau de la réforme pour une année, ou None (produit hors réforme : voir les
    taux de droit commun, 20 % ou 10 %, et les exonérations)."""
    taux = TVA_PAR_EXERCICE.get(produit, {})
    if exercice in taux:
        return taux[exercice]
    if taux and exercice > max(taux):
        return taux[max(taux)]                      # réforme achevée en 2026 : le dernier taux reste en vigueur
    return None


def produit_dans(texte):
    t = texte.lower()
    return next((p for mot, p in sorted(MOTS_PRODUITS.items(), key=lambda e: -len(e[0])) if mot in t), None)


def pct(t):
    """0.2825 → « 28,25 % » ; 0.2 → « 20 % »."""
    return f"{t * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " %"


def fiche_is_par_exercice():
    """Tableau Markdown des taux transitoires d'IS (lignes : situation ; colonnes : exercices)."""
    lignes = [("Bénéfice ≤ 300 000 DH", _PETIT), ("300 001 à 1 000 000 DH", _MOYEN),
              ("> 1 MDH et < 100 MDH (droit commun)", _31_BAS), ("> 1 MDH et < 100 MDH (industriel)", _INDUSTRIEL),
              ("≥ 100 MDH (droit commun et industriel)", _31_HAUT), ("≥ 100 MDH (anciennement plafonné à 20 %)",
                                                                      _PLAFONNE_HAUT),
              ("ZAI et Casablanca Finance City", _ZAI_CFC), ("Banques, BAM, CDG, assurances", _CREDIT)]
    entete = "| Situation | " + " | ".join(str(a) for a in EXERCICES) + " |\n|---|" + "---|" * len(EXERCICES) + "\n"
    corps = "\n".join(f"| {nom} | " + " | ".join(pct(t[a]) for a in EXERCICES) + " |" for nom, t in lignes)
    return entete + corps


def fiche_tva_par_exercice():
    annees = (2023, 2024, 2025, 2026)
    entete = "| Produit ou opération | " + " | ".join(str(a) for a in annees) + " |\n|---|" + "---|" * len(annees) + "\n"
    corps = "\n".join(f"| {p} | " + " | ".join(pct(t[a]) for a in annees) + " |"
                      for p, t in TVA_PAR_EXERCICE.items())
    return entete + corps + "\n\nExonérés depuis le 1er janvier 2024 : " + ", ".join(EXONERES_DEPUIS_2024) + "."


# ==========================================
# Réponse de la pensée propre quand une question nomme un exercice (« taux IS 2024 », « TVA électricité 2025 »)
# ==========================================
import re as _re

ANNEE = _re.compile(r"(?<![\d.,])(202[2-6])(?![\d.,])(?!\s*(dh|dhs|dirhams?|mad)\b)")   # « 2026 dh » : un montant
CONTEXTE_IS = _re.compile(r"(impôt sur les sociétés|impot sur les societes|\bis\b|dariba\b.*\b(charika|chrika|rb7)|"
                          r"\b(rb7|arba7)\b.*\bcharika\b)")
CONTEXTE_FISCAL = _re.compile(r"(taux|bénéfice|benefice|société|societe|dh\b|dirhams?|exercice|impôt|impot|combien|"
                              r"calcul|chhal|ch7al|dariba|banque|assurance|industri|export|hôtel|hotel|\bcfc\b|"
                              r"\bzai\b|électricité|electricite|transport|eau|sucre)")


def exercice_dans(texte):
    from .langues import detecter_langue
    t = texte.lower()
    francais = _re.search(r"(impôt|impot|taux|bénéfice|benefice|banque|assurance|société|societe|\bdh\b|dirham|"
                          r"industri|\btva\b|exercice|dariba|charika|\bcfc\b|\bzai\b|export|hôtel|hotel)", t)
    if detecter_langue(texte) == "English" and not francais:   # « what is … in 2024 » : « is » anglais, pas l'impôt
        return None
    m = ANNEE.search(t)
    if not m or not ((_re.search(r"\btva\b", t) or CONTEXTE_IS.search(t)) and CONTEXTE_FISCAL.search(t)):
        return None
    return int(m.group(1))


def categorie_dans(texte):
    t = texte.lower()
    if _re.search(r"(banque|bancaire|établissement de crédit|assurance|bank al-maghrib|\bcdg\b)", t):
        return "crédit/assurance"
    if _re.search(r"(\bcfc\b|casablanca finance city|\bzai\b|zone d'accélération|zone franche)", t):
        return "zai/cfc"
    if _re.search(r"(export|hôtel|hotel|minière|miniere|artisan|enseignement privé|sportive|agricole|externalisation)",
                  t):
        return "plafonné"
    if _re.search(r"(industri|usine)", t):
        return "industriel"
    return "droit commun"


def repondre_par_exercice(texte, valeurs, exercice):
    """(réponse, étapes) pour une question d'IS ou de TVA qui nomme un exercice ; None si elle n'en relève pas.
    `valeurs` : les montants de la question, année retirée."""
    from .connaissances import calculer_tva
    t = texte.lower()
    dh = lambda v: f"{v:,.0f}".replace(",", " ") + " DH"
    if _re.search(r"\btva\b", t):
        produit = produit_dans(t)
        if produit is None:
            return None                       # produit hors réforme : taux de droit commun, géré ailleurs
        taux = taux_tva(produit, exercice)
        if taux is None:
            return None
        evolution = " → ".join(f"{a} : {pct(v)}" for a, v in TVA_PAR_EXERCICE[produit].items())
        if valeurs:
            v = max(valeurs)
            r = calculer_tva(v, taux, "ttc" in t)
            debut = (f"TVA **{pct(taux)}** en {exercice} sur « {produit} » : montant **{dh(v)}** "
                     f"{'TTC' if 'ttc' in t else 'HT'} → HT {dh(r['ht'])}, TVA {dh(r['tva'])}, **TTC {dh(r['ttc'])}**.")
        else:
            debut = f"Taux de TVA en {exercice} sur « {produit} » : **{pct(taux)}**."
        return (debut + f"\n\nÉvolution prévue par la loi de finances 2024 : {evolution}. "
                f"Pour une consommation à cheval sur deux années, chaque partie prend le taux de sa période. "
                f"_Source : {SOURCE_TVA}._",
                [f"Exercice trouvé : {exercice} ; produit reconnu : {produit}.",
                 "Taux lu dans le tableau de la réforme de la TVA (taux en vigueur au 1er janvier)."])
    if CONTEXTE_IS.search(t):
        categorie = categorie_dans(t)
        if _re.search(r"(chiffre d['’ ]?\s*affaires|\bca\b|produits|ventes|recettes|cotisation minimale)", t):
            return None                       # IS dû avec cotisation minimale : calcul détaillé ailleurs
        if valeurs:
            b = max(valeurs)
            r = taux_is(b, exercice, categorie)
            if r is None:
                return None
            return (f"Exercice {exercice}, {CATEGORIES_IS[categorie].split(' (')[0].lower()} : bénéfice net fiscal "
                    f"**{dh(b)}** ({r['regle']}) → taux **{pct(r['taux'])}** sur tout le bénéfice → **IS {dh(r['is'])}**."
                    f"\n\nÀ comparer à la cotisation minimale (0,25 % des produits, au moins 3 000 DH) : le plus élevé "
                    f"est dû. _Source : {r['source']}._",
                    [f"Exercice trouvé : {exercice} ; catégorie : {categorie}.",
                     "Taux transitoire de l'exercice (taux proportionnel, appliqué à tout le bénéfice)."])
        lignes = [("bénéfice ≤ 300 000 DH", taux_is(1, exercice, categorie)),
                  ("300 001 à 1 000 000 DH", taux_is(500_000, exercice, categorie)),
                  ("> 1 MDH et < 100 MDH", taux_is(10_000_000, exercice, categorie)),
                  ("≥ 100 MDH", taux_is(200_000_000, exercice, categorie))]
        if categorie in ("zai/cfc", "crédit/assurance"):
            lignes = [("taux unique", lignes[0][1])]
        detail = " ; ".join(f"{nom} : **{pct(r['taux'])}**" for nom, r in lignes if r)
        return (f"Taux d'IS de l'exercice {exercice} ({CATEGORIES_IS[categorie].split(' (')[0].lower()}) : {detail}. "
                f"Le taux s'applique à tout le bénéfice. _Source : {SOURCE_IS}._",
                [f"Exercice trouvé : {exercice} ; catégorie : {categorie}.", "Taux transitoires 2023-2026 de l'IS."])
    return None
