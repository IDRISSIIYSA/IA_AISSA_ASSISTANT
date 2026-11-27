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


# ==========================================
# PDF scanné (images sans texte) : reconnaissance de caractères avec Tesseract, si le serveur l'a
# (Streamlit Cloud : paquets tesseract-ocr et tesseract-ocr-fra dans packages.txt). Sans lui : lien vers un OCR en ligne.
# ==========================================
MAX_PAGES_OCR = 60               # une loi de finances scannée : au-delà, trop long pour le petit serveur
CARACTERES_PAR_PAGE = 50         # moins de texte que cela par page : PDF scanné
OCR_EN_LIGNE = "https://iwelah.com/fr/ocr-pdf/"


class PdfScanne(ValueError):
    """PDF fait d'images et pas d'OCR sur le serveur."""


def ocr_disponible():
    import shutil
    return shutil.which("tesseract") is not None


def ocr_pdf(octets, max_pages=MAX_PAGES_OCR):
    """Texte des images de chaque page (Tesseract, français). Renvoie (texte, pages lues, pages du PDF)."""
    import subprocess
    import tempfile
    from pypdf import PdfReader
    pages = PdfReader(io.BytesIO(octets)).pages
    morceaux = []
    with tempfile.TemporaryDirectory() as dossier:
        for n, page in enumerate(pages[:max_pages]):
            for k, image in enumerate(page.images):
                chemin = f"{dossier}/p{n}_{k}{image.name[image.name.rfind('.'):] if '.' in image.name else '.png'}"
                with open(chemin, "wb") as f:
                    f.write(image.data)
                lu = subprocess.run(["tesseract", chemin, "-", "-l", "fra", "--psm", "6"], capture_output=True,
                                    text=True, timeout=120)
                morceaux.append(lu.stdout)
    return "\n".join(morceaux), min(len(pages), max_pages), len(pages)


def lire_pdf(octets):
    """{texte, ocr (bool), pages_lues, pages} : le texte du PDF, ou celui de ses images s'il est scanné.
    Lève PdfScanne si le PDF est scanné et que le serveur n'a pas d'OCR."""
    from pypdf import PdfReader
    texte = texte_du_pdf(octets)
    pages = len(PdfReader(io.BytesIO(octets)).pages)
    if len(texte.strip()) >= CARACTERES_PAR_PAGE * max(pages, 1):
        return {"texte": texte, "ocr": False, "pages_lues": pages, "pages": pages}
    if not ocr_disponible():
        raise PdfScanne(f"Ce PDF est une image scannée ({pages} page(s)) et la reconnaissance de caractères n'est pas "
                        f"installée sur ce serveur : passez-le d'abord à un OCR (par exemple {OCR_EN_LIGNE}) puis "
                        "déposez le PDF obtenu.")
    texte, lues, total = ocr_pdf(octets)
    return {"texte": texte, "ocr": True, "pages_lues": lues, "pages": total}


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


# Barème de l'IR (CGI, art. 73-I), tel que la loi de finances le rédige : « la tranche du revenu allant jusqu'à
# 40 000 dirhams est exonérée ; 10% pour la tranche du revenu allant de 40.001 à 60.000 dirhams ; … ; 37% pour le surplus »
_NOMBRE_LOI = r"(\d{1,3}(?:[ .  ]\d{3})+|\d+)"
_EXONEREE = re.compile(r"tranche du revenu allant jusqu.{1,3}" + _NOMBRE_LOI + r"\s*dirhams est exon", re.I)
_TRANCHE = re.compile(r"(\d{1,2}(?:,\d{1,2})?)\s*%\s*pour la tranche du revenu allant de\s*" + _NOMBRE_LOI
                      + r"\s*(?:dirhams\s*)?(?:à|a)\s*" + _NOMBRE_LOI + r"\s*dirhams", re.I)
_SURPLUS = re.compile(r"(\d{1,2}(?:,\d{1,2})?)\s*%\s*pour le surplus", re.I)


def _entier(texte):
    return float(re.sub(r"[ .  ]", "", texte))


def bareme_ir(texte):
    """Le barème de l'IR trouvé dans le texte : [(plafond ou None, taux, somme à déduire)] avec l'extrait, ou None.
    La somme à déduire est recalculée tranche par tranche (D = D précédente + écart de taux × plafond précédent)."""
    texte = re.sub(r"\s+", " ", texte or "")
    exo = _EXONEREE.search(texte)
    surplus = _SURPLUS.search(texte, exo.end()) if exo else None
    if not exo or not surplus:
        return None
    morceau = texte[exo.start():surplus.end()]
    tranches = [(_entier(exo.group(1)), 0.0)]
    for m in _TRANCHE.finditer(morceau):
        de, a, taux = _entier(m.group(2)), _entier(m.group(3)), float(m.group(1).replace(",", ".")) / 100
        if abs(de - (tranches[-1][0] + 1)) > 1 or a <= de:     # tranches contiguës et croissantes seulement
            return None
        tranches.append((a, taux))
    tranches.append((None, float(surplus.group(1).replace(",", ".")) / 100))
    if len(tranches) < 4 or any(t2[1] <= t1[1] for t1, t2 in zip(tranches, tranches[1:])):
        return None
    bareme, deduction = [], 0.0
    for i, (plafond, taux) in enumerate(tranches):
        if i:
            deduction += (taux - tranches[i - 1][1]) * tranches[i - 1][0]
        bareme.append((plafond, taux, round(deduction, 2)))
    article = next((a for p, a in reversed([(m.start(), m.group(1)) for m in _ARTICLE.finditer(texte)])
                    if p <= exo.start()), None)
    return {"tranches": bareme, "extrait": morceau[:600], "article": article}


def proposition_bareme(texte, annee, memoire=None):
    """Proposition du barème de l'IR pour `annee`, seulement s'il diffère de celui en vigueur cette année-là."""
    from . import baremes as B
    trouve = bareme_ir(texte)
    if trouve is None:
        return None
    actuel = B.periode("ir", int(annee), memoire)
    if actuel is not None:
        en_vigueur = [(None if t[0] == float("inf") else t[0], t[1], t[2]) for t in actuel["bareme"]]
        if len(en_vigueur) == len(trouve["tranches"]) and all(
                (a[0] == b[0]) and abs(a[1] - b[1]) < 1e-9 and abs(a[2] - b[2]) < 0.5
                for a, b in zip(en_vigueur, trouve["tranches"])):
            return None
    return {"type": "bareme_ir", "cle": "bareme_ir", "valeur": trouve["tranches"], "actuelle": actuel and actuel["loi"],
            "article": trouve["article"], "extrait": trouve["extrait"]}


def analyser(memoire, octets, nom_fichier, annee):
    """Lit le PDF, garde les propositions (en attente de validation) et les renvoie."""
    from . import parametres as P
    actuelles = {cle: getattr(module, attribut) for cle, module, attribut, *_ in P.PARAMETRES}
    lecture = lire_pdf(octets)
    texte = lecture["texte"]
    trouvees = propositions(texte, actuelles)
    bareme = proposition_bareme(texte, annee, memoire)
    if bareme:
        trouvees.append(bareme)
    memoire.definir_reglage("loi:derniere_lecture", json.dumps(
        {"fichier": nom_fichier, "ocr": lecture["ocr"], "pages_lues": lecture["pages_lues"], "pages": lecture["pages"]}))
    for t in trouvees:
        t.update(fichier=nom_fichier, annee=int(annee), statut="à valider", ocr=lecture["ocr"],
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
    if valider and p.get("type") == "bareme_ir":
        from .baremes import ajouter_bareme_ir
        ajouter_bareme_ir(memoire, p["annee"], p["annee"], f"Loi de finances {p['annee']}"
                          + (f", article {p['article']}" if p["article"] else "") + " (CGI, art. 73-I)",
                          f"{p['fichier']} (déposé et lu le {p['lu_le']}), validé par l'{auteur}",
                          [tuple(t) for t in p["valeur"]])
    elif valider:
        P.mettre_a_jour(memoire, p["cle"], p["valeur"], f"01/01/{p['annee']}",
                        f"Loi de finances {p['annee']}" + (f", article {p['article']}" if p["article"] else ""),
                        f"{p['fichier']} (déposé et lu le {p['lu_le']}), validé par l'{auteur}", auteur=auteur)
    memoire.definir_reglage(CLE_REGLAGE, json.dumps(attente, ensure_ascii=False))
    return p
