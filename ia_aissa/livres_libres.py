"""
Livres libres : IA AISSA recommande des bibliothèques gratuites et légales, et va elle-même y chercher des livres.

Sa règle, avant d'entrer sur un site : elle lit son robots.txt et vérifie qu'il l'accepte (avec son identité honnête
« IA-AISSA/1.0 », jamais déguisée en navigateur). Si oui, elle entre ; si non (robots.txt, ou refus 401/403 comme
management.org), elle passe à une autre source. Elle ne va jamais sur des sites de livres piratés : un site
repéré est refusé, et un PDF commercial remis en ligne (filigrane ou fiche de commande de l'acheteur) est supprimé
sans être lu.

Une fois un livre téléchargé (70 Mo au plus), elle le lit (150 pages réparties pour un très gros manuel), le rumine
avec sa pensée propre, range l'essentiel dans sa mémoire, puis supprime le fichier.
"""

import json
import os
import tempfile
from urllib.parse import urlparse

from .ecole import mots

# Bibliothèques gratuites et légales. acces = "auto" : elle y va seule ; "manuel" : à télécharger vous-même
# (site qui refuse les robots ou le demande), puis à déposer dans « 🌌 Cosmic Knowledge Ingestion ».
SOURCES_LIBRES = [
    {"nom": "OpenStax", "url": "https://openstax.org/subjects", "acces": "auto", "licence": "CC BY (manuels libres)",
     "contenu": "manuels universitaires : comptabilité financière et de gestion, management, économie, finance, "
                "statistiques, entrepreneuriat, marketing, sciences"},
    {"nom": "Wikilivres (fr.wikibooks.org)", "url": "https://fr.wikibooks.org", "acces": "auto", "licence": "CC BY-SA",
     "contenu": "livres pédagogiques collaboratifs en français (comptabilité, programmation, mathématiques…)"},
    {"nom": "Wikisource (fr.wikisource.org)", "url": "https://fr.wikisource.org", "acces": "auto",
     "licence": "domaine public", "contenu": "textes classiques : littérature, philosophie, histoire, économie"},
    {"nom": "Free Management Library (management.org)", "url": "https://management.org/index.html", "acces": "manuel",
     "licence": "gratuit en ligne", "contenu": "management, leadership, stratégie, finances, RH, marketing",
     "pourquoi": "le site refuse les robots (réponse 403) : ouvrez-le vous-même"},
    {"nom": "Project Gutenberg", "url": "https://www.gutenberg.org", "acces": "manuel", "licence": "domaine public",
     "contenu": "plus de 70 000 livres classiques (EPUB, PDF, texte)",
     "pourquoi": "le site est réservé aux visiteurs humains : téléchargez l'EPUB et déposez-le"},
    {"nom": "OAPEN Library", "url": "https://library.oapen.org", "acces": "manuel", "licence": "accès ouvert",
     "contenu": "livres universitaires en accès ouvert (économie, gestion, droit, sciences sociales)"},
    {"nom": "HAL (archive ouverte française)", "url": "https://hal.science", "acces": "manuel", "licence": "accès ouvert",
     "contenu": "thèses et articles de recherche en français", "pourquoi": "sa recherche est fermée aux robots"},
    {"nom": "Bank Al-Maghrib — publications", "url": "https://www.bkam.ma", "acces": "manuel", "licence": "publications publiques",
     "contenu": "rapports annuels, politique monétaire, statistiques financières du Maroc"},
    {"nom": "HCP — Haut-Commissariat au Plan", "url": "https://www.hcp.ma", "acces": "manuel",
     "licence": "publications publiques", "contenu": "statistiques et études économiques et sociales du Maroc"},
]
OPENSTAX_API = ("https://openstax.org/apps/cms/api/v2/pages/?type=books.Book"
                "&fields=title,high_resolution_pdf_url&limit=200")
# Sites vérifiés qui remettent en ligne des livres commerciaux sans autorisation : jamais visités.
SITES_REFUSES = {"livre21.com": "copies de livres commerciaux, avec le filigrane de l'acheteur (vérifié le 30/10/2026)"}
FILIGRANES = ("propriété exclusive de", "propriete exclusive de", "licensed to", "licence accordée à",
              "réservé à l'usage exclusif", "this copy belongs to", "copie personnelle de")
PRIORITES = ("accounting", "management", "finance", "economics", "statistics", "entrepreneurship", "marketing",
             "organizational", "business")


def recommander(theme=""):
    """Les bibliothèques libres, celles qui parlent du thème d'abord ; en markdown."""
    cles = {m for m in mots(theme) if len(m) > 3}
    sources = sorted(SOURCES_LIBRES, key=lambda s: -len(cles & set(mots(s["contenu"] + " " + s["nom"]))))
    lignes = []
    for s in sources:
        acces = ("je peux y aller seule" if s["acces"] == "auto"
                 else f"à télécharger toi-même puis à me déposer ({s.get('pourquoi', 'site à visiter à la main')})")
        lignes.append(f"- **[{s['nom']}]({s['url']})** — {s['contenu']} · _{s['licence']}_ · {acces}")
    return ("Voici des bibliothèques **gratuites et légales** (jamais de sites piratés) :\n\n" + "\n".join(lignes)
            + "\n\nAvant d'entrer sur un site, je lis son robots.txt : s'il m'accepte j'entre, sinon je cherche "
              "ailleurs. Donne-moi un lien vers un PDF libre, ou dépose le livre : je le lis et je te dis quand "
              "tu peux le supprimer.")


def catalogue_openstax(brouteur):
    """[(titre, url du PDF)] des manuels OpenStax, ceux de gestion et d'économie d'abord, éditions récentes d'abord."""
    livres = json.loads(brouteur.visiter(OPENSTAX_API))["items"]
    livres = [(l["title"], l["high_resolution_pdf_url"]) for l in livres if l.get("high_resolution_pdf_url")]
    rang = lambda t: next((i for i, p in enumerate(PRIORITES) if p in t.lower()), len(PRIORITES))
    return sorted(livres, key=lambda l: (rang(l[0]), -len(l[0])))


def site_refuse(url):
    domaine = urlparse(url).netloc.lower().removeprefix("www.")
    return SITES_REFUSES.get(domaine)


def verifier_droits(chemin, nom):
    """Refuse un livre commercial vendu à une personne puis remis en ligne : filigrane de l'acheteur dans les pages,
    ou fiche de commande (OwnerEmail, OrderNumber) dans le PDF. Renvoie le motif du refus, ou None."""
    if not nom.lower().endswith(".pdf"):
        return None
    from pypdf import PdfReader
    try:
        lecteur = PdfReader(chemin)
    except Exception:
        return None
    infos = {str(k) for k in (lecteur.metadata or {})}
    if {"/OwnerEmail", "/OrderNumber", "/OwnerName"} & infos:
        return "PDF vendu à une personne (fiche de commande dans le fichier) : copie non autorisée"
    debut = " ".join((lecteur.pages[i].extract_text() or "") for i in range(min(3, len(lecteur.pages)))).lower()
    if any(f in debut for f in FILIGRANES):
        return "filigrane de l'acheteur dans les pages : copie non autorisée"
    return None


def deja_lu(memoire, url):
    return memoire.reglage(f"livre_lu:{url}") is not None


def manger_livre(memoire, brouteur, url, titre=None, utilisateur="IA AISSA"):
    """Télécharge (poliment, si le site l'autorise) un livre PDF ou EPUB libre, le lit, le garde, le supprime."""
    from .pensee import ingerer_fichier
    nom = os.path.basename(urlparse(url).path) or "livre.pdf"
    temporaire = tempfile.NamedTemporaryFile(suffix=".epub" if nom.lower().endswith(".epub") else ".pdf", delete=False)
    temporaire.close()
    from .bibliotheque import ErreurBroutage
    refus = site_refuse(url)
    if refus:
        os.remove(temporaire.name)
        raise ErreurBroutage(f"je ne me nourris pas sur ce site ({refus}) : je cherche une source libre")
    try:
        brouteur.telecharger(url, temporaire.name)
        refus = verifier_droits(temporaire.name, nom)
        if refus:
            raise ErreurBroutage(f"{refus} — je l'ai supprimé sans le lire, je cherche une source libre")
    except Exception:
        if os.path.exists(temporaire.name):
            os.remove(temporaire.name)
        raise
    bilan = ingerer_fichier(memoire, temporaire.name, nom, utilisateur, source=titre or nom)
    memoire.definir_reglage(f"livre_lu:{url}", json.dumps({"titre": bilan["source"], "concepts": bilan["concepts"]},
                                                         ensure_ascii=False))
    return bilan


def repas_de_livre(memoire, brouteur, max_essais=4):
    """Un manuel libre pas encore lu : elle essaie les sources autorisées les unes après les autres ; un refus
    (robots.txt, 403, fichier trop lourd) la fait passer au livre ou à la source suivante."""
    refus = []
    for titre, url in catalogue_openstax(brouteur):
        if deja_lu(memoire, url):
            continue
        try:
            return {**manger_livre(memoire, brouteur, url, f"OpenStax — {titre}"), "refus": refus}
        except Exception as e:
            refus.append(f"{titre} : {e}")
            memoire.definir_reglage(f"livre_lu:{url}", json.dumps({"titre": titre, "refus": str(e)[:200]}))
            if len(refus) >= max_essais:
                break
    return {"source": None, "concepts": 0, "refus": refus}
