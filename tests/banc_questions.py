"""Banc d'essai permanent : questions libres (français, darija en lettres latines et arabes), jamais vues telles quelles.
Lancement à chaque séance de développement : python tests/banc_questions.py --garder (ajoute la séance à
data/banc_historique.json). Sans --garder, affiche seulement les résultats."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ia_aissa.banc import evaluer, garder, historique  # noqa: E402
from ia_aissa.ecole import PAR_CLE, charger, examen, precision  # noqa: E402

r = evaluer()
for l in r["lignes"]:
    print(("✅" if l["ecole_juste"] else "❌"), ("🧠" if l["pensee_juste"] else "⚠️"),
          f"{l['question'][:44]:44} -> {l['ecole'][:36]} ({l['confiance_ecole']:.0%})")
print(f"Cerveaux d'école seuls : {r['ecole']}/{r['questions']} | pensée propre (ce que reçoit un visiteur) : "
      f"{r['pensee']}/{r['questions']} | aiguilleur à l'examen : "
      f"{precision(charger('orientation')[0], examen(PAR_CLE['orientation'])):.1%}")
if "--garder" in sys.argv:
    garder(r)
    print(f"Séance gardée ({len(historique())} au total).")
