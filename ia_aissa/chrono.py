"""
Le temps d'ouverture de chaque page, mesuré à chaque affichage (objectif : moins de 3 secondes).

Deux mesures distinctes :
- l'affichage d'une page : du début à la fin du script Streamlit pour cette page (ce que vit chaque visiteur) ;
- le démarrage à froid du serveur : de la naissance du processus à la fin du premier affichage (imports de PyTorch,
  pandas…, payé une seule fois quand Streamlit Cloud réveille l'application).

Les affichages qui préparent une réponse au visiteur (message envoyé) sont comptés à part (« — réponse ») : leur durée
est celle de la réflexion d'IA AISSA, pas celle de l'ouverture de la page.

Alerte : quand le 95e centile des ouvertures d'une page dépasse 3 s sur les dernières 24 heures (au moins 5 mesures).
Les mesures restent en mémoire du serveur (horodatées, au plus 2 000 par page) : rien n'est écrit en base à chaque
affichage.
"""

import os
import statistics
import threading
import time
from collections import deque

import pandas as pd

OBJECTIF_S = 3.0
GARDER = 2_000                  # par page : de quoi couvrir une journée chargée
FENETRE_ALERTE_S = 86_400       # une journée
MIN_MESURES_ALERTE = 5          # pas d'alerte sur une seule ouverture lente
SUFFIXE_REPONSE = " — réponse"
_MESURES = {}
_DEMARRAGE = {}
_COURANT = threading.local()    # le chronomètre de l'affichage en cours (un fil par session Streamlit)


def age_du_processus():
    """Secondes depuis la naissance du processus, lues dans /proc (Linux) ; None ailleurs."""
    try:
        with open("/proc/self/stat") as f:
            debut_ticks = int(f.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/uptime") as f:
            uptime = float(f.read().split()[0])
        return max(0.0, uptime - debut_ticks / os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        return None


def enregistrer(page, duree, quand=None):
    _MESURES.setdefault(page, deque(maxlen=GARDER)).append((quand or time.time(), float(duree)))
    if "secondes" not in _DEMARRAGE:                 # premier affichage depuis le démarrage du serveur
        age = age_du_processus()
        _DEMARRAGE.update(secondes=age, page=page)


class Chrono:
    """with Chrono("IA AISSA"): … — mesure l'affichage de la page, même si elle s'interrompt (rerun, switch_page)."""

    def __init__(self, page):
        self.page = page

    def __enter__(self):
        self.debut = time.perf_counter()
        self.reponse = False
        _COURANT.chrono = self
        return self

    def __exit__(self, *exc):
        _COURANT.chrono = None
        enregistrer(self.page + (SUFFIXE_REPONSE if self.reponse else ""), time.perf_counter() - self.debut)
        return False


def marquer_reponse():
    """Cet affichage prépare une réponse à un message : il est compté à part (pas dans l'ouverture de la page)."""
    chrono = getattr(_COURANT, "chrono", None)
    if chrono is not None:
        chrono.reponse = True


def centile_95(valeurs):
    v = sorted(valeurs)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def demarrage_a_froid():
    return _DEMARRAGE.get("secondes")


def tableau():
    """Par page : nombre d'affichages, médiane, 95e centile, maximum, et respect de l'objectif."""
    lignes = []
    for page, d in sorted(_MESURES.items()):
        v = sorted(duree for _, duree in d)
        p95 = centile_95(v)
        lignes.append({"Page": page, "Affichages mesurés": len(v), "Médiane (s)": round(statistics.median(v), 2),
                       "95e centile (s)": round(p95, 2), "Maximum (s)": round(v[-1], 2),
                       "Objectif < 3 s": "—" if page.endswith(SUFFIXE_REPONSE) else "✅" if p95 < OBJECTIF_S else "⚠️"})
    return pd.DataFrame(lignes)


def alertes(maintenant=None):
    """Pages dont le 95e centile d'ouverture dépasse l'objectif sur les dernières 24 heures (réponses exclues)."""
    maintenant = maintenant or time.time()
    messages = []
    for page, d in sorted(_MESURES.items()):
        if page.endswith(SUFFIXE_REPONSE):
            continue
        jour = [duree for quand, duree in d if maintenant - quand <= FENETRE_ALERTE_S]
        if len(jour) >= MIN_MESURES_ALERTE and (p95 := centile_95(jour)) > OBJECTIF_S:
            messages.append(f"🐢 « {page} » : 95e centile d'ouverture de {p95:.1f} s sur les dernières 24 heures "
                            f"({len(jour)} ouvertures, objectif < {OBJECTIF_S:.0f} s). Pistes : serveur réveillé "
                            "récemment, tâches de fond (broutage, révisions), mémoire du serveur.")
    return messages


def reinitialiser():
    _MESURES.clear()
    _DEMARRAGE.clear()
