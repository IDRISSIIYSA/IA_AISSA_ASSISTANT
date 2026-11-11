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


PREFIXE_SUITE = "lacune_suite:"
LIENS_GARDES = 5


def liens_utiles(question, liens, n=LIENS_GARDES):
    """Les articles liés les plus proches de la question : d'abord ceux dont le titre partage des mots porteurs de
    sens avec elle, puis l'ordre de la page (les premiers liens d'un article sont les plus centraux)."""
    import unicodedata

    def mots_de(t):
        t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
        return {m for m in re.findall(r"[a-z0-9]+", t) if len(m) > 2 and m not in MOTS_VIDES}
    q = mots_de(question)
    classes = sorted(enumerate(liens), key=lambda e: (-len(q & mots_de(e[1])), e[0]))
    return [titre for _, titre in classes[:n]]


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

    def manger(lacune, source, texte):
        memoire.garder_passages("IA AISSA", source, decouper(texte))   # elle pourra retrouver la réponse
        bilan = digerer(memoire, None, None, source, texte, "IA AISSA", nb_bouchees=2, combler=False)
        resolue = repondre_par_lecture(lacune["question"], memoire) is not None
        if resolue:
            memoire.resoudre_lacune(lacune["id"])
        return bilan, resolue

    def conclure(resultat):
        memoire.definir_reglage(f"nourri:{jour}", json.dumps(resultat, ensure_ascii=False))
        return resultat

    # 1. Une lacune qu'un article n'a pas suffi à résoudre : le lendemain, un article lié de cette page
    ouvertes = {l["id"]: l for l in memoire.lacunes_ouvertes(50)}
    for cle, brut in sorted(memoire.reglages(PREFIXE_SUITE).items()):
        suite = json.loads(brut)
        lacune = ouvertes.get(int(cle[len(PREFIXE_SUITE):]))
        if lacune is None or not suite["liens"]:
            continue
        titre = suite["liens"].pop(0)
        suite["essayes"] = suite.get("essayes", []) + [titre]
        suite["epuise"] = not suite["liens"]
        memoire.definir_reglage(cle, json.dumps(suite, ensure_ascii=False))
        try:
            source, texte = brouteur.wikipedia(titre)
        except (ErreurBroutage, Exception) as e:
            essais.append(f"{titre} (article lié) : {str(e)[:80]}")
            break
        bilan, resolue = manger(lacune, source, texte)
        return conclure({"date": jour, "lacune": lacune["question"], "source": source, "concepts": bilan["concepts"],
                         "resolue": resolue, "moteur_utilise": False, "essais": essais[-5:],
                         "article_lie": f"lié depuis « {suite['depuis']} »"})

    # 2. Sinon, une lacune nouvelle (celles dont les articles liés sont épuisés passent après les autres)
    epuisees = {int(k[len(PREFIXE_SUITE):]) for k, v in memoire.reglages(PREFIXE_SUITE).items()
                if json.loads(v).get("epuise")}
    for lacune in sorted(memoire.lacunes_ouvertes(10), key=lambda l: l["id"] in epuisees):
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
                if hasattr(brouteur, "wikipedia_et_liens"):
                    source, texte, liens = brouteur.wikipedia_et_liens(titre)
                else:
                    (source, texte), liens = brouteur.wikipedia(titre), []
            except (ErreurBroutage, Exception) as e:
                essais.append(f"{titre} : {str(e)[:80]}")
                continue
            if len(texte.strip()) < 200:
                essais.append(f"{titre} : article trop court")
                continue
            bilan, resolue = manger(lacune, source, texte)
            if not resolue and liens:          # demain : un article lié, choisi d'après les mots de la question
                memoire.definir_reglage(f"{PREFIXE_SUITE}{lacune['id']}", json.dumps(
                    {"depuis": titre, "liens": liens_utiles(question, liens), "essayes": [], "epuise": False},
                    ensure_ascii=False))
            return conclure({"date": jour, "lacune": question, "source": source, "concepts": bilan["concepts"],
                             "resolue": resolue, "moteur_utilise": moteur_utilise, "essais": essais[-5:]})
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
        try:                                            # et les données officielles marocaines (data.gov.ma)
            from .donnees_maroc import repas_donnees_maroc
            repas_donnees_maroc(memoire)
        except Exception:
            pass
        finally:
            _EN_COURS.release()
    threading.Thread(target=repas, daemon=True, name="ia-aissa-repas-du-jour").start()
    return True


def historique(memoire, n=30):
    return sorted((json.loads(v) for v in memoire.reglages("nourri:").values()), key=lambda r: r["date"], reverse=True)[:n]
