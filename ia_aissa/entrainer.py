"""Envoie IA AISSA à l'école : python -m ia_aissa.entrainer [cle ...]"""
import sys
import time

from .ecole import MATIERES, PAR_CLE, entrainer, sauvegarder

if __name__ == "__main__":
    matieres = [PAR_CLE[c] for c in sys.argv[1:]] or MATIERES
    for m in matieres:
        debut = time.time()
        cerveau, historique = entrainer(m)
        sauvegarder(m, cerveau, historique)
        print(f"{m.domaine:28} {m.nom:42} {historique[0]['precision']:6.1%} -> "
              f"{historique[-1]['precision']:6.1%}  ({time.time() - debut:.0f}s)")
