"""
Les rapports de simulation d'IA AISSA : justifiés, référencés, traçables, téléchargeables en PDF.

Chaque rapport contient les données saisies, les résultats, la méthode (formules), les références légales avec
l'année et les taux appliqués, les limites, et — pour la traçabilité attendue dans une démarche qualité de type
ISO 9001 (maîtrise des informations documentées) — un numéro unique, la date, la version d'IA AISSA et une empreinte
SHA-256 du contenu, gardée dans un journal : on peut prouver plus tard qu'un rapport n'a pas été modifié.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

LIMITES = ("Calcul conforme aux règles des textes cités (articles et taux de l'année de référence), dans leur version "
           "vérifiée à la date indiquée. Les régimes particuliers non saisis (exonérations, zones, conventions, "
           "dispositions transitoires) ne sont pas appliqués : ils sont signalés dans « À savoir ». Avant un dépôt "
           "officiel (déclaration, bulletin, acte), faites valider par un expert-comptable, un avocat ou l'administration "
           "concernée : ce rapport ne les engage pas.")


def version():
    try:
        ligne = next(l for l in (Path(__file__).resolve().parents[1] / "requirements.txt").read_text().splitlines()
                     if "Version d'IA AISSA" in l)
        return ligne.split(":", 1)[1].split("(")[0].strip()
    except (OSError, StopIteration):
        return "inconnue"


def rapport(titre, categorie, entrees, resultats, methode, references, annee=None, tableau=None, remarques=(),
            conseils=()):
    """Assemble un rapport ; entrees et resultats sont des dictionnaires {libellé: valeur affichable}."""
    maintenant = datetime.now(timezone.utc)
    r = {"numero": f"IAA-{maintenant:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4].upper()}",
         "date": maintenant.strftime("%d/%m/%Y %H:%M UTC"), "version": version(), "titre": titre, "categorie": categorie,
         "annee": annee, "entrees": {k: str(v) for k, v in entrees.items()},
         "resultats": {k: str(v) for k, v in resultats.items()}, "methode": list(methode),
         "references": list(references), "remarques": list(remarques), "conseils": list(conseils), "limites": LIMITES}
    r["empreinte"] = empreinte(r)
    r["tableau"] = tableau
    return r


def empreinte(r):
    contenu = {k: r[k] for k in ("numero", "date", "version", "titre", "annee", "entrees", "resultats", "methode",
                                 "references", "conseils")}
    return hashlib.sha256(json.dumps(contenu, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def journaliser(memoire, r):
    """Garde la trace du rapport émis (numéro, date, titre, empreinte) dans le journal des rapports."""
    memoire.definir_reglage(f"rapport:{r['numero']}", json.dumps(
        {"numero": r["numero"], "date": r["date"], "titre": r["titre"], "annee": r["annee"], "empreinte": r["empreinte"],
         "version": r["version"]}, ensure_ascii=False))


def journal(memoire):
    return [json.loads(v) for _, v in sorted(memoire.reglages("rapport:").items(), reverse=True)]


def verifier(memoire, numero, empreinte_lue):
    """Vrai si le numéro existe dans le journal avec exactement cette empreinte (rapport non modifié)."""
    trace = memoire.reglage(f"rapport:{numero.strip()}")
    return bool(trace) and json.loads(trace)["empreinte"] == empreinte_lue.strip().lower()


def markdown(r):
    lignes = [f"**{r['titre']}**" + (f" — année de référence **{r['annee']}**" if r["annee"] else ""), "",
              "| Donnée | Valeur |", "|---|---|"] + [f"| {k} | {v} |" for k, v in r["entrees"].items()]
    lignes += ["", "| Résultat | Valeur |", "|---|---|"] + [f"| {k} | **{v}** |" for k, v in r["resultats"].items()]
    lignes += ["", "**Méthode et justification**"] + [f"{i}. {m}" for i, m in enumerate(r["methode"], 1)]
    if r["conseils"]:
        lignes += ["", "**💡 Propositions et optimisation**"] + [f"- {x}" for x in r["conseils"]]
    lignes += ["", "**Références**"] + [f"- {x}" for x in r["references"]]
    if r["remarques"]:
        lignes += ["", "**À savoir**"] + [f"- {x}" for x in r["remarques"]]
    lignes += ["", f"_{r['limites']}_", "",
               f"<small>Rapport n° {r['numero']} · {r['date']} · version {r['version']} · empreinte SHA-256 "
               f"{r['empreinte'][:16]}…</small>"]
    return "\n".join(lignes)


# ==========================================
# PDF
# ==========================================
REMPLACEMENTS = {"—": "-", "–": "-", "→": "->", "←": "<-", "↔": "<->", "≤": "<=", "≥": ">=", "×": "x", "÷": "/",
                 "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...", "€": "EUR", " ": " ", " ": " ", "•": "-",
                 "√": "racine", "Σ": "somme", "≈": "~", "∞": "infini", "−": "-"}


def latin1(texte):
    """Le texte en caractères latin-1 (police standard du PDF) : symboles remplacés, émojis retirés."""
    texte = str(texte)
    for a, b in REMPLACEMENTS.items():
        texte = texte.replace(a, b)
    texte = re.sub(r"\*\*|__|`", "", texte)
    return texte.encode("latin-1", "ignore").decode("latin-1")


def pdf(r):
    """Le rapport en PDF (octets)."""
    from fpdf import FPDF

    class Document(FPDF):
        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "I", 7)
            self.cell(0, 5, latin1(f"IA AISSA - rapport {r['numero']} - empreinte SHA-256 {r['empreinte']} - "
                                   f"page {self.page_no()}"), align="C")

    doc = Document(format="A4")
    doc.set_auto_page_break(True, 18)
    doc.add_page()
    largeur = doc.w - doc.l_margin - doc.r_margin
    doc.set_font("Helvetica", "B", 15)
    doc.multi_cell(largeur, 8, latin1(f"{r['titre']}"))
    doc.set_font("Helvetica", "", 9)
    doc.multi_cell(largeur, 5, latin1(f"Catégorie : {r['categorie']}" + (f"   -   Année de référence : {r['annee']}"
                                                                          if r["annee"] else "")))
    doc.multi_cell(largeur, 5, latin1(f"Rapport n° {r['numero']}   -   émis le {r['date']}   -   IA AISSA version "
                                      f"{r['version']}"))
    doc.ln(3)

    def section(titre):
        doc.ln(2)
        doc.set_font("Helvetica", "B", 11)
        doc.set_fill_color(232, 238, 251)
        doc.cell(largeur, 7, latin1(titre), fill=True, new_x="LMARGIN", new_y="NEXT")
        doc.set_font("Helvetica", "", 9)

    def paires(d):
        for k, v in d.items():
            doc.set_font("Helvetica", "B", 9)
            doc.cell(largeur * 0.45, 6, latin1(k), border="B")
            doc.set_font("Helvetica", "", 9)
            doc.multi_cell(largeur * 0.55, 6, latin1(v), border="B", new_x="LMARGIN", new_y="NEXT")

    section("1. Données saisies")
    paires(r["entrees"])
    section("2. Résultats")
    paires(r["resultats"])
    section("3. Méthode et justification")
    for i, m in enumerate(r["methode"], 1):
        doc.multi_cell(largeur, 5, latin1(f"{i}. {m}"))
    if r["conseils"]:
        section("Propositions et optimisation")
        for x in r["conseils"]:
            doc.multi_cell(largeur, 5, latin1(f"- {x}"))
    section("4. Références (lois, articles, taux de l'année)")
    for x in r["references"]:
        doc.multi_cell(largeur, 5, latin1(f"- {x}"))
    if r["remarques"]:
        section("5. À savoir")
        for x in r["remarques"]:
            doc.multi_cell(largeur, 5, latin1(f"- {x}"))
    tableau = r.get("tableau")
    if tableau is not None and len(tableau):
        section("Annexe - tableau détaillé" + (" (extrait : 60 premières lignes)" if len(tableau) > 60 else ""))
        colonnes = list(tableau.columns)
        l_col = largeur / len(colonnes)
        doc.set_font("Helvetica", "B", 8)
        for c in colonnes:
            doc.cell(l_col, 6, latin1(c)[:24], border=1, align="C")
        doc.ln()
        doc.set_font("Helvetica", "", 8)
        for ligne in tableau.head(60).itertuples(index=False):
            for v in ligne:
                texte = f"{v:,.2f}".replace(",", " ") if isinstance(v, float) else str(v)
                doc.cell(l_col, 5, latin1(texte), border=1, align="R")
            doc.ln()
    section("Limites et traçabilité")
    doc.multi_cell(largeur, 5, latin1(r["limites"]))
    doc.multi_cell(largeur, 5, latin1(
        f"Traçabilité : ce rapport est enregistré dans le journal d'IA AISSA sous le n° {r['numero']} avec l'empreinte "
        f"SHA-256 {r['empreinte']}. Toute modification du contenu change l'empreinte."))
    return bytes(doc.output())
