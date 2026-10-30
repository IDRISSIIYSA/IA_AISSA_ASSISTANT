"""
Le temps d'ouverture de chaque page, mesuré à chaque affichage (objectif : moins de 3 secondes).

Deux mesures distinctes :
- l'affichage d'une page : du début à la fin du script Streamlit pour cette page (ce que vit chaque visiteur) ;
- le démarrage à froid du serveur : de la naissance du processus à la fin du premier affichage (imports de PyTorch,
  pandas…, payé une seule fois quand Streamlit Cloud réveille l'application).

Les mesures restent en mémoire du serveur (les 50 dernières par page) : rien n'est écrit en base à chaque affichage.
"""

import os
import statistics
import time
from collections import deque

import pandas as pd

OBJECTIF_S = 3.0
GARDER = 50
_MESURES = {}
_DEMARRAGE = {}


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


def enregistrer(page, duree):
    _MESURES.setdefault(page, deque(maxlen=GARDER)).append(float(duree))
    if "secondes" not in _DEMARRAGE:                 # premier affichage depuis le démarrage du serveur
        age = age_du_processus()
        _DEMARRAGE.update(secondes=age, page=page)


class Chrono:
    """with Chrono("IA AISSA"): … — mesure l'affichage de la page, même si elle s'interrompt (rerun, switch_page)."""

    def __init__(self, page):
        self.page = page

    def __enter__(self):
        self.debut = time.perf_counter()
        return self

    def __exit__(self, *exc):
        enregistrer(self.page, time.perf_counter() - self.debut)
        return False


def demarrage_a_froid():
    return _DEMARRAGE.get("secondes")


def tableau():
    """Par page : nombre d'affichages, médiane, 95e centile, maximum, et respect de l'objectif."""
    lignes = []
    for page, d in sorted(_MESURES.items()):
        v = sorted(d)
        p95 = v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]
        lignes.append({"Page": page, "Affichages mesurés": len(v), "Médiane (s)": round(statistics.median(v), 2),
                       "95e centile (s)": round(p95, 2), "Maximum (s)": round(v[-1], 2),
                       "Objectif < 3 s": "✅" if p95 < OBJECTIF_S else "⚠️"})
    return pd.DataFrame(lignes)


def reinitialiser():
    _MESURES.clear()
    _DEMARRAGE.clear()
