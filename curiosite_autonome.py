"""
Un cycle de curiosité d'IA AISSA, sans interface ni humain : lancé toutes les 6 heures par GitHub Actions,
après que tous les tests ont réussi (voir .github/workflows/curiosite.yml).

Variables d'environnement :
- MEMOIRE_URL (obligatoire) : la même mémoire durable que l'application, sinon ce qu'elle lit serait perdu ;
- ANTHROPIC_API_KEY (ou la clé du moteur choisi) ;
- IA_AISSA_MOTEUR (facultatif) : un nom de ia_aissa.assistant.MOTEURS, Claude par défaut ;
- IA_AISSA_MATIERES (facultatif) : nombre de matières faibles à nourrir par cycle (2 par défaut).
"""

import json
import os
import sys

from ia_aissa.assistant import MOTEURS, client_moteur
from ia_aissa.corrections import brancher
from ia_aissa.curiosite import cycle_curiosite
from ia_aissa.memoire import Memoire


def main():
    url = os.environ.get("MEMOIRE_URL")
    if not url:
        sys.exit("MEMOIRE_URL manquante : sans mémoire durable, ce qu'IA AISSA lirait serait perdu.")
    moteur = os.environ.get("IA_AISSA_MOTEUR") or next(iter(MOTEURS))
    cle = os.environ.get(MOTEURS[moteur]["secret"])
    if not cle:
        sys.exit(f"{MOTEURS[moteur]['secret']} manquante : IA AISSA a besoin de son moteur pour ruminer.")
    memoire = Memoire(url)
    brancher(memoire)
    bilan = cycle_curiosite(memoire, MOTEURS[moteur], client_moteur(moteur, cle),
                            nb_matieres=int(os.environ.get("IA_AISSA_MATIERES") or 2))
    print(json.dumps(bilan, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
