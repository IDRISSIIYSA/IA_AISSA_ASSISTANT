"""
L'école d'IA AISSA : chaque matière génère des exercices, et un cerveau né vide apprend seul,
par essais et récompenses (+1 bonne réponse, -1 mauvaise), avec une mémoire de ses expériences.

Les bonnes réponses viennent des règles de connaissances.py : IA AISSA ne lit pas les règles,
elle les découvre en se trompant puis en se corrigeant.
"""

import random
import re
import unicodedata
import zlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import torch
import torch.nn as nn

from . import connaissances as K
from .langues import LANGUES

DOSSIER_CERVEAUX = Path(__file__).resolve().parent / "cerveaux"
DIM_TEXTE = 512


# ==========================================
# Perception du texte : mots et paires de mots -> vecteur (hachage)
# ==========================================
def mots(texte):
    texte = "".join(c for c in unicodedata.normalize("NFD", texte.lower()) if unicodedata.category(c) != "Mn")
    return [m for m in re.split(r"[^a-z0-9]+", texte) if len(m) > 1]


def vectoriser(texte, dim=DIM_TEXTE):
    v = np.zeros(dim, dtype=np.float32)
    m = mots(texte)
    for jeton in m + [a + "_" + b for a, b in zip(m, m[1:])]:
        v[zlib.crc32(jeton.encode()) % dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


def vectoriser_caracteres(texte, dim=DIM_TEXTE):
    """Trigrammes de caractères : reconnaît une langue à ses sons écrits, même sur un mot inconnu."""
    t = f"  {texte.lower()}  "
    v = np.zeros(dim, dtype=np.float32)
    for i in range(len(t) - 2):
        v[zlib.crc32(t[i:i + 3].encode()) % dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


def exercice_langue(rng, categories):
    """Un extrait de phrase (2 mots ou plus) : il faut deviner la langue."""
    y = int(rng.integers(len(categories)))
    m = categories[y][int(rng.integers(len(categories[y])))].split()
    debut = int(rng.integers(0, max(1, len(m) - 1)))
    extrait = " ".join(m[debut:debut + int(rng.integers(2, len(m) + 1))])
    return vectoriser_caracteres(extrait), y, extrait


BRUIT = ["", "", " pour 3 500 dh", " le 12 mars", " facture n° 245", " exercice 2026", " selon pièce jointe",
         " montant 18 000 dirhams", " à casablanca", " du mois dernier"]
PREFIXES = ["", "", "opération : ", "enregistrement de ", "comptabiliser ", "question : ", "cas : "]


def exercice_texte(rng, categories, perception=None):
    """Tire une formulation au hasard, ajoute du bruit et retire parfois un mot."""
    perception = perception or vectoriser
    y = int(rng.integers(len(categories)))
    phrase = categories[y][int(rng.integers(len(categories[y])))]
    m = phrase.split()
    if len(m) > 3 and rng.random() < 0.3:
        del m[int(rng.integers(len(m)))]
    texte = PREFIXES[int(rng.integers(len(PREFIXES)))] + " ".join(m) + BRUIT[int(rng.integers(len(BRUIT)))]
    return perception(texte), y, texte


# ==========================================
# Les matières
# ==========================================
@dataclass
class Matiere:
    cle: str
    nom: str
    domaine: str
    actions: list
    dim: int
    generer: Callable          # rng -> (vecteur, bonne_reponse, énoncé lisible)
    texte: bool = False
    note: str = ""
    perception: Callable = vectoriser


def _matiere_texte(cle, nom, domaine, dictionnaire, note, libelle=lambda k, v: k):
    noms = list(dictionnaire)
    categories = [dictionnaire[k] if isinstance(dictionnaire[k], list) else dictionnaire[k][1] for k in noms]
    actions = [libelle(k, dictionnaire[k]) for k in noms]
    return Matiere(cle, nom, domaine, actions, DIM_TEXTE, lambda rng: exercice_texte(rng, categories), True, note)


def _ir(rng):
    revenu = float(np.exp(rng.uniform(np.log(15_000), np.log(600_000))))
    return np.array([revenu / 200_000, np.log(revenu) / 13], np.float32), K.tranche_ir(revenu), \
        f"Revenu net imposable annuel : {revenu:,.0f} DH"


def _is(rng):
    benefice = float(np.exp(rng.uniform(np.log(1e5), np.log(1e9)))) * (1 if rng.random() > 0.15 else -1)
    y = 0 if benefice <= 0 else (2 if benefice >= K.SEUIL_IS else 1)
    return np.array([np.sign(benefice), np.log10(abs(benefice)) / 9], np.float32), y, \
        f"Bénéfice fiscal : {benefice:,.0f} DH"


def _paie(rng):
    brut = float(rng.uniform(3_000, 12_000))
    y = int(brut > K.PLAFOND_CNSS_MENSUEL)
    return np.array([brut / 10_000], np.float32), y, f"Salaire brut mensuel : {brut:,.0f} DH"


def _rh(rng):
    absent, turnover, hsup, satisf = rng.uniform(0, 12), rng.uniform(0, 30), rng.uniform(0, 20), rng.uniform(2, 10)
    if absent > 6 or satisf < 5:
        y = 1
    elif turnover > 15:
        y = 2
    elif hsup > 10:
        y = 3
    else:
        y = 0
    return np.array([absent / 10, turnover / 20, hsup / 10, satisf / 10], np.float32), y, \
        f"Absentéisme {absent:.1f} %, turnover {turnover:.1f} %, heures sup {hsup:.1f} %, satisfaction {satisf:.1f}/10"


def _stock(rng):
    demande, delai, securite = rng.uniform(5, 50), rng.uniform(2, 20), rng.uniform(0, 300)
    point = demande * delai + securite
    stock = rng.uniform(0.3, 1.7) * point
    return np.array([stock / point, demande / 50, delai / 20, securite / 300], np.float32), int(stock <= point), \
        f"Stock {stock:.0f} u, demande {demande:.0f} u/jour, délai {delai:.0f} j, stock de sécurité {securite:.0f} u"


def _van(rng):
    investissement = rng.uniform(100_000, 1_000_000)
    flux = rng.uniform(0.1, 0.35, 5) * investissement
    taux = rng.uniform(0.03, 0.15)
    y = int(K.calculer_van(investissement, flux, taux)["van"] > 0)
    return np.array([*(flux / investissement), taux * 5], np.float32), y, \
        f"Investissement {investissement:,.0f} DH, flux {', '.join(f'{f:,.0f}' for f in flux)}, taux {taux:.1%}"


def _ratios(rng):
    liquidite, autonomie, rentabilite = rng.uniform(0.5, 2.5), rng.uniform(0.05, 0.7), rng.uniform(-0.15, 0.2)
    if liquidite < 1 or autonomie < 0.15 or rentabilite < -0.05:
        y = 2
    elif liquidite >= 1.2 and autonomie >= 0.3 and rentabilite > 0:
        y = 0
    else:
        y = 1
    return np.array([liquidite / 2, autonomie * 2, rentabilite * 5], np.float32), y, \
        f"Liquidité générale {liquidite:.2f}, autonomie financière {autonomie:.0%}, rentabilité nette {rentabilite:.1%}"


def _placements(rng):
    r1, n1, r2, n2 = rng.uniform(0.01, 0.08), rng.integers(1, 15), rng.uniform(0.01, 0.08), rng.integers(1, 15)
    y = int((1 + r2) ** n2 > (1 + r1) ** n1)
    return np.array([r1 * 10, n1 / 10, r2 * 10, n2 / 10, (n1 * np.log1p(r1) - n2 * np.log1p(r2)) * 5], np.float32), y, \
        f"Placement A : {r1:.2%} pendant {n1} ans ; placement B : {r2:.2%} pendant {n2} ans"


def _seuil(rng):
    prix = rng.uniform(50, 500)
    cvu = prix * rng.uniform(0.3, 0.95)
    charges_fixes = rng.uniform(1e5, 2e6)
    volume = rng.uniform(1e3, 5e4)
    y = int(volume * (prix - cvu) > charges_fixes)
    return np.array([prix / 500, cvu / prix, charges_fixes / 2e6, volume / 5e4,
                     volume * (prix - cvu) / 2e6], np.float32), y, \
        f"Prix {prix:.0f} DH, coût variable {cvu:.0f} DH, charges fixes {charges_fixes:,.0f} DH, volume {volume:,.0f}"


def _politique_monetaire(rng):
    inflation, ecart_production = rng.uniform(-0.5, 7), rng.uniform(-4, 3)
    if inflation > 3 and ecart_production >= -1:
        y = 0
    elif inflation < 1.5 or (ecart_production < -2 and inflation < 2.5):
        y = 2
    else:
        y = 1
    return np.array([inflation / 5, ecart_production / 3], np.float32), y, \
        f"Inflation {inflation:.1f} %, écart de production {ecart_production:+.1f} %"


def _ecarts(rng):
    from controle_gestion_ia import DECISION_IDEALE, classer_situation
    ecart, tendance = rng.normal(0.03, 0.08), rng.normal(0, 0.03)
    y = DECISION_IDEALE[classer_situation({"ecart_pct": ecart, "tendance": tendance})]
    return np.array([ecart * 5, tendance * 20], np.float32), y, f"Écart budgétaire {ecart:+.1%}, tendance {tendance:+.1%}"


def _forme_juridique(rng):
    associes = int(rng.choice([1, 1, 1, 2, 3, 4, 5, 8, 20, 60]))
    services = int(rng.random() < 0.5)
    ca = float(np.exp(rng.uniform(np.log(5e4), np.log(2e7))))
    levee_fonds = int(rng.random() < 0.3)
    plafond = K.PLAFOND_AE["services" if services else "commerce"]
    if associes == 1:
        y = 0 if ca <= plafond and not levee_fonds else 1
    elif associes > K.ASSOCIES_MAX_SARL or (associes >= K.ACTIONNAIRES_MIN_SA and levee_fonds):
        y = 3
    else:
        y = 2
    return np.array([min(associes, 60) / 10, associes == 1, services, np.log10(ca) / 7, ca / plafond / 10, levee_fonds],
                    np.float32), y, \
        f"{associes} associé(s), {'services' if services else 'commerce'}, CA prévu {ca:,.0f} DH" + \
        (", besoin de lever des fonds" if levee_fonds else "")


def _cycle_de_vie(rng):
    croissance, part_marche = rng.uniform(-30, 60), rng.uniform(0, 40)
    if croissance < -5:
        y = 3
    elif croissance > 20:
        y = 0 if part_marche < 5 else 1
    elif part_marche < 5:
        y = 0
    else:
        y = 2
    return np.array([croissance / 30, part_marche / 20], np.float32), y, \
        f"Croissance des ventes {croissance:+.0f} %, part de marché {part_marche:.0f} %"


def _wilson(rng):
    demande, cout_commande, stockage = rng.uniform(500, 50_000), rng.uniform(50, 2_000), rng.uniform(1, 50)
    optimale = K.quantite_wilson(demande, cout_commande, stockage)["quantite_economique"]
    proposee = optimale * float(np.exp(rng.uniform(np.log(0.4), np.log(2.5))))
    y = 0 if proposee < 0.85 * optimale else (2 if proposee > 1.15 * optimale else 1)
    return np.array([np.log(demande) / 10, np.log(cout_commande) / 7, np.log(stockage) / 4,
                     np.log(proposee) / 9], np.float32), y, \
        f"Demande {demande:,.0f} u/an, coût d'une commande {cout_commande:,.0f} DH, stockage {stockage:.1f} DH/u/an, " \
        f"commande proposée {proposee:,.0f} u"


def _bcg(rng):
    croissance, part = rng.uniform(-0.05, 0.30), float(np.exp(rng.uniform(np.log(0.1), np.log(5))))
    y = ["Vedette", "Vache à lait", "Dilemme", "Poids mort"].index(K.position_bcg(croissance, part))
    return np.array([croissance * 5, np.log(part)], np.float32), y, \
        f"Croissance du marché {croissance:.0%}, part de marché relative {part:.2f}"


def _credit(rng):
    revenu = rng.uniform(4_000, 40_000)
    capital, taux, duree = rng.uniform(20_000, 1_500_000), rng.uniform(0.04, 0.09), int(rng.choice([60, 120, 180, 240, 300]))
    autres = rng.uniform(0, 0.25) * revenu
    m = K.mensualite_credit(capital, taux, duree)["mensualite"]
    ratio = (m + autres) / revenu
    y = 0 if ratio <= 0.33 else (1 if ratio <= 0.40 else 2)
    return np.array([ratio * 2, revenu / 40_000, np.log(capital) / 14], np.float32), y, \
        f"Revenu {revenu:,.0f} DH/mois, crédit {capital:,.0f} DH à {taux:.1%} sur {duree} mois, autres charges {autres:,.0f} DH"


def _fractions(rng):
    a, b, c, d = (int(v) for v in rng.integers(1, 13, 4))
    if rng.random() < 0.15:
        k = int(rng.integers(2, 4))
        c, d = a * k, b * k                                           # fractions égales
    diff = a / b - c / d
    y = 1 if abs(diff) < 1e-9 else (0 if diff > 0 else 2)
    return np.array([a / 12, b / 12, c / 12, d / 12, np.log(a / b), np.log(c / d)], np.float32), y, \
        f"Comparer {a}/{b} et {c}/{d}"


def _discriminant(rng):
    a = int(rng.choice([v for v in range(-6, 7) if v]))
    if rng.random() < 0.25:
        r = int(rng.integers(-5, 6))
        b, c = -2 * a * r, a * r * r                                  # racine double
    else:
        b, c = int(rng.integers(-12, 13)), int(rng.integers(-12, 13))
    delta = b * b - 4 * a * c
    y = 2 if delta > 0 else (1 if delta == 0 else 0)
    return np.array([a / 6, b / 12, c / 12, b * b / 144, a * c / 72, np.sign(delta) * np.log1p(abs(delta)) / 6],
                    np.float32), y, f"Équation {a}x² {b:+d}x {c:+d} = 0"


MATIERES = [
    _matiere_texte("comptabilite", "Imputation au Plan Comptable Marocain", "Comptabilité", K.PCM,
                   "Trouver le compte du CGNC correspondant à une opération.", lambda k, v: f"{k} {v[0]}"),
    _matiere_texte("tva", "Régime de TVA 2026", "Fiscalité", K.TVA_OPERATIONS,
                   "20 %, 10 % ou exonéré selon l'opération."),
    Matiere("ir", "Tranche d'IR", "Fiscalité",
            [f"{t:.0%}" for _, t, _ in K.BAREME_IR], 2, _ir, note="Barème IR annuel LF 2025-2026."),
    Matiere("is", "Taux d'IS", "Fiscalité", ["Déficit : cotisation minimale", "IS 20 %", "IS 35 %"], 2, _is,
            note="Taux proportionnels 2026."),
    Matiere("paie", "Plafond CNSS", "Ressources humaines",
            ["CNSS sur tout le salaire", "CNSS plafonnée à 6 000 DH"], 1, _paie, note="Assiette de la cotisation CNSS."),
    Matiere("rh", "Diagnostic social", "Ressources humaines",
            ["RAS", "Enquête climat social", "Plan de fidélisation", "Recrutement"], 4, _rh,
            note="Règles pédagogiques simplifiées."),
    Matiere("production", "Réapprovisionnement", "Gestion de production",
            ["Attendre", "Passer commande"], 4, _stock, note="Point de commande = demande × délai + stock de sécurité."),
    Matiere("investissement", "Décision d'investissement (VAN)", "Finance",
            ["Rejeter", "Accepter"], 6, _van, note="Accepter si la VAN est positive."),
    Matiere("analyse_financiere", "Analyse financière", "Finance",
            ["Situation saine", "Situation fragile", "Entreprise en difficulté"], 3, _ratios,
            note="Seuils pédagogiques simplifiés."),
    Matiere("maths_financieres", "Mathématiques financières", "Mathématiques",
            ["Placement A", "Placement B"], 5, _placements, note="Comparer deux placements à intérêts composés."),
    Matiere("commercial", "Seuil de rentabilité", "Commercial",
            ["Non rentable", "Rentable"], 5, _seuil, note="Marge sur coût variable × volume > charges fixes."),
    Matiere("economie", "Politique monétaire (Bank Al-Maghrib)", "Économie",
            ["Hausse du taux directeur", "Maintien", "Baisse du taux directeur"], 2, _politique_monetaire,
            note="Règle de Taylor stylisée, à visée pédagogique."),
    Matiere("controle_gestion", "Pilotage des écarts", "Contrôle de gestion",
            ["Alerte écart", "Statu quo", "Optimiser coûts"], 2, _ecarts, note="Mêmes règles que le tableau de bord."),
    _matiere_texte("juridique", "Texte de loi applicable", "Juridique", K.TEXTES_DE_LOI,
                   "Identifier la loi marocaine qui régit une situation."),
    Matiere("creation", "Choix de la forme juridique", "Création d'entreprise",
            ["Auto-entrepreneur", "SARL AU", "SARL", "SA"], 6, _forme_juridique,
            note="Recommandation pédagogique selon associés, activité, CA et besoin de financement."),
    Matiere("langues", "Reconnaître la langue", "Langues", list(LANGUES), DIM_TEXTE,
            lambda rng: exercice_langue(rng, [v["phrases"] for v in LANGUES.values()]), True,
            "Arabe, darija (écriture arabe et latine), français, anglais, espagnol.", vectoriser_caracteres),
    _matiere_texte("histoire", "Dynasties du Maroc", "Histoire", K.DYNASTIES,
                   "Rattacher un événement de l'histoire du Maroc à sa dynastie."),
    _matiere_texte("sciences", "Disciplines scientifiques", "Sciences", K.DISCIPLINES,
                   "Reconnaître la discipline d'une notion scientifique."),
    _matiere_texte("epistemologie", "Épistémologie", "Épistémologie", K.EPISTEMOLOGUES,
                   "Reconnaître le penseur derrière une idée sur la connaissance scientifique."),
    _matiere_texte("marketing", "Mix marketing (4P)", "Marketing", K.MIX_MARKETING,
                   "Classer une décision dans le bon « P » du mix marketing."),
    Matiere("cycle_de_vie", "Cycle de vie du produit", "Marketing",
            ["Lancement", "Croissance", "Maturité", "Déclin"], 2, _cycle_de_vie,
            note="Selon la croissance des ventes et la part de marché (seuils pédagogiques)."),
    _matiere_texte("incoterms", "Incoterms 2020", "Commerce international", K.INCOTERMS,
                   "Reconnaître l'Incoterm d'après la répartition des frais et des risques."),
    _matiere_texte("transit", "Documents de transit et de douane", "Transit", K.TRANSIT,
                   "Identifier le document ou la procédure de dédouanement au Maroc."),
    Matiere("logistique", "Quantité économique (Wilson)", "Logistique",
            ["Commande trop petite", "Commande optimale (±15 %)", "Commande trop grande"], 4, _wilson,
            note="Comparer la commande proposée à Q* = √(2 × demande × coût de commande / coût de stockage)."),
    _matiere_texte("familles_sciences", "Grandes familles de sciences", "Sciences", K.FAMILLES_SCIENCES,
                   "Sciences formelles, naturelles, humaines et sociales, appliquées."),
    _matiere_texte("droit_marocain", "Droit civil, pénal et bancaire marocain", "Juridique", K.DROIT_MAROCAIN,
                   "DOC, Moudawana, Code pénal, loi bancaire 103-12, loi 43-05."),
    _matiere_texte("droit_compare", "Systèmes juridiques comparés", "Juridique", K.SYSTEMES_JURIDIQUES,
                   "Droit français, droit musulman, droits arabes modernes, droit marocain, common law."),
    _matiere_texte("quel_impot", "Quel impôt s'applique ?", "Fiscalité", K.QUEL_IMPOT,
                   "IS, IR, TVA, droits d'enregistrement, impôts locaux, retenue à la source, cotisation minimale."),
    _matiere_texte("gestion", "Fonctions de l'entreprise", "Gestion d'entreprise", K.FONCTIONS_ENTREPRISE,
                   "Rattacher une tâche à la bonne fonction de l'entreprise."),
    _matiere_texte("strategie", "Outils du management stratégique", "Stratégie", K.OUTILS_STRATEGIQUES,
                   "SWOT, PESTEL, Porter, BCG, chaîne de valeur, Ansoff."),
    Matiere("bcg", "Matrice BCG", "Stratégie", ["Vedette", "Vache à lait", "Dilemme", "Poids mort"], 2, _bcg,
            note="Croissance du marché ≥ 10 % et part de marché relative ≥ 1."),
    _matiere_texte("banque", "Opérations bancaires", "Banque et finance", K.OPERATIONS_BANCAIRES,
                   "Crédit, dépôts, paiements, international, marchés, prudentiel."),
    Matiere("credit", "Décision de crédit", "Banque et finance", ["Accord", "Accord sous conditions", "Refus"], 3, _credit,
            note="Taux d'endettement : ≤ 33 % accord, ≤ 40 % sous conditions (seuils pédagogiques)."),
    _matiere_texte("statistiques", "Notions de statistiques", "Statistiques", K.NOTIONS_STATISTIQUES,
                   "Reconnaître la notion statistique décrite."),
    _matiere_texte("faits_economiques", "Faits économiques et sociaux", "Économie", K.FAITS_ECONOMIQUES,
                   "Reconnaître le phénomène économique ou social décrit."),
    _matiere_texte("visa", "Dossier de visa", "Visa et voyage", K.DOSSIER_VISA,
                   "Classer une pièce dans la bonne rubrique du dossier de visa."),
    Matiere("fractions", "Comparer des fractions", "École — primaire",
            ["La première est plus grande", "Elles sont égales", "La seconde est plus grande"], 6, _fractions,
            note="Mathématiques, primaire."),
    _matiere_texte("regions", "Régions du Maroc", "École — primaire", K.REGIONS_MAROC,
                   "Géographie : retrouver la région d'une ville (découpage en 12 régions)."),
    Matiere("discriminant", "Équation du second degré", "École — collège et lycée",
            ["Aucune solution réelle", "Une solution double", "Deux solutions"], 6, _discriminant,
            note="Mathématiques : signe du discriminant Δ = b² − 4ac."),
    _matiere_texte("corps_humain", "Le corps humain", "École — collège", K.SYSTEMES_CORPS,
                   "SVT : rattacher un organe à son système."),
    _matiere_texte("unites", "Grandeurs et unités", "École — collège", K.UNITES_SI,
                   "Physique-chimie : l'unité du système international d'une grandeur."),
    Matiere("grammaire_fr", "Nature des mots", "École — collège", list(K.NATURE_MOTS), DIM_TEXTE,
            lambda rng: exercice_texte(rng, list(K.NATURE_MOTS.values()), vectoriser_caracteres), True,
            "Français : nom, verbe, adjectif, adverbe, préposition, pronom.", vectoriser_caracteres),
    Matiere("nahw", "النحو : اسم، فعل، حرف", "École — collège", list(K.NAHW_ARABE), DIM_TEXTE,
            lambda rng: exercice_texte(rng, list(K.NAHW_ARABE.values()), vectoriser_caracteres), True,
            "Arabe : reconnaître الاسم والفعل والحرف.", vectoriser_caracteres),
    _matiere_texte("anglais", "English tenses", "École — collège et lycée", K.TEMPS_ANGLAIS,
                   "Anglais : reconnaître le temps d'une phrase."),
    _matiere_texte("philosophie", "Philosophes", "École — lycée", K.PHILOSOPHES,
                   "Philosophie (baccalauréat) : retrouver le philosophe d'une idée."),
    _matiere_texte("matiere_scolaire", "Quelle matière ?", "École — orientation", K.MATIERES_SCOLAIRES,
                   "Reconnaître la matière scolaire d'un exercice (pour l'aide aux devoirs)."),
    _matiere_texte("ia", "Types d'intelligence artificielle", "Intelligence artificielle", K.TYPES_IA,
                   "Reconnaître le type d'apprentissage adapté à un problème (dont le sien : le renforcement)."),
]
PAR_CLE = {m.cle: m for m in MATIERES}


# ==========================================
# Le cerveau et l'apprentissage
# ==========================================
class Cerveau(nn.Module):
    def __init__(self, dim, n_actions, cache=128):
        super().__init__()
        self.reseau = nn.Sequential(nn.Linear(dim, cache), nn.ReLU(), nn.Linear(cache, cache), nn.ReLU(),
                                    nn.Linear(cache, n_actions))

    def forward(self, x):
        return self.reseau(x)


def examen(matiere, n=400, seed=12345):
    rng = np.random.default_rng(seed)
    x, y, _ = zip(*(matiere.generer(rng) for _ in range(n)))
    return torch.tensor(np.array(x)), np.array(y)


def precision(cerveau, epreuve):
    x, y = epreuve
    with torch.no_grad():
        return float((cerveau(x).argmax(1).numpy() == y).mean())


def entrainer(matiere, pas=None, batch=64, lr=2e-3, seed=0, callback=None):
    """Apprentissage par renforcement (bandit contextuel) avec mémoire profonde."""
    pas = pas or max(4000, 600 * len(matiere.actions))   # plus de réponses possibles = plus d'essais
    rng = np.random.default_rng(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    cerveau = Cerveau(matiere.dim, len(matiere.actions))
    optimiseur = torch.optim.Adam(cerveau.parameters(), lr=lr)
    memoire = deque(maxlen=20_000)
    epreuve = examen(matiere)
    historique = [{"pas": 0, "precision": precision(cerveau, epreuve)}]
    for t in range(1, pas + 1):
        epsilon = max(0.05, 1 - t / (0.6 * pas))
        x, y, _ = matiere.generer(rng)
        if random.random() < epsilon:
            action = random.randrange(len(matiere.actions))     # curiosité
        else:
            with torch.no_grad():
                action = int(cerveau(torch.from_numpy(x)).argmax())
        memoire.append((x, action, 1.0 if action == y else -1.0))
        if len(memoire) >= batch:
            s, a, r = zip(*random.sample(memoire, batch))
            prediction = cerveau(torch.tensor(np.array(s))).gather(1, torch.tensor(a).unsqueeze(1)).squeeze(1)
            perte = nn.functional.mse_loss(prediction, torch.tensor(r))
            optimiseur.zero_grad()
            perte.backward()
            optimiseur.step()
        if t % 250 == 0:
            historique.append({"pas": t, "precision": precision(cerveau, epreuve)})
            if callback:
                callback(t, pas, historique[-1]["precision"])
    return cerveau, historique


def sauvegarder(matiere, cerveau, historique):
    DOSSIER_CERVEAUX.mkdir(exist_ok=True)
    torch.save({"etat": cerveau.state_dict(), "historique": historique}, DOSSIER_CERVEAUX / f"{matiere.cle}.pt")


def charger(cle):
    chemin = DOSSIER_CERVEAUX / f"{cle}.pt"
    if not chemin.exists():
        return None, None
    m = PAR_CLE[cle]
    donnees = torch.load(chemin, weights_only=True)
    cerveau = Cerveau(m.dim, len(m.actions))
    cerveau.load_state_dict(donnees["etat"])
    cerveau.eval()
    return cerveau, donnees["historique"]


def repondre(cle, entree, cerveau=None, top=3):
    """IA AISSA répond : entree est un texte (matières textuelles) ou un vecteur de caractéristiques."""
    m = PAR_CLE[cle]
    cerveau = cerveau or charger(cle)[0]
    if cerveau is None:
        raise ValueError(f"IA AISSA n'a pas encore étudié la matière « {m.nom} ».")
    x = m.perception(entree) if m.texte else np.asarray(entree, np.float32)
    with torch.no_grad():
        proba = torch.softmax(cerveau(torch.from_numpy(x)) * 3, dim=0).numpy()
    ordre = proba.argsort()[::-1][:top]
    return [{"reponse": m.actions[i], "confiance": round(float(proba[i]), 3)} for i in ordre]
