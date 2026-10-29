"""
Apprentissage par les corrections : IA AISSA progresse d'elle-même au fil des conversations.

1. Quand l'assistante (ou l'utilisateur) constate qu'un cerveau d'école s'est trompé, la bonne réponse
   est enregistrée comme correction. Si la matière elle-même avait été mal devinée, l'aiguilleur reçoit
   aussi sa correction.
2. Révision : le cerveau repart de son état actuel (rien n'est oublié) et s'entraîne, toujours par essais
   et récompenses, sur un mélange de ses exercices habituels et de ses corrections, légèrement reformulées.
3. Règle de Dalio : après révision, IA AISSA repasse son examen habituel. Si elle a régressé (plus de 2 points
   depuis la dernière révision, ou plus de 3 points sous sa note d'école), elle refuse le nouveau cerveau et
   garde l'ancien ; ses corrections restent en attente pour la prochaine révision.
"""

import copy
import random
import unicodedata
from collections import deque

import numpy as np
import torch
import torch.nn as nn

from . import ecole
from .ecole import BRUIT, PAR_CLE, PREFIXES, examen, precision

ORIENTATION = "orientation"
TOLERANCE_EXAMEN = 0.02          # régression maximale acceptée à l'examen habituel, révision après révision
PLANCHER_EXAMEN = 0.03           # et jamais plus de 3 points sous la note obtenue à l'école


def brancher(memoire):
    """Les cerveaux révisés sont lus et écrits dans la mémoire durable. Si un cerveau d'origine a changé
    (nouvelle version de l'école), sa révision périmée est oubliée et ses corrections seront réapprises."""
    ecole.STOCKAGE = memoire
    ecole._CACHE.clear()
    for cle in memoire.matieres_revisees():
        if cle in PAR_CLE and ecole.revision_valide(cle) is None:
            memoire.oublier_cerveau(cle)
            memoire.marquer_non_apprises(cle)


def _cle(texte):
    t = "".join(c for c in unicodedata.normalize("NFD", str(texte).lower()) if unicodedata.category(c) != "Mn")
    return " ".join(t.split())


def valider_reponse(cle, reponse):
    """Retrouve la réponse officielle de la matière (« 2355 », « kant », « pile »… suffisent)."""
    actions = PAR_CLE[cle].actions
    r = _cle(reponse)
    exactes = [a for a in actions if _cle(a) == r]
    if exactes:
        return exactes[0]
    proches = [a for a in actions if _cle(a).startswith(r) or r.startswith(_cle(a)) or (len(r) >= 3 and r in _cle(a))]
    return proches[0] if len(proches) == 1 else None


def corriger(memoire, utilisateur, cle, question, bonne_reponse, source="assistante"):
    m = PAR_CLE.get(cle)
    if m is None or not m.texte or cle == ORIENTATION:
        raise ValueError(f"Matière inconnue ou non textuelle : {cle}")
    officielle = valider_reponse(cle, bonne_reponse)
    if officielle is None:
        raise ValueError(f"« {bonne_reponse} » n'est pas une réponse possible en {m.nom}. "
                         f"Réponses possibles : {', '.join(m.actions)}")
    memoire.ajouter_correction(utilisateur, cle, question, officielle, source)
    if cle in PAR_CLE[ORIENTATION].actions:
        memoire.ajouter_correction(utilisateur, ORIENTATION, question, cle, source)
    return {"corrige": True, "matiere": m.nom, "bonne_reponse": officielle}


def _reformuler(rng, question):
    mots = question.split()
    if len(mots) > 3 and rng.random() < 0.3:
        del mots[int(rng.integers(len(mots)))]
    return PREFIXES[int(rng.integers(len(PREFIXES)))] + " ".join(mots) + BRUIT[int(rng.integers(len(BRUIT)))]


def _justesse(cerveau, m, exemples):
    if not exemples:
        return 1.0
    x = torch.tensor(np.array([m.perception(q) for q, _ in exemples]))
    y = np.array([y for _, y in exemples])
    with torch.no_grad():
        return float((cerveau(x).argmax(1).numpy() == y).mean())


def affiner(cle, exemples, pas=None, part_corrections=None, lr=None, seed=0):
    """Révision par renforcement à partir du cerveau actuel. exemples : [(question, index de la bonne réponse)]."""
    m = PAR_CLE[cle]
    ancien, historique = ecole.charger(cle)
    cerveau = copy.deepcopy(ancien)
    cerveau.train()
    pas = pas or (10_000 if cle == ORIENTATION else 3500)
    # peu de corrections = petite place dans les exercices, pour ne pas déséquilibrer ce qui est déjà su
    part_corrections = part_corrections or min(0.4, 0.1 + 0.03 * len(exemples))
    lr = lr or (5e-4 if cle == ORIENTATION else 1e-3)
    rng, alea = np.random.default_rng(seed), random.Random(seed)
    torch.manual_seed(seed)
    optimiseur = torch.optim.Adam(cerveau.parameters(), lr=lr)
    memoire, batch = deque(maxlen=20_000), 64
    for _ in range(pas):
        if exemples and rng.random() < part_corrections:
            question, y = exemples[int(rng.integers(len(exemples)))]
            x = m.perception(_reformuler(rng, question))
        else:
            x, y, _ = m.generer(rng)
        if alea.random() < 0.1:
            action = alea.randrange(len(m.actions))
        else:
            with torch.no_grad():
                action = int(cerveau(torch.from_numpy(x)).argmax())
        memoire.append((x, action, 1.0 if action == y else -1.0))
        if len(memoire) >= batch:
            s, a, r = zip(*alea.sample(memoire, batch))
            prediction = cerveau(torch.tensor(np.array(s))).gather(1, torch.tensor(a).unsqueeze(1)).squeeze(1)
            perte = nn.functional.mse_loss(prediction, torch.tensor(r))
            optimiseur.zero_grad()
            perte.backward()
            optimiseur.step()
    cerveau.eval()
    return ancien, cerveau, historique


def reviser(memoire, cle):
    """Révise une matière avec toutes ses corrections ; adopte le nouveau cerveau seulement s'il ne régresse pas."""
    m = PAR_CLE[cle]
    lignes = memoire.corrections_de(cle)
    exemples = [(l["question"], m.actions.index(l["bonne_reponse"])) for l in lignes if l["bonne_reponse"] in m.actions]
    if not exemples:
        return None
    ancien, nouveau, historique = affiner(cle, exemples)
    epreuve = examen(m)
    bilan = {"matiere": cle, "nb_corrections": len(exemples),
             "examen_avant": precision(ancien, epreuve), "examen_apres": precision(nouveau, epreuve),
             "corrections_avant": _justesse(ancien, m, exemples), "corrections_apres": _justesse(nouveau, m, exemples)}
    note_ecole = next((h["precision"] for h in reversed(historique or []) if isinstance(h["pas"], int)),
                      bilan["examen_avant"])
    bilan["adoptee"] = (bilan["examen_apres"] >= bilan["examen_avant"] - TOLERANCE_EXAMEN
                        and bilan["examen_apres"] >= note_ecole - PLANCHER_EXAMEN
                        and bilan["corrections_apres"] >= bilan["corrections_avant"])
    if bilan["adoptee"]:
        ecole.sauvegarder(m, nouveau, (historique or []) + [{"pas": "révision", "precision": bilan["examen_apres"]}],
                          revision=True)
        memoire.marquer_apprises(cle)
    memoire.noter_revision(**bilan)
    return bilan


def reviser_tout(memoire):
    """Révise chaque matière qui a reçu de nouvelles corrections (l'aiguilleur en dernier)."""
    a_reviser = sorted({l["matiere"] for l in memoire.corrections_de(seulement_nouvelles=True)},
                       key=lambda c: c == ORIENTATION)
    return [b for b in (reviser(memoire, cle) for cle in a_reviser) if b]
