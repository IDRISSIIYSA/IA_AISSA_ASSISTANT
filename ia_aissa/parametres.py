"""
Le registre des taux et seuils utilisés par les simulations : une seule liste, avec pour chacun sa valeur, sa date
d'effet, son texte légal, sa source et sa date de vérification.

Mises à jour : l'administrateur enregistre une nouvelle valeur avec son texte légal et sa source (obligatoires) ; elle
est appliquée aussitôt à toutes les simulations (les calculs lisent ces valeurs au moment du calcul) et l'historique
garde chaque changement. Une alerte signale une nouvelle année dont la loi de finances n'est pas encore intégrée.
"""

import datetime
import json

import pandas as pd

from . import baremes as B
from . import connaissances as K
from . import obligations as O
from . import simulations as S

VERIFIE_LE = B.VERIFIE_LE
CNSS = "Dahir portant loi n° 1-72-184 (régime de sécurité sociale) ; décrets de fixation des taux"
AMO = "Loi n° 65-00 portant code de la couverture médicale de base"

# (clé, module, attribut, libellé, unité, depuis, texte légal, source)
PARAMETRES = [
    ("smig_horaire", K, "SMIG_HORAIRE_2026", "SMIG horaire (secteur non agricole)", "DH/heure", "01/01/2026",
     "Décret de revalorisation du SMIG ; Code du travail, art. 356", "Humantal, Cabinet Dami — paie 2026"),
    ("heures_legales_mois", K, "HEURES_LEGALES_MOIS", "Durée légale du travail", "heures/mois", "—",
     "Code du travail, art. 184 (44 h par semaine)", "Code du travail"),
    ("plafond_cnss", K, "PLAFOND_CNSS_MENSUEL", "Plafond mensuel CNSS (prestations sociales)", "DH/mois", "—",
     CNSS, "Humantal — taux CNSS 2026"),
    ("cnss_salarie", K, "CNSS_SALARIE", "CNSS part salariale (plafonnée)", "taux", "—", CNSS, "Humantal, Nexora"),
    ("cnss_employeur", K, "CNSS_EMPLOYEUR", "CNSS part patronale (plafonnée)", "taux", "—", CNSS, "Humantal, Nexora"),
    ("amo_salarie", K, "AMO_SALARIE", "AMO part salariale", "taux", "—", AMO, "Humantal, Nexora"),
    ("amo_employeur", K, "AMO_EMPLOYEUR", "AMO part patronale", "taux", "—", AMO, "Humantal, Nexora"),
    ("allocations_familiales", K, "ALLOCATIONS_FAMILIALES_EMPLOYEUR", "Allocations familiales (employeur)", "taux",
     "—", CNSS, "Humantal, Nexora"),
    ("formation_professionnelle", K, "TAXE_FORMATION_PROFESSIONNELLE", "Taxe de formation professionnelle", "taux",
     "—", "Dahir n° 1-74-331 (taxe de formation professionnelle)", "Humantal, Nexora"),
    ("plafond_frais_pro", K, "PLAFOND_FRAIS_PRO_ANNUEL", "Plafond des frais professionnels (salaires)", "DH/an",
     "01/01/2025", "CGI, art. 59", "clicpaie.ma, Humantal"),
    ("taux_cotisation_minimale", K, "TAUX_CM", "Cotisation minimale (taux de droit commun)", "taux", "—",
     "CGI, art. 144", "Upsilon Consulting — cotisation minimale 2026"),
    ("minimum_cotisation_minimale", K, "MINIMUM_CM", "Cotisation minimale : montant plancher", "DH", "—",
     "CGI, art. 144", "Upsilon Consulting"),
    ("seuil_tva_mensuelle", O, "SEUIL_TVA_MENSUELLE", "Seuil de la déclaration mensuelle de TVA", "DH de CA", "—",
     "CGI, art. 108", "CGI"),
    ("seuil_petites_cessions", S, "SEUIL_PETITES_CESSIONS", "Profit foncier : exonération des petites cessions",
     "DH par an", "—", "CGI, art. 63", "Upsilon Consulting — profit foncier 2026"),
    ("plafond_residence_principale", S, "PLAFOND_RESIDENCE_PRINCIPALE",
     "Profit foncier : plafond de la résidence principale exonérée", "DH", "LF 2023", "CGI, art. 63 et 144-II",
     "Upsilon Consulting — profit foncier 2026"),
    ("transport_exonere", K, "TRANSPORT_EXONERE_URBAIN", "Indemnité de transport exonérée (zone urbaine)", "DH/mois",
     "—", "CGI, art. 57 ; note circulaire de la DGI", "cabinets de paie 2026"),
]
PAR_CLE = {p[0]: p for p in PARAMETRES}
_ORIGINAUX = {p[0]: getattr(p[1], p[2]) for p in PARAMETRES}


def _cle_reglage(cle):
    return f"parametre:{cle}"


def historique(memoire, cle):
    if memoire is None:
        return []
    brut = memoire.reglage(_cle_reglage(cle))
    return json.loads(brut) if brut else []


def mettre_a_jour(memoire, cle, valeur, depuis, texte_legal, source, auteur="administrateur"):
    """Enregistre une nouvelle valeur (texte légal et source obligatoires) et l'applique aussitôt."""
    if cle not in PAR_CLE:
        raise ValueError(f"Paramètre inconnu : {cle}")
    if not str(texte_legal).strip() or not str(source).strip():
        raise ValueError("Le texte légal et la source sont obligatoires : une valeur sans référence n'est pas acceptée.")
    valeur = float(valeur)
    if valeur < 0 or (PAR_CLE[cle][4] == "taux" and valeur >= 1):
        raise ValueError("Valeur impossible (un taux s'écrit en décimal : 0,0448 pour 4,48 %).")
    h = historique(memoire, cle)
    h.append({"valeur": valeur, "depuis": str(depuis), "texte_legal": texte_legal.strip(), "source": source.strip(),
              "auteur": auteur, "enregistre_le": datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M")})
    memoire.definir_reglage(_cle_reglage(cle), json.dumps(h, ensure_ascii=False))
    appliquer(memoire)
    return h[-1]


def annuler(memoire, cle):
    """Revient à la valeur précédente (ou à la valeur vérifiée d'origine)."""
    h = historique(memoire, cle)[:-1]
    memoire.definir_reglage(_cle_reglage(cle), json.dumps(h, ensure_ascii=False))
    appliquer(memoire)


def appliquer(memoire):
    """Applique à tous les calculs la dernière valeur enregistrée de chaque paramètre (ou l'originale)."""
    for cle, module, attribut, *_ in PARAMETRES:
        h = historique(memoire, cle)
        valeur = h[-1]["valeur"] if h else _ORIGINAUX[cle]
        if isinstance(_ORIGINAUX[cle], int) and float(valeur).is_integer():
            valeur = int(valeur)
        setattr(module, attribut, valeur)


def afficher_valeur(valeur, unite):
    if unite == "taux":
        return f"{valeur * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " %"
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",").removesuffix(",00") + f" {unite}"


def registre(memoire=None, aujourdhui=None):
    """Le tableau de tous les taux en vigueur, avec leur origine et leur statut de vérification."""
    aujourdhui = aujourdhui or datetime.date.today()
    verifie = datetime.datetime.strptime(VERIFIE_LE, "%d/%m/%Y").date()
    lignes = []
    for cle, module, attribut, libelle, unite, depuis, texte, source in PARAMETRES:
        h = historique(memoire, cle)
        if h:
            d = h[-1]
            lignes.append({"Paramètre": libelle, "Valeur": afficher_valeur(d["valeur"], unite), "Depuis": d["depuis"],
                           "Texte légal": d["texte_legal"], "Source": d["source"],
                           "Vérifié le": d["enregistre_le"][:10], "Statut": "🛠️ mis à jour par l'administrateur",
                           "Clé": cle})
        else:
            a_revoir = (aujourdhui - verifie).days > 365 or aujourdhui.year > verifie.year
            lignes.append({"Paramètre": libelle, "Valeur": afficher_valeur(_ORIGINAUX[cle], unite), "Depuis": depuis,
                           "Texte légal": texte, "Source": source, "Vérifié le": VERIFIE_LE,
                           "Statut": "⚠️ à revérifier (nouvelle année)" if a_revoir else "✅ vérifié", "Clé": cle})
    return pd.DataFrame(lignes)


def alertes(memoire=None, aujourdhui=None):
    """Ce qui doit être mis à jour : loi de finances de l'année non intégrée, taux à revérifier."""
    aujourdhui = aujourdhui or datetime.date.today()
    messages = []
    annees_ir = B.annees_couvertes("ir", memoire)
    if aujourdhui.year > max(annees_ir):
        messages.append(f"📅 Loi de finances {aujourdhui.year} non intégrée : le barème de l'IR s'arrête à "
                        f"{max(annees_ir)}. Ajoutez le barème {aujourdhui.year} (Bulletin officiel) dans l'administration.")
    for impot in ("tva", "is"):
        if aujourdhui.year > max(B.annees_couvertes(impot, memoire)):
            messages.append(f"📅 Taux de {impot.upper()} {aujourdhui.year} à vérifier dans la loi de finances "
                            f"{aujourdhui.year}.")
    if aujourdhui.year not in S.RAS_DIVIDENDES:
        messages.append(f"📅 Taux de retenue sur dividendes {aujourdhui.year} à vérifier.")
    a_revoir = registre(memoire, aujourdhui)
    n = int(a_revoir["Statut"].str.startswith("⚠️").sum())
    if n:
        messages.append(f"🔎 {n} taux sociaux et fiscaux à revérifier pour {aujourdhui.year} (SMIG, CNSS, AMO…).")
    return messages
