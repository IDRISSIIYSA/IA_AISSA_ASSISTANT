"""
Comparer deux scénarios d'une même simulation côte à côte (deux crédits, deux statuts, deux business plans…).

Le visiteur garde un résultat comme « scénario A », change ses chiffres : le résultat courant devient le « scénario B ».
Chaque entrée et chaque résultat sont mis face à face ; quand les deux valeurs sont des nombres de même unité
(« 1 500 000 DH », « 20 % »), l'écart B − A est calculé (en points pour les pourcentages). La comparaison est
elle-même un rapport (PDF, Excel) avec les deux numéros de rapport d'origine.
"""

import re

import pandas as pd

from .rapports import rapport

_NOMBRE = re.compile(r"^\s*([−-]?\s*[\d\s  ]+(?:[,.]\d+)?)\s*(.*?)\s*$")


def valeur(texte):
    """« 1 500 000 DH » → (1500000.0, "DH") ; « 20,5 % » → (20.5, "%") ; sinon (None, texte)."""
    m = _NOMBRE.match(str(texte))
    if not m or not re.search(r"\d", m.group(1)):
        return None, str(texte)
    brut = re.sub(r"[\s  ]", "", m.group(1)).replace("−", "-").replace(",", ".")
    try:
        return float(brut), m.group(2)
    except ValueError:
        return None, str(texte)


def ecart(a, b):
    va, ua = valeur(a)
    vb, ub = valeur(b)
    if va is None or vb is None or ua != ub:
        return "" if str(a) == str(b) else "différent"
    d = vb - va
    if abs(d) < 1e-9:
        return "="
    texte = f"{d:+,.2f}".replace(",", " ").replace(".", ",").replace(",00", "")
    if ua == "%":
        return f"{texte} point(s)"
    return f"{texte} {ua}".strip()


def comparer(a, b):
    """Tableau : Rubrique, Nature, Scénario A, Scénario B, Écart (B − A)."""
    lignes = []
    for nature, cle in (("Entrée", "entrees"), ("Résultat", "resultats")):
        rubriques = list(dict.fromkeys([*a[cle], *b[cle]]))
        for r in rubriques:
            va, vb = a[cle].get(r, "—"), b[cle].get(r, "—")
            lignes.append({"Rubrique": r, "Nature": nature, "Scénario A": va, "Scénario B": vb,
                           "Écart (B − A)": ecart(va, vb)})
    return pd.DataFrame(lignes)


def rapport_comparaison(nom, a, b):
    t = comparer(a, b)
    differents = t[(t["Nature"] == "Résultat") & ~t["Écart (B − A)"].isin(["", "="])]
    return rapport(f"Comparaison de deux scénarios — {nom}", a["categorie"],
                   {"Scénario A (rapport)": a["numero"], "Scénario B (rapport)": b["numero"]},
                   {"Résultats qui changent": f"{len(differents)} sur {int((t['Nature'] == 'Résultat').sum())}",
                    **{f"Écart — {l['Rubrique']}": l["Écart (B − A)"] for _, l in differents.head(6).iterrows()}},
                   ["Les deux scénarios sont calculés par la même simulation, avec les mêmes textes et taux.",
                    "Écart = scénario B − scénario A, quand les deux valeurs sont des nombres de même unité "
                    "(les pourcentages en points)."],
                   [*dict.fromkeys(a["references"] + b["references"])], a.get("annee"), tableau=t,
                   remarques=["Comparez des scénarios réalistes : un écart favorable sur le papier doit être confirmé "
                              "par vos justificatifs et, si besoin, par votre expert-comptable."])
