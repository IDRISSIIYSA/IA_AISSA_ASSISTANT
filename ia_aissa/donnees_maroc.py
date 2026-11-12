"""
Les données officielles marocaines, lues sur le portail national des données ouvertes data.gov.ma.

Conditions vérifiées le 31/10/2026 (et le 01/11/2026 pour ACAPS, CMR, CNRA, CNOPS) : l'API du portail (CKAN, /data/api/3/) est publique et n'est pas interdite par son
robots.txt ; les jeux de données du HCP (82), de Bank Al-Maghrib (43) et de la CNSS (12) sont publiés sous licence
ouverte ODbL (réutilisation libre, avec obligation de citer la source et de partager à l'identique une base dérivée),
au format Excel. IA AISSA cite donc toujours l'institution, le jeu de données et la licence.

Chaque semaine : le catalogue de chaque institution (titre, date, lien) et quelques tableaux, à tour de rôle (les
jamais lus d'abord, les thèmes les plus demandés en tête : chômage, prix, PIB, crédits, salariés…), sont lus et rangés dans sa mémoire de lecture, une phrase par ligne
de tableau, pour qu'elle puisse répondre en citant l'institution et l'année.
"""

import datetime
import json
import os
import re
import tempfile

from .bibliotheque import ErreurBroutage

PORTAIL = "https://data.gov.ma"
API = PORTAIL + "/data/api/3/action/package_search"
LICENCE = "licence ouverte ODbL, data.gov.ma"
INSTITUTIONS = {"haut-commissariat-au-plan": "HCP", "bank-al-maghrib": "Bank Al-Maghrib", "cnss": "CNSS",
                "autorite-de-controle-des-assurances-et-de-la-prevoyance-sociale": "ACAPS",
                "caisse-marocaine-des-retraites": "CMR", "caisse-nationale-de-retraites-et-d-assurances": "CNRA",
                "caisse-nationale-des-organismes-de-prevoyance-sociale": "CNOPS"}   # toutes en ODbL (vérifié le 01/11/2026)
THEMES = ("chômage", "prix", "inflation", "pib", "crédit", "salari", "masse salariale", "emploi", "épargne",
          "cotisation", "pension", "retraite", "assurance maladie", "amo", "rente", "prestation", "tarification",
          "valeur ajoutée", "activité")                     # du plus demandé au moins demandé

# Sources examinées et NON lues, faute d'autorisation de réutilisation (vérifié le 01/11/2026) : IA AISSA renvoie
# vers elles par leur lien, sans copier leur contenu.
SOURCES_NON_LUES = {
    "DEPF (Direction des études et des prévisions financières)": (
        "https://www.finances.gov.ma", "site du ministère « © Tous droits réservés », sans licence ouverte ; "
        "le serveur depf.finances.gov.ma coupe les connexions automatiques"),
    "Office des changes (balance commerciale, transferts)": (
        "https://www.oc.gov.ma", "le site rejette les robots (page « Request Rejected »)"),
}
MAX_TABLEAUX = 8
MAX_LIGNES = 80
MAX_OCTETS = 3_000_000
FREQUENCE_JOURS = 7


def catalogue(brouteur, organisation):
    """Les jeux de données d'une institution (titre, date, description, ressources), du plus récent au plus ancien."""
    brut = brouteur.visiter(API, {"fq": f"organization:{organisation}", "rows": 200, "sort": "metadata_modified desc"})
    try:
        resultat = json.loads(brut)["result"]["results"]
    except (ValueError, KeyError, TypeError) as e:
        raise ErreurBroutage(f"Réponse inattendue de data.gov.ma ({type(e).__name__}).") from e
    return resultat


def fiche(sigle, jeu):
    """Une phrase de catalogue : ce que publie l'institution, quand, sous quelle licence, où."""
    formats = sorted({(r.get("format") or "").upper() for r in jeu.get("resources", []) if r.get("format")})
    note = re.sub(r"\s+", " ", jeu.get("notes") or "").strip()
    return (f"{sigle} publie « {jeu['title']} » sur data.gov.ma (mis à jour le {jeu.get('metadata_modified', '')[:10]}, "
            f"{jeu.get('license_title') or 'licence non précisée'}, formats {', '.join(formats) or '—'})"
            + (f" : {note[:200]}" if note else "") + f". Lien : {PORTAIL}/data/fr/dataset/{jeu['name']}")


def nombre_fr(v):
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}".replace(",", " ")                 # 6100 → « 6 100 », comme les nombres à virgule
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", " ").replace(".", ",").rstrip("0").rstrip(",")
    return str(v)


def date_de(entete):
    """(année, trimestre) d'un en-tête de colonne (« 2025 », « T4-2025 », « 2024-T2 »), ou None."""
    m = re.search(r"(?<!\d)(19\d\d|20\d\d)(?!\d)", str(entete or ""))
    if not m:
        return None
    t = re.search(r"\bT([1-4])\b", str(entete))
    return int(m.group(1)), int(t.group(1)) if t else 0


def tableau_en_phrases(chemin, sigle, titre, max_lignes=MAX_LIGNES):
    """Un tableau Excel en phrases : « titre — dimensions : valeur (colonne) ; … ». Repère tout seul la ligne de titre
    et la ligne d'en-têtes (la première ligne d'au moins trois cellules)."""
    import openpyxl
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        classeur = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    phrases = []
    for feuille in classeur.worksheets[:3]:
        intitule, entetes = titre, None
        for ligne in feuille.iter_rows(values_only=True):
            cellules = [c for c in ligne if c not in (None, "")]
            if not cellules:
                continue
            if entetes is None:
                if len(cellules) >= 3:              # en-têtes : du texte ou des années, jamais une valeur
                    entetes = [str(c).strip() if isinstance(c, str) else
                               str(int(c)) if isinstance(c, (int, float)) and float(c).is_integer() and 1900 <= c <= 2100
                               else "" for c in ligne]
                elif isinstance(cellules[0], str):
                    intitule = cellules[0].strip()
                continue
            etiquettes = [str(c).strip() for c in ligne if isinstance(c, str) and c.strip()]
            valeurs = [(entetes[i] if i < len(entetes) else "", c) for i, c in enumerate(ligne)
                       if isinstance(c, (int, float)) and not isinstance(c, bool)]
            if not valeurs:
                continue
            datees = [(date_de(e), e, v) for e, v in valeurs]
            if any(d for d, _, _ in datees):            # séries datées : la plus récente d'abord, et annoncée
                valeurs = [(e, v) for _, e, v in sorted(datees, key=lambda x: x[0] or (0, 0), reverse=True)]
                (e0, v0), reste = valeurs[0], valeurs[1:6]
                detail = (f"dernier chiffre publié : {nombre_fr(v0)} ({e0})"
                          + ("" if not reste else " ; avant : " + " ; ".join(
                              f"{nombre_fr(v)} ({e})" if e else nombre_fr(v) for e, v in reste)))
            else:
                detail = " ; ".join(f"{nombre_fr(v)} ({e})" if e else nombre_fr(v) for e, v in valeurs[:6])
            phrases.append(f"{sigle} — {intitule} — {', '.join(etiquettes) or 'ensemble'} : {detail}.")
            if len(phrases) >= max_lignes:
                classeur.close()
                return phrases
    classeur.close()
    return phrases


def rang_theme(titre):
    titre = titre.lower()
    return next((i for i, t in enumerate(THEMES) if t in titre), None)


def ordre_de_lecture(jeu, lus):
    """Rotation : d'abord les jeux jamais lus (les thèmes les plus demandés en tête), puis les plus anciennement lus.
    Semaine après semaine, tout le catalogue est lu ; ce qui a été lu reste dans sa mémoire."""
    rang = rang_theme(jeu["title"])
    return lus.get(jeu["name"], ""), len(THEMES) if rang is None else rang


def ressource_donnees(jeu):
    """Le fichier de données du jeu (pas celui des métadonnées), en Excel moderne (XLSX)."""
    for r in jeu.get("resources", []):
        url = r.get("url") or ""
        if (r.get("format") or "").upper() == "XLSX" and "metadata" not in url.lower():   # l'ancien XLS : illisible
            return url
    return None


def repas_donnees_maroc(memoire, brouteur=None, aujourdhui=None, forcer=False, max_tableaux=MAX_TABLEAUX):
    """Catalogues et tableaux officiels, rangés dans sa mémoire de lecture (au plus une fois par semaine)."""
    aujourdhui = aujourdhui or datetime.date.today()
    derniere = memoire.reglage("donnees_maroc:derniere")
    if derniere and not forcer:
        if (aujourdhui - datetime.date.fromisoformat(json.loads(derniere)["date"])).days < FREQUENCE_JOURS:
            return {**json.loads(derniere), "deja": True}
    if brouteur is None:
        from .broutage import Brouteur
        brouteur = Brouteur()
    bilan = {"date": aujourdhui.isoformat(), "catalogues": {}, "tableaux": [], "refus": []}
    memoire.garder_passages("IA AISSA", "Sources officielles marocaines à consulter directement",
                            [f"{nom} : je ne recopie pas ses publications ({raison}) ; consultez-les à la source : {lien}."
                             for nom, (lien, raison) in SOURCES_NON_LUES.items()])
    a_lire = []
    lus = json.loads(memoire.reglage("donnees_maroc:lus") or "{}")     # jeu → date de sa dernière lecture
    for organisation, sigle in INSTITUTIONS.items():
        try:
            jeux = catalogue(brouteur, organisation)
        except ErreurBroutage as e:
            bilan["refus"].append(f"{sigle} : {e}")
            continue
        memoire.garder_passages("IA AISSA", f"data.gov.ma — catalogue {sigle} ({LICENCE})",
                                [fiche(sigle, j) for j in jeux])
        bilan["catalogues"][sigle] = len(jeux)
        lisibles = [j for j in jeux if ressource_donnees(j)]
        a_lire.append((sigle, sorted(lisibles, key=lambda j: ordre_de_lecture(j, lus))))
    choisis = []                                    # les thèmes les plus demandés, en alternant les institutions
    while len(choisis) < max_tableaux and any(jeux for _, jeux in a_lire):
        for sigle, jeux in a_lire:
            if jeux and len(choisis) < max_tableaux:
                choisis.append((sigle, jeux.pop(0)))
    for sigle, jeu in choisis:
        url = ressource_donnees(jeu)
        lus[jeu["name"]] = bilan["date"]               # lu ou refusé : la rotation passe au suivant
        descripteur, chemin = tempfile.mkstemp(suffix=".xlsx")
        os.close(descripteur)
        try:
            brouteur.telecharger(url, chemin, max_octets=MAX_OCTETS)
            phrases = tableau_en_phrases(chemin, sigle, jeu["title"])
        except Exception as e:                      # fichier trop gros, refusé ou illisible : on passe au suivant
            bilan["refus"].append(f"{jeu['title'][:60]} : {str(e)[:80]}")
            continue
        finally:
            if os.path.exists(chemin):
                os.remove(chemin)                   # rien ne reste sur le disque du serveur
        if phrases:
            memoire.garder_passages("IA AISSA", f"{sigle} — {jeu['title']} ({LICENCE})", phrases)
            bilan["tableaux"].append({"institution": sigle, "titre": jeu["title"], "lignes": len(phrases)})
    memoire.definir_reglage("donnees_maroc:lus", json.dumps(lus))
    bilan["couverture"] = {"lus": len(lus), "total": sum(len(j) for _, j in a_lire) + len(choisis)}
    memoire.definir_reglage("donnees_maroc:derniere", json.dumps(bilan, ensure_ascii=False))
    return bilan
