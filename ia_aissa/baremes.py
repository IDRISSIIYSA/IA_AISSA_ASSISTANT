"""
Les barèmes fiscaux marocains par année, avec leur base légale et leur source.

Seules les périodes vérifiées sont encodées (date de vérification et sources indiquées). Pour une année non couverte,
IA AISSA le dit au lieu d'inventer : l'administrateur peut alors ajouter un barème lu dans un texte officiel
(Bulletin officiel, loi de finances de l'année), avec sa source, ou lui faire lire ce texte.
"""

import json

VERIFIE_LE = "30/10/2026"

# IR annuel : (plafond de la tranche, taux, somme à déduire)
IR = [
    {"de": 2010, "a": 2024, "loi": "Loi de finances n° 48-09 pour l'année 2010 ; Code général des impôts, art. 73-I",
     "bareme": [(30_000, 0.00, 0), (50_000, 0.10, 3_000), (60_000, 0.20, 8_000), (80_000, 0.30, 14_000),
                (180_000, 0.34, 17_200), (float("inf"), 0.38, 24_400)],
     "sources": ["kontabl.ma — barème de l'IR", "dreamjob.ma — calcul de l'IR (barème LF 2010 jusqu'en 2024)"]},
    {"de": 2025, "a": 2026, "loi": "Loi de finances n° 60-24 pour l'année 2025, art. 8 ; CGI, art. 73-I "
                                    "(inchangé en 2026)",
     "bareme": [(40_000, 0.00, 0), (60_000, 0.10, 4_000), (80_000, 0.20, 10_000), (100_000, 0.30, 18_000),
                (180_000, 0.34, 22_000), (float("inf"), 0.37, 27_400)],
     "sources": ["clicpaie.ma — barème IR 2026", "humantal.ma — barème IR 2026", "fiscalitemaroc.com"]},
]
TVA = [
    {"de": 2021, "a": 2023, "loi": "Code général des impôts, art. 98 et 99 (avant la réforme de la LF 2024)",
     "taux": {"normal": 0.20, "réduits": [0.14, 0.10, 0.07]},
     "sources": ["Wikipédia — TVA au Maroc", "upsilon-consulting.com — réforme TVA 2024-2026"],
     "remarque": "Quatre taux : 20 % (normal), 14 %, 10 % et 7 %, selon les produits et services."},
    {"de": 2024, "a": 2025, "loi": "Loi de finances 2024 (réforme progressive de la TVA) ; CGI, art. 98 et 99",
     "taux": {"normal": 0.20, "réduits": [0.10, "7 % et 14 % en voie de suppression selon les produits"]},
     "sources": ["upsilon-consulting.com — réforme TVA 2024-2026", "hespress.com — réforme progressive 2024-2026"],
     "remarque": "Période de transition : le calendrier exact dépend de chaque produit (à vérifier dans le CGI)."},
    {"de": 2026, "a": 2026, "loi": "Lois de finances 2024 à 2026 ; CGI, art. 98 et 99",
     "taux": {"normal": 0.20, "réduits": [0.10]},
     "sources": ["upsilon-consulting.com — guide pratique TVA 2026", "hespress.com"],
     "remarque": "Deux taux seulement depuis le 1er janvier 2026 : 20 % et 10 % (7 % et 14 % supprimés)."},
]
IS = [
    {"de": 2026, "a": 2026, "loi": "Loi de finances n° 50-22 pour 2023 (convergence 2023-2026) ; CGI, art. 19",
     "taux": {"bénéfice < 100 MDH": 0.20, "bénéfice ≥ 100 MDH": 0.35, "banques et assurances": 0.40},
     "cotisation_minimale": {"taux": 0.0025, "minimum": 3_000, "loi": "CGI, art. 144"},
     "sources": ["aafir.ma — taux IS 2023-2026", "upsilon-consulting.com — cotisation minimale 2026"]},
]
BAREMES = {"ir": IR, "tva": TVA, "is": IS}


def periode(impot, annee, memoire=None):
    """Le barème en vigueur pour l'année (ajouts de l'administrateur compris), ou None s'il n'est pas vérifié."""
    for p in BAREMES[impot] + ajouts_admin(memoire, impot):
        if p["de"] <= annee <= p["a"]:
            return p
    return None


def annees_couvertes(impot, memoire=None):
    return sorted({a for p in BAREMES[impot] + ajouts_admin(memoire, impot) for a in range(p["de"], p["a"] + 1)})


def ajouts_admin(memoire, impot):
    """Barèmes ajoutés par l'administrateur (lus dans un texte officiel), gardés dans la base avec leur source."""
    if memoire is None:
        return []
    ajouts = []
    for _, v in sorted(memoire.reglages(f"bareme:{impot}:").items()):
        p = json.loads(v)
        if impot == "ir":
            p["bareme"] = [(float("inf") if t[0] is None else t[0], t[1], t[2]) for t in p["bareme"]]
        ajouts.append(p)
    return ajouts


def ajouter_bareme_ir(memoire, de, a, loi, source, tranches):
    """tranches : [(plafond ou None pour la dernière, taux décimal, somme à déduire)]."""
    if not loi or not source:
        raise ValueError("La loi et la source sont obligatoires : un barème sans référence n'est pas accepté.")
    memoire.definir_reglage(f"bareme:ir:{de}-{a}", json.dumps(
        {"de": int(de), "a": int(a), "loi": loi, "sources": [source], "bareme": [list(t) for t in tranches],
         "ajoute_par": "administrateur"}, ensure_ascii=False))


def ir_annee(revenu_net_imposable, annee, memoire=None):
    """IR annuel selon le barème de l'année ; lève ValueError si l'année n'est pas couverte."""
    p = periode("ir", annee, memoire)
    if p is None:
        raise ValueError(f"Barème de l'IR {annee} non vérifié : je ne l'invente pas. Années disponibles : "
                         f"{', '.join(map(str, annees_couvertes('ir', memoire)))}.")
    r = float(revenu_net_imposable)
    plafond, taux, deduction = next(t for t in p["bareme"] if r <= t[0])
    ir = max(0.0, r * taux - deduction)
    return {"annee": annee, "revenu": r, "taux_marginal": taux, "somme_a_deduire": deduction, "ir_annuel": round(ir, 2),
            "ir_mensuel": round(ir / 12, 2), "taux_moyen": round(ir / r, 4) if r else 0.0, "periode": p}
