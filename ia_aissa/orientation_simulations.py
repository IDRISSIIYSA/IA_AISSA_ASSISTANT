"""
Orienter une question de la vie courante vers la bonne simulation (« je vends mon appartement », « SARL ou
auto-entrepreneur ? », « combien je touche si je démissionne ? »), en français et en darija.

Chaque piste est une expression reconnue → une simulation de la liste (espace_simulations.CATEGORIES) et la raison
en une phrase. Une question qui demande une explication de loi (« mon patron veut me licencier ») n'est pas détournée :
seules les questions de montant ou de choix mènent à une simulation.
"""

import re

PISTES = [
    (r"(sarl|soci[ée]t[ée]|charika).{0,40}\b(ou|wla|wela|vs|contre)\b.{0,40}(auto[- ]?entrepreneur|personne physique)"
     r"|(auto[- ]?entrepreneur|personne physique).{0,40}\b(ou|wla|wela|vs|contre)\b.{0,40}(sarl|soci[ée]t[ée]|charika)"
     r"|compar\w*.{0,30}(sarl|soci[ée]t[ée]|auto[- ]?entrepreneur).{0,30}\bet\b.{0,30}(sarl|soci[ée]t[ée]|"
     r"auto[- ]?entrepreneur|personne physique)"
     r"|quel statut (choisir|juridique)|(chno|ach) (ndir|nkhtar).{0,20}(sarl|statut|charika)",
     "Choisir son statut (comparaison)",
     "elle compare, pour la même activité, l'impôt, les cotisations et ce qu'il vous reste selon chaque statut"),
    (r"(vente|vendre|vends|nbi3|bi3t|cession|c[ée]der).{0,40}(appartement|maison|\bdar\b|terrain|\bard\b|"
     r"bien immobilier|immeuble|villa|lbo9|lmanzil)|plus[- ]value immobili|profit foncier",
     "Plus-value immobilière (profit foncier)",
     "elle calcule l'impôt sur la vente (20 % du profit ou 3 % du prix), avec le coefficient de réévaluation officiel"),
    (r"solde de tout compte|(quitt|d[ée]mission|nkhrej|khrejt|nkhli).{0,40}(travail|boulot|khdma|entreprise|"
     r"charika).{0,60}(combien|touche|chhal|indemnit|nakhod)|(combien|chhal).{0,40}(touche|nakhod).{0,40}"
     r"(quitt|d[ée]mission|d[ée]part)",
     "Solde de tout compte",
     "elle additionne le dernier salaire, les congés non pris, le préavis et les indemnités dues au départ"),
    (r"indemnit[ée] de licenciement|(licenci|tredouni|jrani|ytredni).{0,60}(combien|chhal|calcul|montant)",
     "Indemnité de licenciement",
     "elle calcule l'indemnité selon l'ancienneté et le salaire (Code du travail, art. 52 à 53)"),
    (r"rembours\w* anticip|(rembourser|solder|nkhles|nsedd).{0,30}(cr[ée]dit|kredi|pr[êe]t).{0,30}(avant|t[ôo]t|"
     r"kamel|bekri|d.un coup)",
     "Remboursement anticipé d'un crédit",
     "elle chiffre ce que vous économisez en intérêts et l'indemnité de remboursement anticipé"),
    (r"business plan|plan d.affaires|[ée]tude de (projet|faisabilit[ée])|bghit (ndir|nbda|n7el) (machrou3|projet)|"
     r"lancer (un|mon) projet",
     "Business plan sur 5 ans",
     "il projette chiffre d'affaires, charges, résultat et trésorerie sur 5 ans, avec le seuil de rentabilité"),
    (r"(combien|chhal).{0,30}(emprunter|nsellef|kredi|cr[ée]dit).{0,40}(salaire|gagne|revenu|chahriya)|"
     r"(salaire|revenu|chahriya|gagne).{0,40}(combien|chhal).{0,30}(emprunter|nsellef|kredi|cr[ée]dit)|"
     r"capacit[ée] d.emprunt",
     "Capacité d'emprunt",
     "elle calcule le montant que la banque peut vous prêter d'après vos revenus et vos charges"),
    (r"acheter ou louer|louer ou acheter|nchri wla nkri|nkri wla nchri",
     "Acheter ou louer",
     "elle compare sur la durée le coût d'un achat à crédit et celui d'une location"),
    (r"leasing ou cr[ée]dit|cr[ée]dit ou leasing",
     "Leasing ou crédit",
     "elle compare le coût total d'un leasing et d'un crédit pour le même bien"),
    (r"(je ne sais rien|d[ée]butant|je d[ée]bute|par o[ùu] commencer|ma 3reft walou).{0,60}(imp[ôo]t|fiscal|"
     r"entreprise|soci[ée]t[ée]|d[ée]clar|charika)",
     "Feuille de route du débutant",
     "elle vous guide pas à pas : immatriculation, obligations, déclarations, dans l'ordre"),
]
_COMPILEES = [(re.compile(m, re.I), nom, raison) for m, nom, raison in PISTES]


def orienter(texte):
    """(nom de la simulation, raison) ou None."""
    for motif, nom, raison in _COMPILEES:
        if motif.search(texte or ""):
            return nom, raison
    return None


def reponse_orientation(texte):
    """(réponse, étapes) pour la pensée propre, ou None."""
    trouve = orienter(texte)
    if not trouve:
        return None
    nom, raison = trouve
    from .espace_simulations import categorie_de
    return (f"Pour cela, la bonne simulation est **« {nom} »** ({categorie_de(nom)}) : {raison}. "
            "Ouvre-la avec le bouton ci-dessous (ou **🧮 Simulations et guides**, puis la liste) : tu auras le calcul "
            "détaillé, les textes de loi et un rapport PDF.",
            [f"Ta question décrit une situation que je sais simuler : « {nom} »."])
