"""
Code général des impôts, édition 2026 (DGI, à jour de la loi de finances n° 50-25 pour 2026) : structure et intitulé
des articles qu'IA AISSA cite, vérifiés dans le PDF officiel le 21/11/2026.

Source : https://www.finances.gov.ma/Publication/dgi/2025/CGI-2026-FR.pdf (765 pages ; copie identique sur tax.gov.ma
et tgr.gov.ma). Le code compte trois livres, mais la numérotation des articles est continue et inchangée : les
articles cités (19, 73, 99, 144, 247…) gardent leur numéro et leur objet. Deux articles cités autrefois sont abrogés :
l'article 98 (taux réduits de TVA, abrogé par la LF 2024 ; seul l'article 99 fixe désormais 20 % et 10 %) et
l'article 42 (l'auto-entrepreneur relève des articles 42 bis et 42 ter, pas de l'article 41, qui vise la CPU).

Un test vérifie que chaque article cité dans le code d'IA AISSA figure ici et n'est pas abrogé.
"""

SOURCE = "Code général des impôts, édition 2026 (DGI), finances.gov.ma/Publication/dgi/2025/CGI-2026-FR.pdf"
VERIFIE_LE = "21/11/2026"
LIVRES = [
    ("Livre premier", "Règles d'assiette et de recouvrement (IS, IR, TVA, droits d'enregistrement, timbre…)", 2, 209),
    ("Livre II", "Procédures fiscales (contrôle, contentieux, prescription, restitutions…)", 210, 248),
    ("Livre III", "Autres droits et taxes", 249, None),
]
ABROGES = {"42", "98"}
ARTICLES = {
    "2": "Personnes imposables (IS)", "10": "Charges déductibles", "13": "Produits des actions, parts sociales et "
    "revenus assimilés", "19": "Taux d'imposition (IS : 20 %, 35 %, 40 %…)", "20": "Déclaration du résultat fiscal "
    "et du chiffre d'affaires", "22": "Revenus et profits imposables (IR)", "23": "Territorialité",
    "28": "Déductions sur le revenu global imposable", "42 bis": "Auto-entrepreneur : détermination de la base "
    "imposable", "57": "Exonérations (revenus salariaux)", "59": "Déductions (frais professionnels, retraite…)",
    "61": "Définition des revenus et profits fonciers", "63": "Exonérations (profits fonciers)",
    "64": "Détermination du revenu foncier imposable", "65": "Détermination du profit foncier imposable",
    "73": "Taux de l'impôt (barème de l'IR, taux spécifiques, auto-entrepreneur)", "74": "Réduction pour charge de "
    "famille", "79": "Déclaration des traitements et salaires", "82": "Déclaration annuelle du revenu global",
    "82 bis": "Déclaration du chiffre d'affaires de l'auto-entrepreneur", "83": "Déclaration des profits fonciers",
    "86": "Dispense de la déclaration annuelle du revenu global", "87": "Définition (TVA)",
    "89": "Opérations obligatoirement imposables", "99": "Taux de la TVA (A : 20 % ; B : 10 %)",
    "101": "Droit à déduction : règle générale", "108": "Périodicité de la déclaration (TVA)",
    "110": "Déclaration mensuelle", "111": "Déclaration trimestrielle", "125": "Affectation du produit de la TVA "
    "et mesures transitoires", "133": "Droits proportionnels (enregistrement)", "144": "Cotisation minimale",
    "145": "Tenue de la comptabilité", "151": "Déclaration des rémunérations allouées à des tiers et des produits "
    "de location", "154 bis": "Déclaration des revenus fonciers versés à des personnes physiques (avant le 1er mars)", "155": "Télédéclaration", "157": "Retenue à la source sur les rémunérations allouées à des tiers et les produits de location", "156": "Retenue à la source sur les salaires et "
    "rentes viagères", "160": "Retenue à la source sur les produits bruts versés aux non-résidents",
    "160 bis": "Retenue à la source sur les revenus fonciers",
    "170": "Recouvrement par paiement spontané (IS)", "173": "Recouvrement par paiement spontané (IR)",
    "174": "Recouvrement par voie de retenue à la source", "184": "Sanctions pour défaut ou retard de déclaration",
    "208": "Sanctions pour paiement tardif", "211": "Conservation des documents comptables",
    "236": "Dégrèvements, remises et modérations", "241": "Restitution en matière de droits d'enregistrement",
    "241 bis": "Restitution en matière d'impôt sur le revenu", "247": "Dates d'effet et dispositions transitoires",
}


def livre_de(numero):
    """Le livre du CGI 2026 où se trouve l'article (« 99 », « 42 bis »…)."""
    n = int(str(numero).split()[0])
    return next((nom for nom, _, debut, fin in LIVRES if n >= debut and (fin is None or n <= fin)), None)


def article(numero):
    """« Article 99 du CGI (édition 2026, livre premier) : Taux de la TVA (A : 20 % ; B : 10 %). » ou None."""
    numero = str(numero).strip()
    if numero in ABROGES:
        return f"L'article {numero} du CGI est abrogé dans l'édition 2026 (vérifié le {VERIFIE_LE})."
    titre = ARTICLES.get(numero)
    if titre is None:
        return None
    return f"Article {numero} du CGI (édition 2026, {livre_de(numero).lower()}) : {titre}."
