"""
IA AISSA autodidacte : elle développe seule ses connaissances et ses compétences, même sans clé API.

- Lire seule (rumination locale) : sans moteur, elle tire elle-même l'essentiel d'un texte (mots-clés les plus
  fréquents, phrases qui les portent) et range ces concepts dans sa bibliothèque, classés par son cerveau
  « Grandes familles de sciences ». Moins fine qu'avec un grand moteur, mais à elle.
- S'exercer seule (pratique délibérée) : elle choisit la matière où elle progresse le plus, s'entraîne un peu
  à partir de son cerveau actuel, et n'adopte le nouveau cerveau que s'il fait mieux à l'examen (règle de Dalio :
  jamais de régression).
- Apprendre de ses propres réponses (auto-apprentissage) : quand sa mémoire associative et ses cerveaux d'école
  sont d'accord et sûrs d'eux, la question devient un exemple de plus — elle apprend la façon dont on lui parle.
"""

import collections
import re

from . import ecole
from .ecole import PAR_CLE, examen, mots, precision, repondre

FAMILLES_DIGESTION = ["Sciences formelles", "Sciences naturelles", "Sciences humaines et gestion", "Sciences appliquées"]
VIDES = set("""le la les de des du un une et en au aux pour par sur dans avec sans sont est été être cette ces son sa
ses leur leurs qui que quoi dont plus moins aussi ainsi comme mais elle il ils elles nous vous on se ne pas ou où
entre après avant lors très tout tous toute toutes peut peuvent fait faire selon depuis deux trois premier première
the of and to in is are for with that this as by from on an be or which it its was were has have""".split())
SOURCE_AUTO = "auto-apprentissage"
SEUIL_AUTO = 0.9                # confiance minimale (et accord analogie × école) pour apprendre de soi-même
GAIN_MINIMAL = 0.005            # la pratique n'est adoptée que si l'examen progresse d'au moins 0,5 point


# ==========================================
# Lire seule
# ==========================================
def phrases(texte):
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", texte) if 40 <= len(p.strip()) <= 400]


def forme_originale(cle, texte):
    """Le mot tel qu'il est écrit dans le texte (avec ses accents) : « photosynthese » -> « Photosynthèse »."""
    for brut in re.findall(r"\w+", texte):
        if len(brut) == len(cle) and mots(brut) == [cle]:
            return brut[:1].upper() + brut[1:]
    return cle.capitalize()


def ruminer_local(morceau, source="", famille=None):
    """Rumination sans moteur : les mots-clés du texte et les phrases qui les portent le mieux.
    famille : la famille de sciences, si elle est déjà connue (sujet de son programme)."""
    frequences = collections.Counter(m for m in mots(morceau) if len(m) > 4 and m not in VIDES and not m.isdigit())
    cles = [m for m, n in frequences.most_common(12) if n >= 2]
    concepts, vus = [], set()
    for cle in cles:
        candidates = [p for p in phrases(morceau) if cle in mots(p) and p not in vus]
        if not candidates:
            continue
        meilleure = max(candidates, key=lambda p: sum(frequences[m] for m in set(mots(p)) if m in cles))
        vus.add(meilleure)
        concepts.append({"nom": forme_originale(cle, meilleure), "explication": meilleure[:300]})
        if len(concepts) == 5:
            break
    if famille not in FAMILLES_DIGESTION:
        titre = source.split("—", 1)[-1].strip()
        famille = repondre("familles_sciences", f"{titre} {' '.join(cles[:4])}", top=1)[0]["reponse"]
        famille = famille if famille in FAMILLES_DIGESTION else "Sciences humaines et gestion"
    return {"famille": famille, "concepts": concepts, "analogie": "",
            "confiance": round(min(0.6, 0.1 * len(concepts) + 0.1), 2)}


# ==========================================
# S'exercer seule
# ==========================================
def pratiquer(memoire, cle=None, pas=1500):
    """Une séance de pratique délibérée sur une matière (par défaut celle où elle progresse le plus)."""
    from .corrections import affiner
    from .croissance import vitesse_apprentissage
    if cle is None:
        vitesses = vitesse_apprentissage(memoire)
        candidates = [c for c in vitesses["matiere"] if c != "orientation"]
        if not candidates:
            return None
        cle = candidates[0]
    m = PAR_CLE[cle]
    exemples = [(l["question"], m.actions.index(l["bonne_reponse"])) for l in memoire.corrections_de(cle)
                if l["bonne_reponse"] in m.actions]
    ancien, nouveau, historique = affiner(cle, exemples, pas=pas, seed=len(historique_pratique(memoire)))
    epreuve = examen(m)
    avant, apres = precision(ancien, epreuve), precision(nouveau, epreuve)
    adoptee = apres >= avant + GAIN_MINIMAL
    if adoptee:
        ecole.sauvegarder(m, nouveau, (historique or []) + [{"pas": "pratique", "precision": apres}], revision=True)
    memoire.noter_revision(matiere=cle, nb_corrections=len(exemples), examen_avant=avant, examen_apres=apres,
                           corrections_avant=0.0, corrections_apres=0.0, adoptee=adoptee)
    return {"matiere": cle, "nom": m.nom, "avant": avant, "apres": apres, "adoptee": adoptee}


def historique_pratique(memoire):
    try:
        return memoire.revisions()
    except AttributeError:
        return []


# ==========================================
# Apprendre de ses propres réponses
# ==========================================
def apprendre_de_soi(memoire, question, conclusion):
    """Si analogie et école étaient d'accord et sûres, la question devient un exemple d'apprentissage."""
    from .corrections import valider_reponse
    if not conclusion or not conclusion.get("accord") or conclusion.get("confiance", 0) < SEUIL_AUTO:
        return False
    if not 6 <= len(question) <= 300 or conclusion["cle"] in ("orientation", "langues"):
        return False
    officielle = valider_reponse(conclusion["cle"], conclusion["reponse"])
    if officielle is None:
        return False
    # révisée en arrière-plan par le travailleur autonome, jamais pendant la conversation
    memoire.ajouter_correction("IA AISSA", conclusion["cle"], question, officielle, SOURCE_AUTO)
    return True


def apprendre_du_programme(memoire, sujet, famille):
    """Elle lit un sujet de son propre programme : elle en connaît la famille, elle s'en sert pour se corriger
    (son cerveau « Grandes familles de sciences » apprend « photosynthèse → Sciences naturelles »)."""
    reponse = {"Sciences humaines et gestion": "Sciences humaines et sociales"}.get(famille, famille)
    if reponse not in PAR_CLE["familles_sciences"].actions:
        return False
    if repondre("familles_sciences", sujet, top=1)[0]["reponse"] == reponse:
        return False                                  # elle le savait déjà
    memoire.ajouter_correction("IA AISSA", "familles_sciences", sujet, reponse, SOURCE_AUTO)   # pas l'aiguilleur :
    return True                                                                           # trop lourd à chaque repas
