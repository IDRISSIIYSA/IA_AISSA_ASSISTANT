"""
Le banc d'essai permanent : des questions libres (français, darija en lettres latines et arabes), jamais vues telles
quelles, posées à IA AISSA à chaque séance de développement.

Deux niveaux sont mesurés :
- les cerveaux d'école seuls (aiguilleur + matière), pour suivre leur généralisation ;
- sa pensée propre (analogie, fiches, calculs et cerveaux), c'est-à-dire ce qu'un visiteur reçoit sans clé API.

Chaque question ratée par les cerveaux d'école reçoit de nouvelles formulations (même sens, autres mots), pour
vérifier qu'une réussite n'est pas due à une phrase apprise par cœur. L'historique des séances est gardé dans
data/banc_historique.json (versionné avec le code) et, depuis l'administration, dans la base.
"""

import datetime
import json
from pathlib import Path

HISTORIQUE = Path(__file__).resolve().parent.parent / "data" / "banc_historique.json"

QUESTIONS = [
    ("achat de 3 ordinateurs pour le bureau", "2355 Matériel informatique"),
    ("paiement de la facture maroc telecom", "6145 Frais postaux et de télécommunications"),
    ("qui a construit la koutoubia ?", "Almohades (1121-1269)"),
    ("le vendeur paie le fret et l'assurance jusqu'au port", "CIF (coût assurance fret)"),
    ("je dois prouver l'origine pour l'union européenne", "Certificat d'origine (EUR.1)"),
    ("licenciement d'un salarié", "Code du travail (loi 65-99)"),
    ("mon ami veut faire un prêt immobilier", "Crédit"),
    ("paiement du loyer du dépôt", "6131 Locations et charges locatives"),
    ("facture d'électricité", "6125 Achats non stockés de matières et fournitures"),
    ("la force se mesure en ?", "Newton (N)"),
    ("fatoura dyal dow w lma", "6125 Achats non stockés de matières et fournitures"),
    ("khlast lkra dyal lmahal", "6131 Locations et charges locatives"),
    ("chrit pc jdid l charika", "2355 Matériel informatique"),
    ("chkoun li bna lkoutoubia", "Almohades (1121-1269)"),
    ("lkhdam bgha ytred mn lkhdma", "Code du travail (loi 65-99)"),
    ("tva dyal dwa", "Exonéré"),
    ("bghit nakhod kredi dyal dar", "Crédit"),
    ("dariba 3la rb7 dyal charika", "IS (impôt sur les sociétés)"),
    ("خلصت الكرا ديال المحل", "6131 Locations et charges locatives"),
    ("شريت طوموبيل للشركة", "2340 Matériel de transport"),
]

# Nouvelles formulations des questions ratées par les cerveaux d'école (séance du 31/10/2026) : même sens, autres mots
NOUVELLES_FORMULATIONS = [
    ("j'ai réglé l'abonnement internet du bureau", "6145 Frais postaux et de télécommunications"),
    ("khlast fatoura dyal telephone dyal charika", "6145 Frais postaux et de télécommunications"),
    ("je veux emprunter pour acheter un appartement", "Crédit"),
    ("bghit nakhod kredi l tomobil", "Crédit"),
    ("payer la location du local commercial", "6131 Locations et charges locatives"),
    ("khlast l kra dyal lmagasin", "6131 Locations et charges locatives"),
    ("achat d'un ordinateur portable pour la société", "2355 Matériel informatique"),
    ("chrit ordinateur l bureau", "2355 Matériel informatique"),
    ("mon patron veut me licencier", "Code du travail (loi 65-99)"),
    ("wach ymken lpatron ytredni bla sbab", "Code du travail (loi 65-99)"),
    ("tva sur les médicaments", "Exonéré"),
    ("impôt sur le bénéfice de la société", "IS (impôt sur les sociétés)"),
    ("chhal dariba 3la arbah charika", "IS (impôt sur les sociétés)"),
    ("achat d'une voiture pour l'entreprise", "2340 Matériel de transport"),
    ("chrit tomobil l charika", "2340 Matériel de transport"),
]
TOUTES = QUESTIONS + NOUVELLES_FORMULATIONS


def evaluer(questions=TOUTES, memoire=None):
    """Pose chaque question aux deux niveaux. Renvoie les lignes détaillées et les scores."""
    from .ecole import repondre_automatiquement
    from .pensee import penser
    lignes = []
    for question, attendu in questions:
        ecole = repondre_automatiquement(question)[0]
        pensee = penser(question, memoire)[0]
        lignes.append({"question": question, "attendu": attendu, "ecole": ecole["reponse"],
                       "confiance_ecole": round(float(ecole["confiance"]), 3), "ecole_juste": ecole["reponse"] == attendu,
                       "pensee_juste": attendu in pensee})
    n = len(lignes)
    return {"date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M"), "questions": n,
            "ecole": sum(l["ecole_juste"] for l in lignes), "pensee": sum(l["pensee_juste"] for l in lignes),
            "ratees_ecole": [l["question"] for l in lignes if not l["ecole_juste"]],
            "ratees_pensee": [l["question"] for l in lignes if not l["pensee_juste"]], "lignes": lignes}


def resume(resultat):
    return {k: v for k, v in resultat.items() if k != "lignes"}


def historique(memoire=None):
    """Les séances passées : celles du fichier versionné, puis celles lancées depuis l'administration."""
    seances = json.loads(HISTORIQUE.read_text(encoding="utf-8")) if HISTORIQUE.exists() else []
    if memoire is not None:
        seances += [json.loads(v) for _, v in sorted(memoire.reglages("banc:").items())]
    return sorted(seances, key=lambda s: s["date"])


def garder(resultat, memoire=None):
    """Ajoute la séance à l'historique : dans la base si elle est donnée, sinon dans le fichier versionné."""
    r = resume(resultat)
    if memoire is not None:
        memoire.definir_reglage(f"banc:{r['date']}", json.dumps(r, ensure_ascii=False))
        return
    seances = json.loads(HISTORIQUE.read_text(encoding="utf-8")) if HISTORIQUE.exists() else []
    seances.append(r)
    HISTORIQUE.write_text(json.dumps(seances, ensure_ascii=False, indent=1), encoding="utf-8")
