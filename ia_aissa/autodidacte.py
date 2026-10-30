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


# ==========================================
# Quarantaine thématique : ne digérer que ce qui touche son programme
# ==========================================
SEUIL_PERTINENCE = 0.15         # part minimale des mots-clés du texte présents dans le vocabulaire du programme
_VOCABULAIRE = {}


def vocabulaire_programme():
    """Les mots de ses 74 matières (noms, notes, réponses, formulations) et des sujets de broutage."""
    if not _VOCABULAIRE:
        from . import connaissances as K
        from .broutage import SUJETS
        textes = [f"{m.nom} {m.domaine} {m.note} {' '.join(m.actions)}" for m in PAR_CLE.values()]
        textes += [f for m in PAR_CLE.values() if m.exemples for formes in m.exemples for f in formes]
        textes += [s for sujets in SUJETS.values() for s in sujets]
        textes += [f for formes in K.FAMILLES_SCIENCES.values() for f in formes]
        _VOCABULAIRE["mots"] = {m for t in textes for m in mots(t) if len(m) > 4 and m not in VIDES}
    return _VOCABULAIRE["mots"]


def pertinence_programme(texte, n=30):
    """Part des 30 mots-clés du texte (mots de plus de 4 lettres) qui appartiennent au vocabulaire du programme."""
    frequences = collections.Counter(m for m in mots(texte) if len(m) > 4 and m not in VIDES and not m.isdigit())
    cles = [m for m, _ in frequences.most_common(n)]
    if not cles:
        return 0.0
    vocabulaire = vocabulaire_programme()
    return round(sum(c in vocabulaire for c in cles) / len(cles), 3)


def mettre_en_quarantaine(memoire, source, sujet, taux):
    import json
    import time
    memoire.definir_reglage(f"quarantaine:{int(time.time() * 1000)}",
                            json.dumps({"source": source, "sujet": sujet, "pertinence": taux}, ensure_ascii=False))


def quarantaine(memoire):
    import json
    return [json.loads(v) for _, v in sorted(memoire.reglages("quarantaine:").items())]


# ==========================================
# Rumination récursive : sous 75 % de confiance, trois autres façons de digérer
# ==========================================
SEUIL_ASSIMILATION = 0.75


def ruminer_recursif(texte, morceau, source="", famille=None):
    """Rumine le morceau ; si la confiance est sous 75 %, essaie aussitôt trois reformulations internes
    (un autre passage du texte, le texte entier, et les mots-clés de tout le texte appliqués au morceau)
    et garde la meilleure digestion. Renvoie (digestion, nombre d'essais)."""
    essais = [ruminer_local(morceau, source, famille)]
    if essais[0]["confiance"] < SEUIL_ASSIMILATION:
        milieu = len(texte) // 2
        alternatives = [texte[milieu:milieu + len(morceau)], texte[:3 * len(morceau)], morceau + "\n" + texte[:1500]]
        essais += [ruminer_local(a, source, famille) for a in alternatives if len(a.strip()) > 200]
    meilleure = max(essais, key=lambda d: (d["confiance"], len(d["concepts"])))
    return meilleure, len(essais)


# ==========================================
# Pollinisation croisée : trois analogies mathématiques avec le contrôle de gestion
# ==========================================
GABARITS_ANALOGIES = [
    ("Écart relatif", "Mesurer « {c} » comme un écart budgétaire : e = (réel − prévu) / prévu ; "
                      "alerte au-delà de |e| > 10 %, analyse de la cause dès |e| > 5 %."),
    ("Conservation stock-flux", "Bilan de « {c} » : stock final = stock initial + entrées − sorties, la même "
                                "équation que la trésorerie (solde final = solde initial + encaissements − décaissements)."),
    ("Régulation par rétroaction", "Piloter « {c} » par rétroaction : correction(t) = k × écart(t), avec 0 < k < 1 ; "
                                   "l'écart décroît comme (1 − k)^t, comme une action corrective budgétaire répétée."),
]


def analogies_mathematiques(memoire, concept, source):
    """Trois analogies par gabarit (à valider : confiance 0,3), gardées dans la galerie d'inventions."""
    import json
    for titre, gabarit in GABARITS_ANALOGIES:
        memoire.garder_idee("IA AISSA", f"Contrôle de gestion × {concept}", f"{titre} : {concept}",
                            gabarit.format(c=concept), 0.3, 0.0,
                            json.dumps({"source": source, "type": "analogie mathématique (gabarit)"}, ensure_ascii=False))
    return len(GABARITS_ANALOGIES)


# ==========================================
# Crises financières synthétiques (contexte marocain) : s'entraîner sans qu'on lui demande
# ==========================================
SECTEURS = ["Textile Fès", "Agroalimentaire Agadir", "Tech Casablanca", "Automobile Tanger", "Phosphates Khouribga",
            "Tourisme Marrakech", "Pêche Dakhla", "BTP Rabat"]
CRISES_PAR_HEURE = 5


def generer_crise(rng):
    """Une crise budgétaire synthétique : la moitié du temps une dérive grave (+25 à +60 %), sinon un mois plus
    calme, pour qu'elle apprenne aussi à ne pas crier au loup."""
    prevu = float(rng.uniform(500_000, 2_000_000))
    facteur = float(rng.uniform(1.25, 1.60)) if rng.random() < 0.5 else float(rng.normal(1.03, 0.06))
    tendance = float(rng.normal(0, 0.03))
    return {"secteur": SECTEURS[int(rng.integers(len(SECTEURS)))], "prevu": prevu, "reel": prevu * facteur,
            "ecart_pct": facteur - 1, "tendance": tendance}


def resoudre_crises(memoire, n=CRISES_PAR_HEURE, rng=None):
    """Elle résout n crises avec son propre cerveau « pilotage des écarts », se corrige avec la règle du contrôleur
    (classer_situation), et, si elle s'est trompée, s'exerce aussitôt sur cette matière (adopté seulement si
    l'examen progresse). Renvoie le bilan réel : crises, justes, pratique."""
    import json
    import time

    import numpy as np
    from controle_gestion_ia import DECISION_IDEALE, classer_situation
    rng = rng or np.random.default_rng()
    justes, details = 0, []
    for _ in range(n):
        c = generer_crise(rng)
        x = np.array([c["ecart_pct"] * 5, c["tendance"] * 20], np.float32)
        choix = repondre("controle_gestion", x, top=1)[0]
        attendu = PAR_CLE["controle_gestion"].actions[DECISION_IDEALE[classer_situation(c)]]
        juste = choix["reponse"] == attendu
        justes += juste
        details.append({**{k: round(v, 4) if isinstance(v, float) else v for k, v in c.items()},
                        "decision": choix["reponse"], "attendu": attendu, "juste": juste})
    memoire.definir_reglage(f"crises:{int(time.time() * 1000)}", json.dumps(details, ensure_ascii=False))
    bilan = {"crises": n, "justes": justes, "pratique": None}
    if justes < n:
        bilan["pratique"] = pratiquer(memoire, cle="controle_gestion", pas=800)
    return bilan
