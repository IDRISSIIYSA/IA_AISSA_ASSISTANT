"""
Coefficients de réévaluation du prix d'acquisition pour l'IR sur les profits fonciers (CGI, art. 65-II), fixés chaque
année par arrêté du ministre de l'Économie et des Finances.

Année 2026 (cessions réalisées en 2026) : arrêté de la ministre de l'économie et des finances n° 230-26 du 6 février
2026, Bulletin officiel n° 7488 du 5 mars 2026 (édition de traduction officielle, p. 258-259 ; texte arabe : BO n° 7486
du 26 février 2026). Les 80 coefficients (1946 à 2025) ont été comparés un à un au PDF officiel (sgg.gov.ma) le
26/11/2026 : identiques au tableau recopié le 06/11/2026 de CAE Experts et Le Matin.

Acquisitions de 1945 et avant : l'arrêté écrit seulement « Année 1945 et années antérieures : 3% », sans en préciser
l'application — non calculé (saisie manuelle, d'après le notaire ou la DGI).

Chaque année, l'administrateur ajoute le nouveau tableau (arrêté de février) depuis l'administration (onglet 📈
Apprentissage) en le collant tel quel, avec sa source : il est vérifié (années consécutives jusqu'à l'année précédant la
vente, coefficients ≥ 1 et décroissants à long terme), gardé en base et chargé au démarrage. Les tableaux des années
passées restent : une vente de 2026 garde le tableau 2026 même quand celui de 2027 est ajouté.
"""

import json
import re
from datetime import datetime, timezone

ANNEE_DU_TABLEAU = 2026
SOURCE = ("Arrêté n° 230-26 du 6 février 2026 (Bulletin officiel n° 7488 du 5 mars 2026, p. 258-259 ; texte arabe : "
          "BO n° 7486 du 26 février 2026), vérifié sur le BO le 26/11/2026")
_VALEURS = """
1946 57,773 1947 44,991 1948 31,717 1949 25,479 1950 24,885 1951 22,105 1952 18,862 1953 18,262 1954 19,916
1955 18,862 1956 16,018 1957 16,880 1958 13,803 1959 13,803 1960 13,280 1961 12,671 1962 12,459 1963 11,463
1964 11,032 1965 10,660 1966 10,705 1967 10,898 1968 10,822 1969 10,453 1970 10,348 1971 9,870 1972 9,366
1973 9,247 1974 8,264 1975 7,160 1976 6,536 1977 6,016 1978 5,407 1979 5,020 1980 4,646 1981 4,143 1982 3,722
1983 3,576 1984 3,085 1985 2,921 1986 2,655 1987 2,609 1988 2,550 1989 2,460 1990 2,300 1991 2,101 1992 1,999
1993 1,896 1994 1,819 1995 1,732 1996 1,686 1997 1,673 1998 1,628 1999 1,614 2000 1,585 2001 1,569 2002 1,536
2003 1,523 2004 1,492 2005 1,478 2006 1,432 2007 1,402 2008 1,351 2009 1,309 2010 1,296 2011 1,285 2012 1,270
2013 1,248 2014 1,243 2015 1,223 2016 1,205 2017 1,196 2018 1,175 2019 1,173 2020 1,164 2021 1,150 2022 1,078
2023 1,017 2024 1,008 2025 1,000
"""
_mots = _VALEURS.split()
COEFFICIENTS_2026 = {int(a): float(c.replace(",", ".")) for a, c in zip(_mots[::2], _mots[1::2])}


CLE_TABLEAU = "coefficients_fonciers:{}"
PREMIERE_ANNEE = 1946
_TABLEAUX = {ANNEE_DU_TABLEAU: {"valeurs": COEFFICIENTS_2026, "source": SOURCE}}


def lire_tableau(texte, annee_cession):
    """Le tableau collé (« 1946 57,773 1947 44,991 … », une année par ligne ou en colonnes) → {année: coefficient}.
    Lève ValueError avec la raison si le tableau est incomplet ou invraisemblable."""
    paires = re.findall(r"\b(19[4-9]\d|20\d\d)\s*[:;|\t ]\s*(\d{1,3}(?:[.,]\d{1,4})?)\b", texte or "")
    valeurs = {int(a): float(c.replace(",", ".")) for a, c in paires}
    attendues = set(range(PREMIERE_ANNEE, annee_cession))
    manquantes = sorted(attendues - set(valeurs))
    if manquantes:
        raise ValueError(f"{len(manquantes)} année(s) manquante(s) entre {PREMIERE_ANNEE} et {annee_cession - 1} "
                         f"(par exemple {', '.join(map(str, manquantes[:5]))}).")
    en_trop = sorted(set(valeurs) - attendues)
    if en_trop:
        raise ValueError(f"Année(s) hors du tableau d'une vente en {annee_cession} : {', '.join(map(str, en_trop[:5]))}.")
    if any(v < 1 for v in valeurs.values()):
        raise ValueError("Un coefficient est inférieur à 1 : vérifiez la virgule décimale.")
    if valeurs[PREMIERE_ANNEE] < 5 * valeurs[annee_cession - 1]:
        raise ValueError("Les coefficients ne décroissent pas des années anciennes vers les récentes : tableau inversé ?")
    return valeurs


def enregistrer_tableau(memoire, annee_cession, texte, source, auteur="administrateur"):
    """Vérifie, garde en base et charge le tableau des ventes de `annee_cession`. Renvoie le nombre d'années."""
    if not (source or "").strip():
        raise ValueError("Indiquez la source (arrêté, Bulletin officiel, date).")
    valeurs = lire_tableau(texte, int(annee_cession))
    donnees = {"valeurs": {str(a): c for a, c in valeurs.items()}, "source": source.strip(), "auteur": auteur,
               "ajoute_le": datetime.now(timezone.utc).strftime("%d/%m/%Y")}
    memoire.definir_reglage(CLE_TABLEAU.format(int(annee_cession)), json.dumps(donnees, ensure_ascii=False))
    _TABLEAUX[int(annee_cession)] = {"valeurs": valeurs, "source": donnees["source"], "ajoute_le": donnees["ajoute_le"]}
    return len(valeurs)


def charger(memoire):
    """Charge les tableaux ajoutés par l'administrateur (au démarrage du serveur). Renvoie les années disponibles."""
    for cle, brut in (memoire.reglages("coefficients_fonciers:") if memoire is not None else {}).items():
        try:
            annee, d = int(cle.split(":")[1]), json.loads(brut)
            if annee != ANNEE_DU_TABLEAU:              # le tableau 2026 vérifié dans le code reste la référence
                _TABLEAUX[annee] = {"valeurs": {int(a): c for a, c in d["valeurs"].items()}, "source": d["source"],
                                    "ajoute_le": d.get("ajoute_le")}
        except (ValueError, KeyError, IndexError):
            continue
    return annees_disponibles()


def annees_disponibles():
    return sorted(_TABLEAUX)


def derniere_annee():
    return max(_TABLEAUX)


def source(annee_cession):
    t = _TABLEAUX.get(annee_cession)
    return t["source"] if t else None


def coefficient(annee_acquisition, annee_cession=None):
    """Le coefficient officiel du tableau de l'année de la vente (par défaut le plus récent), ou None (pas de tableau
    pour cette année de vente, ou acquisition avant 1946)."""
    annee_cession = annee_cession or derniere_annee()
    tableau = _TABLEAUX.get(annee_cession)
    if tableau is None:
        return None
    if annee_acquisition >= annee_cession:
        return 1.0                                 # acquis l'année même de la cession : pas de réévaluation
    return tableau["valeurs"].get(int(annee_acquisition))
