"""
Broutage autonome : IA AISSA part seule, en arrière-plan, se nourrir sur internet, puis rumine et invente.

Un travailleur d'arrière-plan (un fil d'exécution par serveur) choisit un sujet (d'abord ses lacunes, sinon
un sujet du programme des quatre familles de sciences et du contrôle de gestion), va le chercher sur des
sources académiques ouvertes (API Wikipédia, API arXiv), le rumine en concepts denses, et injecte chaque
analogie avec le contrôle de gestion dans sa galerie d'inventions. Sa courbe de croissance monte en direct.

Un brouteur poli, jamais déguisé :
- il s'annonce honnêtement (User-Agent « IA-AISSA/1.0 ») et respecte le fichier robots.txt de chaque site ;
- il attend 2 à 5 secondes (aléatoire) entre deux visites d'un même site ;
- sur une réponse 429 (« trop de visites »), il se met au repos sur ce site le temps demandé (Retry-After) ;
- il ne garde que le texte utile (ni scripts, ni menus, ni pieds de page) et au plus 10 000 caractères par page ;
- il respecte un budget quotidien d'appels au moteur (secret BROUTAGE_PAR_JOUR, 6 par défaut).
"""

import random
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from .bibliotheque import AGENT, ErreurBroutage, adresse_publique, digerer, texte_html

TAILLE_MAX_PAGE = 10_000
SUJETS = {
    "Sciences formelles": ["théorie des graphes", "probabilités bayésiennes", "optimisation linéaire",
                           "apprentissage par renforcement", "théorie des jeux", "séries temporelles"],
    "Sciences naturelles": ["photosynthèse", "thermodynamique", "écosystème", "génétique des populations",
                            "énergie solaire photovoltaïque", "cycle de l'eau"],
    "Sciences humaines et gestion": ["contrôle de gestion", "comptabilité analytique", "tableau de bord prospectif",
                                     "budget base zéro", "économie comportementale", "gouvernance d'entreprise"],
    "Sciences appliquées": ["gestion de la chaîne logistique", "maintenance prédictive", "lean management",
                            "agriculture de précision", "économie circulaire", "dessalement de l'eau de mer"],
}
BANDEAUX = ("Pour les articles homonymes", "Cet article", "Si vous disposez", "Vous pouvez partager",
            "Pour l'article", "Ne doit pas être confondu", "Cette section")
REESSAI = 600                  # secondes avant de retenter un repas raté
ETAT = {"actif": False, "dernier_repas": None, "repas_du_jour": 0, "jour": None, "erreurs": [], "prochain": None}


class Brouteur:
    """Visites polies : robots.txt, délai aléatoire par site, repos sur 429, nettoyage du texte."""

    def __init__(self, dormir=time.sleep, delai=(2.0, 5.0), repos_429=60):
        self.dormir, self.delai, self.repos_429 = dormir, delai, repos_429
        self.robots, self.derniere_visite, self.repos_jusqua = {}, {}, {}

    def autorise(self, url):
        site = urlparse(url)
        racine = f"{site.scheme}://{site.netloc}"
        if racine not in self.robots:
            regles = RobotFileParser(racine + "/robots.txt")
            try:
                import requests
                r = requests.get(racine + "/robots.txt", headers={"User-Agent": AGENT}, timeout=10)
                regles.parse(r.text.splitlines() if r.status_code == 200 else [])
            except Exception:
                regles.parse([])                      # robots.txt injoignable : on suppose l'accès permis
            self.robots[racine] = regles
        return self.robots[racine].can_fetch(AGENT, url)

    def visiter(self, url, params=None):
        """Renvoie le texte brut de la réponse, ou lève ErreurBroutage (interdit, au repos, erreur)."""
        import requests
        adresse_publique(url)
        site = urlparse(url).netloc
        if time.time() < self.repos_jusqua.get(site, 0):
            raise ErreurBroutage(f"{site} est au repos (trop de visites récentes).")
        if not self.autorise(url):
            raise ErreurBroutage(f"robots.txt de {site} interdit cette page à IA AISSA.")
        regles = self.robots.get(f"{urlparse(url).scheme}://{site}")
        demande = (regles.crawl_delay(AGENT) if regles else None) or 0      # le délai que le site demande, s'il en fixe un
        attente = max(random.uniform(*self.delai), float(demande)) - (time.time() - self.derniere_visite.get(site, 0))
        if attente > 0:
            self.dormir(attente)                       # politesse : 2 à 5 s entre deux visites d'un même site
        r = requests.get(url, params=params, headers={"User-Agent": AGENT}, timeout=20)
        self.derniere_visite[site] = time.time()
        if r.status_code == 429:
            try:
                repos = int(r.headers.get("Retry-After", self.repos_429))
            except ValueError:
                repos = self.repos_429
            self.repos_jusqua[site] = time.time() + repos
            raise ErreurBroutage(f"{site} demande de ralentir (429) : repos de {repos} s.")
        if r.status_code in (401, 403):
            raise ErreurBroutage(f"{site} refuse l'accès aux robots ({r.status_code}) : IA AISSA cherche ailleurs.")
        r.raise_for_status()
        return r.text

    def telecharger(self, url, chemin, max_octets=70_000_000):
        """Télécharge un fichier (PDF, EPUB) vers le disque, par morceaux, avec les mêmes règles de politesse ;
        refuse au-delà de max_octets (70 Mo) pour ménager le serveur. Renvoie le nombre d'octets."""
        import requests
        adresse_publique(url)
        site = urlparse(url).netloc
        if time.time() < self.repos_jusqua.get(site, 0):
            raise ErreurBroutage(f"{site} est au repos (trop de visites récentes).")
        if not self.autorise(url):
            raise ErreurBroutage(f"robots.txt de {site} interdit ce fichier à IA AISSA.")
        attente = random.uniform(*self.delai) - (time.time() - self.derniere_visite.get(site, 0))
        if attente > 0:
            self.dormir(attente)
        with requests.get(url, headers={"User-Agent": AGENT}, timeout=60, stream=True) as r:
            self.derniere_visite[site] = time.time()
            if r.status_code in (401, 403):
                raise ErreurBroutage(f"{site} refuse l'accès aux robots ({r.status_code}) : IA AISSA cherche ailleurs.")
            r.raise_for_status()
            if int(r.headers.get("content-length") or 0) > max_octets:
                raise ErreurBroutage(f"fichier trop lourd ({int(r.headers['content-length']) / 1e6:.0f} Mo).")
            total = 0
            with open(chemin, "wb") as f:
                for morceau in r.iter_content(1 << 20):
                    total += len(morceau)
                    if total > max_octets:
                        raise ErreurBroutage("fichier trop lourd : téléchargement arrêté.")
                    f.write(morceau)
        return total

    def page(self, url):
        _, texte = texte_html(self.visiter(url))
        return texte[:TAILLE_MAX_PAGE]

    def wikipedia(self, sujet, langue="fr"):
        """L'article lui-même (/wiki/Titre), seule partie de Wikipédia que son robots.txt ouvre aux robots :
        son API et sa recherche leur sont fermées, et IA AISSA respecte cette règle."""
        from urllib.parse import quote
        titre = sujet.strip()
        titre = titre[:1].upper() + titre[1:]
        url = f"https://{langue}.wikipedia.org/wiki/{quote(titre.replace(' ', '_'))}"
        try:
            _, texte = texte_html(self.visiter(url))
        except ErreurBroutage:
            raise
        except Exception as e:
            raise ErreurBroutage(f"Pas d'article Wikipédia « {titre} » ({type(e).__name__}).") from e
        utiles = [l for l in texte.splitlines() if not l.startswith(BANDEAUX)]
        return f"Wikipédia — {titre}", "\n".join(utiles)[:TAILLE_MAX_PAGE]

    def arxiv(self, sujet, n=3):
        flux = self.visiter("https://export.arxiv.org/api/query",
                            {"search_query": f"all:{sujet}", "max_results": n})
        ns = {"a": "http://www.w3.org/2005/Atom"}
        articles = [(e.findtext("a:title", "", ns).strip(), e.findtext("a:summary", "", ns).strip())
                    for e in ET.fromstring(flux).findall("a:entry", ns)]
        if not articles:
            raise ErreurBroutage(f"Rien sur arXiv pour « {sujet} ».")
        texte = "\n\n".join(f"{t}. {r}" for t, r in articles)[:TAILLE_MAX_PAGE]
        return f"arXiv — {articles[0][0][:80]}", texte


def choisir_sujet(memoire, rng=random):
    """D'abord une lacune ouverte (ce qu'IA AISSA ne sait pas), sinon un sujet du programme, au hasard."""
    lacunes = memoire.lacunes_ouvertes(5)
    if lacunes:
        return lacunes[0]["question"], None
    famille = rng.choice(list(SUJETS))
    return rng.choice(SUJETS[famille]), famille


def cycle(memoire, moteur_config, client, brouteur=None, rng=random):
    """Un repas : un sujet, une source ouverte, une rumination, et les analogies injectées dans la galerie."""
    brouteur = brouteur or Brouteur()
    sujet, famille = choisir_sujet(memoire, rng)
    try:
        if famille in ("Sciences formelles", "Sciences naturelles") and rng.random() < 0.5:
            source, texte = brouteur.arxiv(sujet)
        else:
            source, texte = brouteur.wikipedia(sujet)
    except ErreurBroutage:
        if famille is None:                    # une lacune sans article à son nom : un sujet du programme
            famille = rng.choice(list(SUJETS))
            sujet = rng.choice(SUJETS[famille])
        source, texte = brouteur.wikipedia(sujet)
    from .autodidacte import SEUIL_PERTINENCE, analogies_mathematiques, mettre_en_quarantaine, pertinence_programme
    taux = pertinence_programme(texte)
    if taux < SEUIL_PERTINENCE:                     # hors de son programme : en quarantaine, pas digéré
        mettre_en_quarantaine(memoire, source, sujet, taux)
        return {"source": source, "sujet": sujet, "concepts": 0, "injections": 0, "quarantaine": taux,
                "digestions": [], "pratique": None}
    bilan = digerer(memoire, moteur_config, client, source, texte, nb_bouchees=1, famille=famille)
    bilan["pertinence"] = taux
    if famille:                                     # un sujet de son programme : elle connaît sa famille
        from .autodidacte import apprendre_du_programme
        from .corrections import reviser
        if apprendre_du_programme(memoire, sujet, famille):
            bilan["revisions"] = (bilan.get("revisions") or []) + [reviser(memoire, "familles_sciences")]
    injections = 0
    for d in bilan["digestions"]:                    # invention : chaque concept relié au contrôle de gestion
        if d["analogie"]:
            concepts = ", ".join(c["nom"] for c in d["concepts"][:3])
            memoire.garder_idee("IA AISSA", f"Allocation des ressources inspirée de : {concepts}",
                                f"Analogie : {concepts} × contrôle de gestion", d["analogie"],
                                d["confiance"], 0.0, f'{{"source": "{source}"}}')
            injections += 1
    if source.startswith("Wikipédia") and bilan["concepts"]:     # pollinisation croisée : 3 analogies mathématiques
        injections += analogies_mathematiques(memoire, source.split("—", 1)[-1].strip(), source)
    bilan.update(sujet=sujet, injections=injections)
    try:                                            # hygiène : compresser la bibliothèque si elle devient dense
        from .pensee import elaguer
        bilan["elagage"] = elaguer(memoire)
    except Exception:
        pass
    try:                                            # puis une séance de pratique délibérée dans une matière
        from .autodidacte import pratiquer
        from .corrections import reviser_tout
        bilan["pratique"] = pratiquer(memoire)
        bilan["revisions"] = (bilan.get("revisions") or []) + reviser_tout(memoire)   # ce qu'elle a appris d'elle-même
    except Exception as e:
        bilan["pratique"] = {"erreur": str(e)[:120]}
    return bilan


def demarrer(memoire, moteur_config, fabrique_client, par_jour=6):
    """Lance le travailleur d'arrière-plan (un seul par serveur). Il dort entre deux repas pour respecter
    le budget quotidien ; une erreur n'arrête jamais la boucle."""
    if ETAT["actif"]:
        return ETAT
    ETAT["actif"] = True
    intervalle = 86_400 / max(1, par_jour)

    def boucle():
        brouteur = Brouteur()
        time.sleep(120)                 # laisse l'application démarrer tranquillement avant le premier repas
        prochain_repas = derniere_crise = 0.0
        dernier_livre = time.time() - 86_400 + 900      # premier livre un quart d'heure après le démarrage
        while True:
            maintenant = time.time()
            jour = datetime.now(timezone.utc).date()
            if ETAT["jour"] != jour:
                ETAT.update(jour=jour, repas_du_jour=0)
            if maintenant - derniere_crise >= 3600:     # 5 crises synthétiques par heure
                derniere_crise = maintenant
                try:
                    from .autodidacte import resoudre_crises
                    bilan = resoudre_crises(memoire)
                    total = ETAT.setdefault("crises", {"resolues": 0, "justes": 0})
                    total["resolues"] += bilan["crises"]
                    total["justes"] += bilan["justes"]
                    total["derniere"] = bilan
                except Exception as e:
                    ETAT["erreurs"] = (ETAT["erreurs"] + [f"crises — {type(e).__name__} : {str(e)[:100]}"])[-5:]
            if maintenant >= prochain_repas and ETAT["repas_du_jour"] < par_jour:
                try:
                    bilan = cycle(memoire, moteur_config, fabrique_client(), brouteur)
                    ETAT["dernier_repas"] = {"quand": datetime.now(timezone.utc), "sujet": bilan["sujet"],
                                             "source": bilan["source"], "concepts": bilan["concepts"],
                                             "injections": bilan["injections"], "pratique": bilan.get("pratique"),
                                             "quarantaine": bilan.get("quarantaine")}
                    ETAT["repas_du_jour"] += 1
                    prochain_repas = time.time() + intervalle
                except Exception as e:                  # réseau, site au repos, moteur indisponible…
                    ETAT["erreurs"] = (ETAT["erreurs"] + [f"{type(e).__name__} : {str(e)[:120]}"])[-5:]
                    prochain_repas = time.time() + REESSAI   # retenté bientôt, sans entamer le budget
            if maintenant - dernier_livre >= 86_400:    # un manuel libre par jour (OpenStax…), si le site l'autorise
                dernier_livre = maintenant
                try:
                    from .livres_libres import repas_de_livre
                    livre = repas_de_livre(memoire, brouteur)
                    ETAT["dernier_livre"] = {"quand": datetime.now(timezone.utc), "source": livre["source"],
                                             "concepts": livre["concepts"], "refus": livre["refus"]}
                    from .lecture import examen_lecture
                    ETAT["examen_lecture"] = examen_lecture(memoire)        # chaque jour, elle s'examine
                except Exception as e:
                    ETAT["erreurs"] = (ETAT["erreurs"] + [f"livres — {type(e).__name__} : {str(e)[:100]}"])[-5:]
            try:                                       # rester sous le plafond de mémoire vive
                from .pensee import alleger
                ETAT["memoire_vive"] = alleger()
            except Exception:
                pass
            ETAT["prochain"] = prochain_repas
            time.sleep(max(60.0, min(prochain_repas, derniere_crise + 3600) - time.time()))

    threading.Thread(target=boucle, name="ia-aissa-broutage", daemon=True).start()
    return ETAT
