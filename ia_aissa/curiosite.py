"""
Curiosité d'IA AISSA : une récompense intrinsèque qui la pousse à apprendre là où elle est la plus faible.

1. Faiblesse : elle examine ses cerveaux d'école (dernière note d'examen) et ses lacunes ouvertes, matière par
   matière, et choisit les plus faibles. Une matière déjà nourrie par la curiosité dans les 7 derniers jours
   passe après les autres, pour qu'elle explore au lieu de tourner en rond.
2. Broutage : pour chaque matière choisie, elle lit l'article Wikipédia et les résumés des articles scientifiques
   en libre accès les plus cités (OpenAlex), puis les rumine comme n'importe quelle lecture.
3. Récompense : la nouveauté de ce qu'elle a digéré (1 − proximité avec ce que sa bibliothèque savait déjà).
   Un cycle qui n'apprend que du déjà-vu rapporte presque zéro ; un cycle qui ouvre un territoire rapporte gros.

Aucun code n'est modifié : ce qu'elle apprend va dans sa mémoire durable (concepts, corrections, cerveaux révisés).
"""

import json
from datetime import datetime, timedelta, timezone

import numpy as np

from . import bibliotheque as B
from .autonomie import MATIERES_ETUDIABLES
from .ecole import charger, vectoriser_mixte

PREFIXE = "Curiosité"
FENETRE = timedelta(days=7)


def _date(valeur):
    d = valeur if isinstance(valeur, datetime) else datetime.fromisoformat(str(valeur))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def matieres_faibles(memoire, n=2):
    """Les n matières les plus faibles : (1 − dernière note) + 0,1 par lacune ouverte − 0,5 si déjà explorée
    récemment par curiosité. Renvoie [{"cle", "nom", "note", "lacunes", "faiblesse"}], la plus faible d'abord."""
    lacunes = {}
    for l in memoire.lacunes_ouvertes(500):
        lacunes[l["matiere_devinee"]] = lacunes.get(l["matiere_devinee"], 0) + 1
    limite = datetime.now(timezone.utc) - FENETRE
    recentes = " ".join(d["source"] for d in memoire.digestions()
                        if d["source"].startswith(PREFIXE) and _date(d["cree_le"]) > limite)
    classement = []
    for m in MATIERES_ETUDIABLES:
        _, historique = charger(m.cle)
        notes = [h["precision"] for h in historique or [] if isinstance(h.get("pas"), int)]
        note = notes[-1] if notes else 0.0
        faiblesse = (1 - note) + 0.1 * lacunes.get(m.cle, 0) - (0.5 if f"({m.nom})" in recentes else 0)
        classement.append({"cle": m.cle, "nom": m.nom, "note": round(note, 3), "lacunes": lacunes.get(m.cle, 0),
                           "faiblesse": round(faiblesse, 3)})
    return sorted(classement, key=lambda x: -x["faiblesse"])[:n]


def _vecteurs_bibliotheque(memoire):
    return [vectoriser_mixte(f"{c['nom']} {c.get('explication', '')}")
            for d in memoire.digestions() for c in json.loads(d["concepts"])]


def recompense(connus, concepts):
    """Nouveauté moyenne des concepts digérés (0 = tout était déjà connu, 1 = entièrement nouveau)."""
    if not concepts:
        return 0.0
    if not connus:
        return 1.0
    connus = np.stack(connus)
    nouveautes = [1 - float(np.max(connus @ vectoriser_mixte(f"{c['nom']} {c.get('explication', '')}")))
                  for c in concepts]
    return round(float(np.clip(np.mean(nouveautes), 0, 1)), 3)


def cycle_curiosite(memoire, moteur, client, nb_matieres=2, sources=None):
    """Un cycle complet, sans personne : choisir les matières faibles, brouter, ruminer, mesurer la récompense."""
    sources = sources or [B.brouter_wikipedia, B.brouter_openalex]
    connus = _vecteurs_bibliotheque(memoire)
    bilan = {"matieres": [], "concepts": 0, "lacunes_comblees": 0, "exercices": 0, "erreurs": []}
    concepts = []
    for m in matieres_faibles(memoire, nb_matieres):
        lu = []
        for brouter in sources:
            try:
                titre, texte = brouter(m["nom"])
                b = B.digerer(memoire, moteur, client, f"{PREFIXE} ({m['nom']}) — {titre}", texte, nb_bouchees=2)
            except B.ErreurBroutage as e:
                bilan["erreurs"].append(f"{m['nom']} : {e}")
                continue
            concepts += [c for d in b["digestions"] for c in d["concepts"]]
            bilan["concepts"] += b["concepts"]
            bilan["lacunes_comblees"] += len(b["lacunes_comblees"])
            bilan["exercices"] += b["exercices"]
            lu.append(titre)
        bilan["matieres"].append({**m, "lu": lu})
    bilan["recompense"] = recompense(connus, concepts)
    return bilan
