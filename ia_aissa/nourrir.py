"""
Nourrir IA AISSA chaque jour : une fois par jour, elle prend une de ses lacunes (une question à laquelle elle n'a pas
su répondre), trouve l'article de Wikipédia qui y répond, le lit et le range dans sa mémoire de lecture. Elle vérifie
ensuite qu'elle sait y répondre en relisant : seulement alors la lacune est résolue.

Au plus un appel au grand moteur par jour (s'il y a une clé), pour transformer la question en titre d'article ;
sinon, les titres possibles sont tirés de la question elle-même. La lecture et la digestion se font sans moteur.
Wikipédia est lu par ses pages /wiki/, seules ouvertes aux robots par son robots.txt.
"""

import datetime
import json
import re
import threading

from .bibliotheque import ErreurBroutage, digerer

MOTS_VIDES = set("""quel quelle quels quelles qui que quoi qu est ce c comment combien pourquoi où ou quand le la les l un
une des du de d au aux et en dans sur pour par avec sans je tu il elle on nous vous ils elles mon ma mes ton ta tes son sa
ses notre votre leur leurs moi toi lui y a ai as ont sont suis es être avoir fait faire dis dire donne explique parle
moi peux veux sais sait connais svp stp merci bonjour salut est-ce qu'est que'est wach chno chnou kifach 3lach fin chkoun
dyal had bghit construit construire calcule calculer explique expliquer parle parler signifie veut faut existe
définition définis c'est qu'est-ce""".split())
_EN_COURS = threading.Lock()


def titres_candidats(question, n=4):
    """Titres d'article possibles, tirés de la question : d'abord les noms propres (mots à majuscule qui se suivent :
    « Ibn Khaldoun »), puis les groupes de mots porteurs de sens, du plus long au plus court."""
    mots = [m for brut in re.findall(r"[\wÀ-ÿ'-]+", question) for m in brut.split("-") if m]
    mots = [m.split("'")[-1] for m in mots]                   # l'article élidé : « l'Atlas » → « Atlas »
    propres, groupe = [], []
    for i, m in enumerate(mots + [""]):
        if m[:1].isupper() and m.lower() not in MOTS_VIDES:
            groupe.append(m)
        else:
            if groupe:
                propres.append(" ".join(groupe))
            groupe = []
    utiles = [m for m in mots if m.lower() not in MOTS_VIDES and len(m) > 2]
    candidats = propres[:]
    for taille in (3, 2, 1):
        candidats += [" ".join(utiles[i:i + taille]) for i in range(len(utiles) - taille + 1)]
    vus, titres = set(), []
    for t in candidats:
        if t.lower() not in vus and len(t) > 2:
            vus.add(t.lower())
            titres.append(t)
    return titres[:n]


def titre_par_moteur(moteur_config, client, question):
    """L'unique appel au grand moteur de la journée : le titre exact de l'article qui répond à la question."""
    from .autonomie import demander
    reponse = demander(moteur_config, client,
                       "Donne uniquement le titre exact de l'article de Wikipédia en français qui répond le mieux à "
                       f"cette question : « {question} ». Réponds par le titre seul, sans guillemets ni phrase.")
    titre = (reponse or "").strip().splitlines()[0].strip(" «»\"'.") if reponse else ""
    return titre[:100]


def nourrir_du_jour(memoire, moteur_config=None, client=None, brouteur=None, aujourdhui=None, forcer=False):
    """Un repas par jour, tiré de ses lacunes. Renvoie le bilan (déjà fait aujourd'hui : le bilan du jour)."""
    jour = (aujourdhui or datetime.date.today()).isoformat()
    deja = memoire.reglage(f"nourri:{jour}")
    if deja and not forcer:
        return {**json.loads(deja), "deja": True}
    if brouteur is None:
        from .broutage import Brouteur
        brouteur = Brouteur()
    from .lecture import decouper, repondre_par_lecture
    moteur_utilise, essais = False, []
    for lacune in memoire.lacunes_ouvertes(10):
        question = lacune["question"]
        titres = []
        if client is not None and not moteur_utilise:
            moteur_utilise = True
            try:
                titres.append(titre_par_moteur(moteur_config, client, question))
            except Exception as e:                      # moteur indisponible : les titres tirés de la question
                essais.append(f"moteur : {type(e).__name__}")
        titres += titres_candidats(question)
        for titre in [t for i, t in enumerate(titres) if t and t not in titres[:i]][:5]:
            try:
                source, texte = brouteur.wikipedia(titre)
            except (ErreurBroutage, Exception) as e:
                essais.append(f"{titre} : {str(e)[:80]}")
                continue
            if len(texte.strip()) < 200:
                essais.append(f"{titre} : article trop court")
                continue
            memoire.garder_passages("IA AISSA", source, decouper(texte))   # elle pourra retrouver la réponse
            bilan = digerer(memoire, None, None, source, texte, "IA AISSA", nb_bouchees=2)
            resolue = repondre_par_lecture(question, memoire) is not None
            if resolue:
                memoire.resoudre_lacune(lacune["id"])
            resultat = {"date": jour, "lacune": question, "source": source, "concepts": bilan["concepts"],
                        "resolue": resolue, "moteur_utilise": moteur_utilise, "essais": essais[-5:]}
            memoire.definir_reglage(f"nourri:{jour}", json.dumps(resultat, ensure_ascii=False))
            return resultat
    resultat = {"date": jour, "lacune": None, "source": None, "concepts": 0, "resolue": False,
                "moteur_utilise": moteur_utilise, "essais": essais[-5:]}
    memoire.definir_reglage(f"nourri:{jour}", json.dumps(resultat, ensure_ascii=False))
    return resultat


def nourrir_en_arriere_plan(memoire, moteur_config=None, fabrique_client=lambda: None):
    """À chaque visite : lance le repas du jour en arrière-plan s'il n'a pas eu lieu (la page n'attend pas)."""
    if memoire.reglage(f"nourri:{datetime.date.today().isoformat()}") or not _EN_COURS.acquire(blocking=False):
        return False

    def repas():
        try:
            nourrir_du_jour(memoire, moteur_config, fabrique_client())
        except Exception:
            pass
        try:                                            # et, une fois par semaine, les données ouvertes à jour
            from .donnees_ouvertes import repas_donnees_ouvertes
            repas_donnees_ouvertes(memoire)
        except Exception:
            pass
        finally:
            _EN_COURS.release()
    threading.Thread(target=repas, daemon=True, name="ia-aissa-repas-du-jour").start()
    return True


def historique(memoire, n=30):
    return sorted((json.loads(v) for v in memoire.reglages("nourri:").values()), key=lambda r: r["date"], reverse=True)[:n]
