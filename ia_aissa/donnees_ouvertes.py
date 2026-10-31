"""
Données ouvertes sur l'économie marocaine, lues à leur source officielle, avec leur licence.

Banque mondiale — World Development Indicators (API publique api.worldbank.org, licence CC BY 4.0 : réutilisation
libre avec citation de la source ; pas de robots.txt, donc aucune restriction pour les robots ; vérifié le
31/10/2026). Une seule requête rapporte tous les indicateurs : PIB, croissance, inflation, chômage, population,
commerce extérieur, dette, transferts des Marocains du monde.

Le texte obtenu est rangé dans sa mémoire de lecture (comme un livre) : IA AISSA peut alors répondre « l'inflation au
Maroc en 2025 » en citant la source et l'année. Mise à jour au plus une fois par semaine (les séries changent peu).
"""

import datetime
import json

from .bibliotheque import ErreurBroutage

SOURCE = "Banque mondiale — Indicateurs du développement (Maroc)"
LICENCE = "Banque mondiale, World Development Indicators, licence CC BY 4.0 (api.worldbank.org)"
INDICATEURS = {
    "NY.GDP.MKTP.CD": ("PIB du Maroc (dollars courants)", "dollars"),
    "NY.GDP.MKTP.KD.ZG": ("Croissance du PIB du Maroc (% par an)", "%"),
    "NY.GDP.PCAP.CD": ("PIB par habitant du Maroc (dollars courants)", "dollars"),
    "FP.CPI.TOTL.ZG": ("Inflation au Maroc, prix à la consommation (% par an)", "%"),
    "SL.UEM.TOTL.ZS": ("Taux de chômage au Maroc (% de la population active, estimation OIT)", "%"),
    "SP.POP.TOTL": ("Population totale du Maroc", "habitants"),
    "NE.EXP.GNFS.ZS": ("Exportations de biens et services du Maroc (% du PIB)", "%"),
    "NE.IMP.GNFS.ZS": ("Importations de biens et services du Maroc (% du PIB)", "%"),
    "GC.DOD.TOTL.GD.ZS": ("Dette de l'administration centrale du Maroc (% du PIB)", "%"),
    "BX.TRF.PWKR.CD.DT": ("Transferts des Marocains du monde reçus (dollars courants)", "dollars"),
}
URL = "https://api.worldbank.org/v2/country/MAR/indicator/{codes}"
FREQUENCE_JOURS = 7


def nombre(valeur, unite):
    if unite == "%":
        return f"{valeur:.1f}".replace(".", ",") + " %"
    if valeur >= 1e9:
        return f"{valeur / 1e9:.1f}".replace(".", ",") + (" milliards de dollars" if unite == "dollars" else " milliards")
    if valeur >= 1e6:
        return f"{valeur / 1e6:.1f}".replace(".", ",") + (" millions d'habitants" if unite == "habitants" else " millions")
    return f"{valeur:,.0f}".replace(",", " ") + (" dollars" if unite == "dollars" else "")


def lire_banque_mondiale(brouteur, annees=6):
    """Une requête polie (robots.txt, délai) à l'API ; renvoie (source, texte, séries)."""
    brut = brouteur.visiter(URL.format(codes=";".join(INDICATEURS)),
                            {"format": "json", "source": 2, "mrv": annees, "per_page": 500})
    try:
        entete, lignes = json.loads(brut)
    except (ValueError, TypeError) as e:
        raise ErreurBroutage(f"Réponse inattendue de la Banque mondiale ({type(e).__name__}).") from e
    series = {}
    for l in lignes or []:
        if l.get("value") is not None:
            series.setdefault(l["indicator"]["id"], []).append((int(l["date"]), float(l["value"])))
    if not series:
        raise ErreurBroutage("La Banque mondiale n'a renvoyé aucune donnée.")
    mise_a_jour = entete.get("lastupdated", "")
    phrases = [f"{SOURCE}. Source : {LICENCE}, données mises à jour le {mise_a_jour}."]
    for code, (libelle, unite) in INDICATEURS.items():
        points = sorted(series.get(code, []), reverse=True)
        if points:
            derniere_annee, derniere = points[0]
            historique = " ; ".join(f"{a} : {nombre(v, unite)}" for a, v in points)
            phrases.append(f"{libelle} : {nombre(derniere, unite)} en {derniere_annee}. Évolution : {historique}.")
    return SOURCE, "\n\n".join(phrases), series


def repas_donnees_ouvertes(memoire, brouteur=None, aujourdhui=None, forcer=False):
    """Met à jour sa mémoire de lecture avec les dernières données ouvertes (au plus une fois par semaine)."""
    aujourdhui = aujourdhui or datetime.date.today()
    derniere = memoire.reglage("donnees_ouvertes:derniere")
    if derniere and not forcer:
        avant = datetime.date.fromisoformat(json.loads(derniere)["date"])
        if (aujourdhui - avant).days < FREQUENCE_JOURS:
            return {**json.loads(derniere), "deja": True}
    if brouteur is None:
        from .broutage import Brouteur
        brouteur = Brouteur()
    source, texte, series = lire_banque_mondiale(brouteur)
    from .lecture import decouper
    passages = [p.strip() for p in texte.split("\n\n") if p.strip()]       # une phrase par indicateur : précis
    memoire.garder_passages("IA AISSA", source, passages or decouper(texte))
    bilan = {"date": aujourdhui.isoformat(), "source": source, "indicateurs": len(series),
             "annee_la_plus_recente": max(a for points in series.values() for a, _ in points)}
    memoire.definir_reglage("donnees_ouvertes:derniere", json.dumps(bilan, ensure_ascii=False))
    return bilan
