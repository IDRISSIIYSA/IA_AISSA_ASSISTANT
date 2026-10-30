"""Banc d'essai : questions libres (français, darija en lettres latines et arabes), jamais vues telles quelles.
Lancement : python tests/banc_questions.py — à suivre à chaque séance de développement."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ia_aissa.ecole import PAR_CLE, charger, examen, precision, repondre_automatiquement  # noqa: E402
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
bons = 0
for q, attendu in QUESTIONS:
    r = repondre_automatiquement(q)[0]
    ok = r["reponse"] == attendu
    bons += ok
    print(("✅" if ok else "❌"), f"{q[:42]:42} -> {r['reponse'][:38]} ({r['confiance']:.0%})")
print(f"Banc d'essai : {bons}/{len(QUESTIONS)} | aiguilleur à l'examen : {precision(charger('orientation')[0], examen(PAR_CLE['orientation'])):.1%}")

# La pensée propre (analogie + cerveaux d'école), telle qu'elle répond sans clé API
from ia_aissa.pensee import penser  # noqa: E402
bons_pensee = sum(attendu in penser(q)[0] for q, attendu in QUESTIONS)
print(f"Pensée propre (analogie + école) : {bons_pensee}/{len(QUESTIONS)}")
