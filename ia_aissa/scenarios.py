"""
Comparer deux scénarios d'une même simulation côte à côte (deux crédits, deux statuts, deux business plans…).

Le visiteur garde un résultat comme « scénario A », change ses chiffres : le résultat courant devient le « scénario B ».
Chaque entrée et chaque résultat sont mis face à face ; quand les deux valeurs sont des nombres de même unité
(« 1 500 000 DH », « 20 % »), l'écart B − A est calculé (en points pour les pourcentages). La comparaison est
elle-même un rapport (PDF, Excel) avec les deux numéros de rapport d'origine.
"""

import re


from .rapports import rapport
from .reseaux import Paresseux

pd = Paresseux("pandas")              # au premier tableau : pas au démarrage

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


# Le critère qui départage deux scénarios, par simulation : (résultat, "min" ou "max", ce qu'il mesure). Les
# simulations sans critère unique (choix à arbitrer, ou verdict déjà donné par la simulation) n'en ont pas.
CRITERES = {
    "Crédit (échéancier)": ("Total remboursé", "min", "le total remboursé"),
    "TEG d'un crédit": ("Coût total du crédit", "min", "le coût total du crédit"),
    "Remboursement anticipé d'un crédit": ("Gain net", "max", "le gain net du remboursement"),
    "Capacité d'emprunt": ("Capital empruntable", "max", "le capital que la banque peut prêter"),
    "Épargne (intérêts composés)": ("Capital final", "max", "le capital final"),
    "Investissement (VAN, TRI)": ("VAN", "max", "la valeur actuelle nette (VAN)"),
    "Valorisation d'entreprise (DCF)": ("Valeur des titres (fonds propres)", "max", "la valeur des titres"),
    "Effet de levier financier": ("Rentabilité financière (après IS)", "max", "la rentabilité financière"),
    "Risque de perte (Monte-Carlo)": ("Probabilité de perte", "min", "la probabilité de perte"),
    "IR (impôt sur le revenu)": ("IR annuel", "min", "l'IR annuel"),
    "IS (impôt sur les sociétés)": ("IS dû", "min", "l'IS dû"),
    "Auto-entrepreneur": ("Impôt", "min", "l'impôt"),
    "Revenus fonciers (loyers)": ("IR dû à cause des loyers", "min", "l'IR dû sur les loyers"),
    "Retenue sur dividendes": ("Dividende net perçu", "max", "le dividende net perçu"),
    "Plus-value immobilière (profit foncier)": ("Net pour le vendeur", "max", "ce qui reste au vendeur"),
    "Frais d'acquisition immobilière": ("Coût complet de l'achat", "min", "le coût complet de l'achat"),
    "Rentabilité locative": ("Rentabilité nette (avant impôt)", "max", "la rentabilité nette"),
    "Douane à l'importation": ("Coût dédouané", "min", "le coût dédouané"),
    "Paie (brut ↔ net)": ("Salaire net", "max", "le salaire net du salarié"),
    "Retraite CNSS (pension)": ("Pension mensuelle estimée", "max", "la pension mensuelle"),
    "Seuil de rentabilité": ("Seuil (unités)", "min", "le seuil de rentabilité (moins d'unités à vendre)"),
    "Coût de revient complet": ("Coût de revient unitaire", "min", "le coût de revient unitaire"),
    "Trésorerie sur 12 mois": ("Solde le plus bas", "max", "le solde le plus bas de l'année"),
    "Besoin en fonds de roulement (BFR)": ("BFR", "min", "le besoin en fonds de roulement"),
}


def verdict(nom, a, b):
    """Une phrase : le scénario le plus avantageux selon le critère de la simulation, et pourquoi ; None si la
    simulation n'a pas de critère unique ou si le critère n'est pas comparable (valeur absente, unités différentes)."""
    if nom not in CRITERES:
        return None
    rubrique, sens, quoi = CRITERES[nom]
    texte_a, texte_b = a["resultats"].get(rubrique), b["resultats"].get(rubrique)
    (va, ua), (vb, ub) = valeur(texte_a), valeur(texte_b)
    if va is None or vb is None or ua != ub:
        return None
    if abs(va - vb) < 1e-9:
        return f"⚖️ Égalité sur {quoi} ({texte_a}) : choisissez selon les autres résultats du tableau."
    meilleur = "B" if (vb < va) == (sens == "min") else "A"
    gagnant, perdant = (texte_b, texte_a) if meilleur == "B" else (texte_a, texte_b)
    sens_mot = "plus bas" if sens == "min" else "plus élevé"
    return (f"🏆 Le scénario {meilleur} est le plus avantageux selon {quoi} : {gagnant} contre {perdant} "
            f"(écart B − A : {ecart(texte_a, texte_b)}), car ce critère doit être le {sens_mot} possible.")


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
    phrase = verdict(nom, a, b)
    return rapport(f"Comparaison de deux scénarios — {nom}", a["categorie"],
                   {"Scénario A (rapport)": a["numero"], "Scénario B (rapport)": b["numero"]},
                   {**({"Le plus avantageux": phrase.lstrip("🏆⚖️ ")} if phrase else {}),
                    "Résultats qui changent": f"{len(differents)} sur {int((t['Nature'] == 'Résultat').sum())}",
                    **{f"Écart — {l['Rubrique']}": l["Écart (B − A)"] for _, l in differents.head(6).iterrows()}},
                   ["Les deux scénarios sont calculés par la même simulation, avec les mêmes textes et taux.",
                    "Écart = scénario B − scénario A, quand les deux valeurs sont des nombres de même unité "
                    "(les pourcentages en points)."],
                   [*dict.fromkeys(a["references"] + b["references"])], a.get("annee"), tableau=t,
                   remarques=["Comparez des scénarios réalistes : un écart favorable sur le papier doit être confirmé "
                              "par vos justificatifs et, si besoin, par votre expert-comptable."])
