"""
Lire la loi de finances de l'année (PDF déposé par l'administrateur) et proposer les nouveaux taux et seuils trouvés.

IA AISSA ne change rien seule : chaque proposition (paramètre, valeur, article, extrait du texte) attend la validation
de l'administrateur, qui l'applique alors par le registre des taux (parametres.mettre_a_jour, texte légal et source
remplis d'après la loi). Seuls les paramètres qu'une loi de finances fixe sont cherchés (frais professionnels,
cotisation minimale, seuil de TVA mensuelle, profit foncier, indemnité de transport) ; le SMIG et les taux CNSS
relèvent de décrets.

Méthode : le texte est découpé en phrases ; une phrase qui parle d'un paramètre (mots-clés) et contient un nombre de la
bonne unité (« % » pour un taux, « dirhams » pour un montant, y compris la forme « trois mille (3 000) dirhams ») donne
une proposition, si la valeur diffère de la valeur en vigueur. L'article est le dernier « Article … » qui précède.
"""

import io
import json
import re
from datetime import datetime, timezone

CLE_REGLAGE = "propositions_loi"
MOTIFS = {
    "plafond_frais_pro": r"frais professionnels",
    "taux_cotisation_minimale": r"cotisation minimale",
    "minimum_cotisation_minimale": r"cotisation minimale",
    "seuil_tva_mensuelle": r"déclaration mensuelle|chiffre d.affaires.{0,80}mensuel",
    "seuil_petites_cessions": r"(cession|profit foncier).{0,160}(n.excède pas|inférieure? ou égale?|n.excédant pas)",
    "plafond_residence_principale": r"habitation principale|résidence principale",
    "transport_exonere": r"indemnités? de (transport|déplacement)",
}
# Valeurs plausibles de chaque paramètre : écarte les montants d'exemples (chiffres d'affaires, bénéfices…)
BORNES = {
    "plafond_frais_pro": (10_000, 200_000), "taux_cotisation_minimale": (0.001, 0.06),
    "minimum_cotisation_minimale": (500, 50_000), "seuil_tva_mensuelle": (100_000, 20_000_000),
    "seuil_petites_cessions": (50_000, 2_000_000), "plafond_residence_principale": (1_000_000, 50_000_000),
    "transport_exonere": (100, 5_000),
}
# Une règle se dit « fixé à », « porté à », « plafonné », « ne peut être inférieur », « n'excède pas »…
REGLE = re.compile(r"(fix|port[ée]|plafonn|limit|inf[ée]rieur|exc[èé]d|relev|ramen|minimum|seuil|taux de)", re.I)
CALCUL = re.compile(r"(=|…|\.{4,}|\bexemple\b|\bsoit\b\s*:|\d\s*[x×]\s*\d)", re.I)
_MONTANT = re.compile(r"\(?\b(\d{1,3}(?:[ .  ]\d{3})+|\d+)(?:,(\d+))?\)?\s*(?:de\s+)?(?:dirhams|DH)\b", re.I)
_TAUX = re.compile(r"\b(\d{1,2}(?:,\d{1,2})?)\s*%")
_ARTICLE = re.compile(r"\bArticle\s+(\d+[\w-]*(?:\s+(?:bis|ter|quater))?)", re.I)


def texte_du_pdf(octets):
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(octets)).pages)


_ANCIENNE = re.compile(r"\bde\s+(?:[\w-]+\s+){0,4}\(?\d[\d  .,]*\)?\s*(?:%|dirhams|DH)(?:\s+susvis[ée]e?s?)?(?=\s+à\s)", re.I)


def sans_ancienne_valeur(phrase):
    """« porté de 0,50 % à 0,25 % » : seule la nouvelle valeur (après « à ») est une proposition."""
    return _ANCIENNE.sub(" ", phrase)


def _montants(phrase):
    valeurs = []
    for entier, decimales, in ((m.group(1), m.group(2)) for m in _MONTANT.finditer(phrase)):
        v = float(re.sub(r"[ .  ]", "", entier) + (f".{decimales}" if decimales else ""))
        valeurs.append(v)
    return valeurs


def _taux(phrase):
    return [float(t.replace(",", ".")) / 100 for t in _TAUX.findall(phrase)]


def propositions(texte, valeurs_actuelles):
    """Les propositions trouvées : [{cle, valeur, actuelle, article, extrait}], une par (paramètre, valeur)."""
    from .parametres import PAR_CLE
    texte = re.sub(r"[ \t]+", " ", texte)
    articles = [(m.start(), m.group(1)) for m in _ARTICLE.finditer(texte)]
    trouvees, vues = [], set()
    debut = 0
    for phrase in re.split(r"(?<=[.;:])\s+", texte):
        position = texte.find(phrase, debut)
        debut = max(debut, position)
        article = next((a for p, a in reversed(articles) if p <= position), None)
        if CALCUL.search(phrase) or not REGLE.search(phrase):
            continue                                       # un exemple chiffré n'est pas une règle
        for cle, motif in MOTIFS.items():
            if not re.search(motif, phrase, re.I):
                continue
            unite = PAR_CLE[cle][4]
            utile = sans_ancienne_valeur(phrase)
            candidats = _taux(utile) if unite == "taux" else _montants(utile)
            for v in candidats:
                bas, haut = BORNES.get(cle, (0, float("inf")))
                if not bas <= v <= haut or (cle, v) in vues or abs(v - float(valeurs_actuelles.get(cle, -1))) < 1e-9:
                    continue
                vues.add((cle, v))
                trouvees.append({"cle": cle, "valeur": v, "actuelle": valeurs_actuelles.get(cle),
                                 "article": article, "extrait": phrase.strip()[:400]})
    return trouvees


def analyser(memoire, octets, nom_fichier, annee):
    """Lit le PDF, garde les propositions (en attente de validation) et les renvoie."""
    from . import parametres as P
    actuelles = {cle: getattr(module, attribut) for cle, module, attribut, *_ in P.PARAMETRES}
    trouvees = propositions(texte_du_pdf(octets), actuelles)
    for t in trouvees:
        t.update(fichier=nom_fichier, annee=int(annee), statut="à valider",
                 lu_le=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"))
    memoire.definir_reglage(CLE_REGLAGE, json.dumps(en_attente(memoire) + trouvees, ensure_ascii=False))
    return trouvees


def en_attente(memoire):
    brut = memoire.reglage(CLE_REGLAGE)
    return [p for p in (json.loads(brut) if brut else []) if p["statut"] == "à valider"]


def decider(memoire, index, valider, auteur="administrateur"):
    """Valide (applique par le registre des taux, avec la loi comme texte légal) ou rejette une proposition."""
    from . import parametres as P
    attente = en_attente(memoire)
    p = attente.pop(index)
    if valider:
        P.mettre_a_jour(memoire, p["cle"], p["valeur"], f"01/01/{p['annee']}",
                        f"Loi de finances {p['annee']}" + (f", article {p['article']}" if p["article"] else ""),
                        f"{p['fichier']} (déposé et lu le {p['lu_le']}), validé par l'{auteur}", auteur=auteur)
    memoire.definir_reglage(CLE_REGLAGE, json.dumps(attente, ensure_ascii=False))
    return p
