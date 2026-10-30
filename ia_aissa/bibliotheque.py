"""
La bibliothèque d'IA AISSA : elle broute internet, mange les livres et rumine pour grandir.

1. Brouter : une page web (lien), un livre entier (PDF ou texte, morceau par morceau) ou Wikipédia,
   qu'elle explore de sa propre initiative sur les sujets de ses lacunes.
2. Ruminer : le moteur de conversation compresse chaque morceau en concepts clés, rattachés à une famille
   de sciences, avec une analogie vers le contrôle de gestion, une confiance, et des exercices pour l'école.
3. Intégrer : les concepts entrent dans sa bibliothèque (consultée par l'assistante), les exercices
   deviennent des corrections et des révisions de ses cerveaux, et sa courbe de croissance s'élève.
Seuls les concepts sont gardés, jamais le texte complet des sources.
"""

import io
import ipaddress
import json
import socket
import time
from urllib.parse import urlparse

import numpy as np

from .autonomie import consigne_etude, demander
from .corrections import corriger, reviser_tout
from .ecole import vectoriser_mixte
from .invention import lire_objet

AGENT = "IA-AISSA/1.0 (assistant pédagogique ; https://github.com/IDRISSIIYSA/ia_aissa_assistant)"
TAILLE_MAX = 3_000_000          # octets téléchargés au plus
TAILLE_MORCEAU = 6_000          # caractères par bouchée
FAMILLES_DIGESTION = ["Sciences formelles", "Sciences naturelles", "Sciences humaines et gestion", "Sciences appliquées"]


class ErreurBroutage(Exception):
    pass


# ==========================================
# 1. Brouter
# ==========================================
def adresse_publique(url):
    """Refuse les adresses internes (protection du serveur) ; n'accepte que http(s) vers internet."""
    partie = urlparse(url)
    if partie.scheme not in ("http", "https") or not partie.hostname:
        raise ErreurBroutage("Seuls les liens http(s) sont acceptés.")
    try:
        adresses = {info[4][0] for info in socket.getaddrinfo(partie.hostname, None)}
    except socket.gaierror:
        raise ErreurBroutage(f"Site introuvable : {partie.hostname}")
    for a in adresses:
        ip = ipaddress.ip_address(a)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ErreurBroutage("Adresse interne refusée.")
    return url


def telecharger(url, essais=2):
    import requests
    adresse_publique(url)
    for essai in range(essais):
        r = requests.get(url, headers={"User-Agent": AGENT}, timeout=20, stream=True)
        if r.status_code == 429 and essai + 1 < essais:
            time.sleep(min(30, int(r.headers.get("Retry-After", "5") or 5)))
            continue
        if r.status_code == 429:
            raise ErreurBroutage("Le site limite les visites (429) : IA AISSA réessaiera plus tard.")
        r.raise_for_status()
        contenu = r.raw.read(TAILLE_MAX + 1, decode_content=True)
        if len(contenu) > TAILLE_MAX:
            contenu = contenu[:TAILLE_MAX]
        return contenu, r.headers.get("content-type", "")
    raise ErreurBroutage("Téléchargement impossible.")


def texte_html(contenu):
    from bs4 import BeautifulSoup
    soupe = BeautifulSoup(contenu, "html.parser")
    for balise in soupe(["script", "style", "nav", "footer", "header", "aside", "form"]):
        balise.decompose()
    titre = soupe.title.get_text(" ", strip=True) if soupe.title else ""
    blocs = [b.get_text(" ", strip=True) for b in soupe.find_all(["h1", "h2", "h3", "p", "li"])]
    return titre, "\n".join(b for b in blocs if len(b) > 30)


def texte_pdf(contenu):
    from pypdf import PdfReader
    lecteur = PdfReader(io.BytesIO(contenu))
    titre = (lecteur.metadata.title if lecteur.metadata and lecteur.metadata.title else "")
    return titre, "\n".join((page.extract_text() or "") for page in lecteur.pages)


def brouter_lien(url):
    contenu, type_contenu = telecharger(url)
    if "pdf" in type_contenu or url.lower().endswith(".pdf"):
        titre, texte = texte_pdf(contenu)
    else:
        titre, texte = texte_html(contenu)
    return titre or url, texte


def texte_epub(contenu):
    """Un livre numérique EPUB : une archive zip de pages XHTML, lues dans l'ordre de l'archive."""
    import zipfile
    with zipfile.ZipFile(io.BytesIO(contenu)) as archive:
        pages = sorted(n for n in archive.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
        morceaux = [texte_html(archive.read(n))[1] for n in pages]
    return "", "\n".join(morceaux)


def brouter_fichier(nom, contenu):
    if nom.lower().endswith(".pdf"):
        titre, texte = texte_pdf(contenu)
    elif nom.lower().endswith(".epub"):
        titre, texte = texte_epub(contenu)
    elif nom.lower().endswith((".html", ".htm")):
        titre, texte = texte_html(contenu)
    else:
        texte = contenu.decode("utf-8", errors="replace")
        titre = ""
    return titre or nom, texte


def brouter_wikipedia(sujet, langue="fr"):
    """Cherche le meilleur article Wikipédia sur un sujet et renvoie (titre, texte)."""
    import requests
    api = f"https://{langue}.wikipedia.org/w/api.php"
    for essai in range(2):
        r = requests.get(api, params={"action": "query", "list": "search", "srsearch": sujet, "srlimit": 1,
                                      "format": "json"}, headers={"User-Agent": AGENT}, timeout=20)
        if r.status_code == 429 and essai == 0:
            time.sleep(min(30, int(r.headers.get("Retry-After", "5") or 5)))
            continue
        if r.status_code == 429:
            raise ErreurBroutage("Wikipédia limite les visites (429) : IA AISSA réessaiera plus tard.")
        r.raise_for_status()
        resultats = r.json().get("query", {}).get("search", [])
        if not resultats:
            raise ErreurBroutage(f"Rien trouvé sur Wikipédia pour « {sujet} ».")
        titre = resultats[0]["title"]
        r = requests.get(api, params={"action": "query", "prop": "extracts", "explaintext": 1, "titles": titre,
                                      "format": "json"}, headers={"User-Agent": AGENT}, timeout=20)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        return f"Wikipédia — {titre}", next(iter(pages.values()), {}).get("extract", "")
    raise ErreurBroutage("Wikipédia injoignable.")


def bouchees(texte, nb_max):
    """Découpe le texte en morceaux réguliers répartis sur tout le livre (début, milieu, fin)."""
    texte = " ".join(texte.split())
    morceaux = [texte[i:i + TAILLE_MORCEAU] for i in range(0, len(texte), TAILLE_MORCEAU)]
    if len(morceaux) <= nb_max:
        return morceaux
    indices = np.linspace(0, len(morceaux) - 1, nb_max).round().astype(int)
    return [morceaux[i] for i in sorted(set(indices))]


# ==========================================
# 2. Ruminer
# ==========================================
def ruminer(moteur, client, morceau, source):
    consigne = (
        "Tu es le système digestif d'IA AISSA, une IA marocaine qui apprend seule. Tu viens de « manger » ce "
        f"morceau de « {source} ». Rumine-le : garde l'essentiel, rejette le superflu, compresse en concepts denses.\n\n"
        f"Contenu :\n{morceau}\n\n"
        "Réponds uniquement en JSON : {\"famille\": une de " + json.dumps(FAMILLES_DIGESTION, ensure_ascii=False) +
        ", \"concepts\": [{\"nom\": \"...\", \"explication\": \"2 phrases fidèles au texte\"}] (au plus 6), "
        "\"analogie_controle_gestion\": \"un lien original avec le contrôle de gestion\", "
        "\"confiance\": de 0 à 1 (qualité de la digestion : texte clair et fiable = élevé)}")
    d = lire_objet(demander(moteur, client, consigne))
    concepts = [c for c in d.get("concepts", []) if isinstance(c, dict) and c.get("nom")][:6]
    try:
        confiance = max(0.0, min(1.0, float(d.get("confiance", 0))))
    except (TypeError, ValueError):
        confiance = 0.0
    famille = d.get("famille") if d.get("famille") in FAMILLES_DIGESTION else "Sciences humaines et gestion"
    return {"famille": famille, "concepts": concepts, "analogie": str(d.get("analogie_controle_gestion", "")),
            "confiance": confiance}


def exercices_pour_ecole(moteur, client, concepts):
    """Transforme les concepts digérés en exercices du programme d'IA AISSA (quand une matière s'y prête)."""
    questions = [{"id": i, "question": f"{c['nom']} : {c.get('explication', '')}"[:280]}
                 for i, c in enumerate(concepts, 1)]
    if not questions:
        return []
    from .autonomie import lire_json
    reponses = lire_json(demander(moteur, client, consigne_etude(questions)))
    return [(q["question"], r["matiere"], r["reponse"]) for q in questions for r in reponses
            if isinstance(r, dict) and r.get("id") == q["id"] and r.get("matiere") and r.get("reponse")]


# ==========================================
# 3. Intégrer
# ==========================================
def digerer(memoire, moteur, client, source, texte, utilisateur="IA AISSA", nb_bouchees=4, callback=None,
            famille=None):
    """Mange le texte (morceau par morceau), rumine, range les concepts et nourrit l'école. Renvoie le bilan."""
    if len(texte.strip()) < 200:
        raise ErreurBroutage("Pas assez de texte à manger (page vide, protégée ou scannée sans texte).")
    morceaux = bouchees(texte, nb_bouchees)
    digestions = []
    for k, morceau in enumerate(morceaux, 1):
        if client is None:                          # sans moteur : IA AISSA rumine seule, et recommence sous 75 %
            from .autodidacte import ruminer_recursif
            d, _ = ruminer_recursif(texte, morceau, source, famille)
        else:
            d = ruminer(moteur, client, morceau, source)
        if d["concepts"]:
            memoire.garder_digestion(utilisateur, source, d["famille"], json.dumps(d["concepts"], ensure_ascii=False),
                                     d["analogie"], d["confiance"])
            digestions.append(d)
        if callback:
            callback(k, len(morceaux), d)
    concepts = [c for d in digestions for c in d["concepts"]]
    comblees = combler_lacunes(memoire, concepts)
    apprises = 0
    for question, matiere, reponse in (exercices_pour_ecole(moteur, client, concepts) if client else []):
        try:
            corriger(memoire, "IA AISSA", matiere, question, reponse, source="lecture")
            apprises += 1
        except ValueError:
            pass
    return {"source": source, "bouchees": len(morceaux), "concepts": len(concepts), "digestions": digestions,
            "exercices": apprises, "lacunes_comblees": comblees,
            "revisions": reviser_tout(memoire) if apprises else []}


SEUIL_COMBLEMENT = 0.3


def combler_lacunes(memoire, concepts):
    """Ferme les lacunes ouvertes auxquelles un concept digéré répond (proximité des mots et des lettres)."""
    if not concepts:
        return []
    vecteurs = [vectoriser_mixte(f"{c['nom']} {c.get('explication', '')}") for c in concepts]
    comblees = []
    for lacune in memoire.lacunes_ouvertes(200):
        q = vectoriser_mixte(lacune["question"])
        score, concept = max((float(np.dot(q, v)), c["nom"]) for v, c in zip(vecteurs, concepts))
        if score >= SEUIL_COMBLEMENT:
            memoire.resoudre_lacune(lacune["id"])
            comblees.append({"question": lacune["question"], "concept": concept, "proximite": round(score, 3)})
    return comblees


AUTONOME = "IA AISSA"            # ce qu'elle a lu seule sur le web : savoir commun à tous
BIBLIOTHEQUE = "Bibliothèque"    # les livres déposés par l'administrateur : savoir commun, jamais oublié


def visible_par(d, utilisateur):
    """Les documents d'une personne restent les siens : elle ne voit que ses lectures et le savoir commun."""
    return utilisateur is None or d["utilisateur"] in (utilisateur, AUTONOME, BIBLIOTHEQUE)


def chercher(memoire, requete, n=5, utilisateur=None):
    """Les concepts de la bibliothèque les plus proches d'une question (similarité des mots et des lettres).
    utilisateur : ne cherche que dans ses documents à lui et dans le savoir commun (lu seule sur le web)."""
    fiches = [(d, c) for d in memoire.digestions() if visible_par(d, utilisateur) for c in json.loads(d["concepts"])]
    if not fiches:
        return []
    q = vectoriser_mixte(requete)
    scores = [float(np.dot(q, vectoriser_mixte(f"{c['nom']} {c.get('explication', '')}"))) for _, c in fiches]
    meilleurs = sorted(zip(scores, fiches), key=lambda x: -x[0])[:n]
    return [{"concept": c["nom"], "explication": c.get("explication", ""), "source": d["source"],
             "famille": d["famille"], "pertinence": round(s, 3), "id": d["id"]} for s, (d, c) in meilleurs if s > 0.05]


def explorer_lacunes(memoire, moteur, client, nb_sujets=2, callback=None, sujets=None):
    """Initiative d'IA AISSA : elle va chercher sur Wikipédia de quoi combler ses lacunes, puis rumine."""
    bilans = []
    for sujet in sujets or [l["question"] for l in memoire.lacunes_ouvertes(nb_sujets)]:
        try:
            source, texte = brouter_wikipedia(sujet)
            bilans.append(digerer(memoire, moteur, client, source, texte, nb_bouchees=2, callback=callback))
        except ErreurBroutage as e:
            bilans.append({"source": sujet, "erreur": str(e)})
    return bilans
