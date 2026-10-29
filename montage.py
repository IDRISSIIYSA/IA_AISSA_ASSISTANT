"""
Montage automatique d'un contrôle de gestion à partir de données brutes, quelle que soit leur structure.

Structures reconnues (CSV ou Excel, une ou plusieurs feuilles) :
  - "colonnes" : une colonne par indicateur (budget, réel, CA…), une ligne par période/centre ;
  - "journal"  : écritures comptables (date, compte, débit/crédit ou montant, section analytique…) ;
  - "large"    : un tableau avec les mois en colonnes (Janv, Févr… ou 2024-01, 2024-02…).

Le scénario (budget / réel) est déduit d'une colonne "Type", du libellé des lignes, de l'en-tête
des colonnes ou du nom de la feuille. Si aucun budget n'existe, il est reconstruit à partir de
l'historique (même mois de l'année précédente, sinon moyenne des 3 mois précédents).

Toutes les structures sont ramenées au format standard :
    periode, centre, budget, reel, revenus
"""

import io
import re
import unicodedata

import numpy as np
import pandas as pd

FORMATS = {
    "colonnes": "Tableau par indicateurs (budget, réel, CA en colonnes)",
    "journal": "Journal / grand livre (écritures comptables)",
    "large": "Tableau mensuel (mois en colonnes)",
    "ignorer": "Ignorer cette feuille",
}

# Libellés affichés dans l'interface, dans l'ordre de détection (les plus spécifiques d'abord)
ROLES_AFFICHES = {
    "budget": "Budget", "reel": "Réel (charges)", "revenus": "Revenus / CA",
    "debit": "Débit", "credit": "Crédit", "montant": "Montant",
    "periode": "Période / date", "annee": "Année", "centre": "Centre / section",
    "scenario": "Type (budget/réel)", "compte": "Compte", "libelle": "Libellé",
}

ALIAS = {
    "budget": ["budget", "budget_prevu", "prevu", "previsionnel", "prevision", "objectif", "budgete", "bp",
               "montant_budget", "budget_annuel"],
    "reel": ["reel", "realise", "cout_reel", "couts_reels", "actual", "depenses", "charges", "cout", "couts",
             "realisation", "montant_reel", "charges_reelles"],
    "revenus": ["revenus", "revenu", "ca", "chiffre_affaires", "chiffre_d_affaires", "revenue", "ventes",
                "produits", "recettes", "ca_reel"],
    "debit": ["debit", "mouvement_debit", "montant_debit"],
    "credit": ["credit", "mouvement_credit", "montant_credit"],
    "montant": ["montant", "amount", "valeur", "value", "solde", "mt", "montant_ttc", "montant_ht"],
    "periode": ["periode", "date", "mois", "month", "period", "date_ecriture", "date_piece", "date_operation",
                "ecrituredate", "piecedate"],
    "annee": ["annee", "year", "exercice"],
    "centre": ["centre", "centre_cout", "centre_de_cout", "centre_de_couts", "cdc", "departement", "service",
               "section", "section_analytique", "analytique", "axe_analytique", "projet", "site", "activite",
               "division", "entite", "rubrique", "poste", "direction", "unite"],
    "scenario": ["type", "scenario", "version", "budget_reel", "statut", "type_donnee", "nature_donnee"],
    "compte": ["compte", "num_compte", "numero_compte", "n_compte", "no_compte", "account", "compte_general",
               "compte_comptable", "code_compte", "comptenum"],
    "libelle": ["libelle", "designation", "description", "intitule", "label", "ecriturelib", "libelle_ecriture",
                "comptelib"],
}
ROLES_NUMERIQUES = {"budget", "reel", "revenus", "debit", "credit", "montant"}

MOIS = {
    "janvier": 1, "janv": 1, "jan": 1, "january": 1,
    "fevrier": 2, "fevr": 2, "fev": 2, "feb": 2, "february": 2,
    "mars": 3, "mar": 3, "march": 3,
    "avril": 4, "avr": 4, "apr": 4, "april": 4,
    "mai": 5, "may": 5,
    "juin": 6, "jun": 6, "june": 6,
    "juillet": 7, "juil": 7, "jul": 7, "july": 7,
    "aout": 8, "aou": 8, "aug": 8, "august": 8,
    "septembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octobre": 10, "oct": 10, "october": 10,
    "novembre": 11, "nov": 11, "november": 11,
    "decembre": 12, "dec": 12, "december": 12,
}

MOTS_PRODUITS = {"ca", "chiffre", "vente", "ventes", "recette", "recettes", "produit", "produits", "revenu",
                 "revenus", "sales", "revenue", "facturation"}
MOTS_TOTAUX = {"total", "totaux", "sous_total", "soustotal", "cumul", "ensemble"}


# ==========================================
# Outils de lecture
# ==========================================
def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def cle(valeur):
    """'Budget prévu (€)' -> 'budget_prevu'"""
    texte = sans_accents(str(valeur)).lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", texte).strip("_")


def _nombre(v):
    if v is None or isinstance(v, bool):
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    if not isinstance(v, str):
        return np.nan
    t = v.strip()
    if not t or re.search(r"\d\s*[/:]\s*\d|\d-\d", t):   # dates et heures ne sont pas des montants
        return np.nan
    negatif = t.startswith("(") and t.endswith(")")
    t = re.sub(r"[^\d,.\-]", "", t)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".") if t.count(",") == 1 else t.replace(",", "")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    try:
        n = float(t)
    except ValueError:
        return np.nan
    return -abs(n) if negatif else n


def en_nombres(serie):
    """Convertit '1 234,56 €', '(500)', '1.234,5' … en nombres."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    return serie.map(_nombre).astype(float)


def part_numerique(serie):
    remplies = serie.notna().sum()
    return en_nombres(serie).notna().sum() / remplies if remplies else 0.0


def classer_scenario(texte):
    k = cle(texte)
    mots = set(k.split("_"))
    if re.search(r"budget|previ|objectif|forecast|prevu", k) or mots & {"bp", "plan", "cible"}:
        return "budget"
    if re.search(r"reel|realis|actual|effectif|constat", k):
        return "reel"
    return None


def est_produit(texte):
    return bool(set(cle(texte).split("_")) & MOTS_PRODUITS)


def est_total(texte):
    k = cle(texte)
    return bool(set(k.split("_")) & MOTS_TOTAUX) or k.startswith("sous_total")


def mois_depuis_entete(entete):
    """'Janv 2024', '2024-01', '01/2024', 'M03', datetime… -> ('2024-01' ou 'M03', scénario éventuel)."""
    if isinstance(entete, (pd.Timestamp, np.datetime64)) or hasattr(entete, "month") and hasattr(entete, "year"):
        return pd.Timestamp(entete).strftime("%Y-%m"), None
    k = cle(entete)
    if not k:
        return None, None
    scenario = classer_scenario(entete)
    m = re.match(r"^((?:19|20)\d\d)_(\d{1,2})(?:_|$)", k)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{m.group(1)}-{int(m.group(2)):02d}", scenario
    m = re.match(r"^(\d{1,2})_((?:19|20)\d\d)(?:_|$)", k)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{m.group(2)}-{int(m.group(1)):02d}", scenario
    m = re.match(r"^m_?(\d{1,2})(?:_|$)", k)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"M{int(m.group(1)):02d}", scenario
    mots = k.split("_")
    if len(mots) > 4:
        return None, None
    mois = next((MOIS[w] for w in mots if w in MOIS), None)
    if mois is None:
        return None, None
    annee = next((w for w in mots if re.fullmatch(r"(?:19|20)\d\d", w)), None)
    if annee is None:
        annee = next(("20" + w for w in mots if re.fullmatch(r"\d\d", w)), None)
    return (f"{annee}-{mois:02d}" if annee else f"M{mois:02d}"), scenario


def en_periodes(serie, annees=None):
    """Transforme des dates ou libellés de mois en périodes 'AAAA-MM'."""
    texte = serie.astype(str).where(serie.notna())
    dates = pd.to_datetime(serie, errors="coerce", dayfirst=True, format="mixed") \
        if not pd.api.types.is_datetime64_any_dtype(serie) else serie
    periodes = dates.dt.strftime("%Y-%m")
    manquantes = periodes.isna() & texte.notna()
    if manquantes.any():
        periodes[manquantes] = texte[manquantes].map(lambda v: mois_depuis_entete(v)[0])
    if annees is not None:
        sans_annee = periodes.str.match(r"^M\d\d$", na=False)
        a = en_nombres(annees).astype("Int64").astype(str)
        periodes[sans_annee] = a[sans_annee] + "-" + periodes[sans_annee].str[1:]
    return periodes


# ==========================================
# Analyse de la structure
# ==========================================
def detecter_entete(brut):
    """Trouve la ligne d'en-tête en sautant les lignes de titre."""
    largeur = brut.shape[1]
    for i in range(min(20, len(brut))):
        ligne = brut.iloc[i]
        remplies = ligne.notna().sum()
        if remplies < max(2, 0.5 * largeur):
            continue
        entetes = sum(
            (isinstance(v, str) and np.isnan(_nombre(v))) or hasattr(v, "month") for v in ligne.dropna()
        )
        if entetes / remplies >= 0.6:
            return i
    return 0


def _appliquer_entete(brut, i):
    noms, vus = [], {}
    for j, v in enumerate(brut.iloc[i]):
        nom = v.strftime("%Y-%m") if hasattr(v, "strftime") else (str(v).strip() if pd.notna(v) else f"colonne_{j + 1}")
        vus[nom] = vus.get(nom, 0) + 1
        noms.append(nom if vus[nom] == 1 else f"{nom}_{vus[nom]}")
    df = brut.iloc[i + 1:].copy()
    df.columns = noms
    return df.dropna(how="all").reset_index(drop=True)


def colonnes_mois(df):
    resultat = {}
    for c in df.columns:
        periode, scenario = mois_depuis_entete(c)
        if periode and part_numerique(df[c]) >= 0.5:
            resultat[c] = (periode, scenario)
    return resultat


def detecter_roles(df):
    roles, utilisees = {}, set(colonnes_mois(df))
    cles = {c: cle(c) for c in df.columns if c not in utilisees}
    for passe in ("exacte", "mot"):
        for role, alias in ALIAS.items():
            if role in roles:
                continue
            for c, k in cles.items():
                if c in utilisees:
                    continue
                trouve = k in alias if passe == "exacte" else bool(set(k.split("_")) & set(alias))
                if trouve and (role not in ROLES_NUMERIQUES or part_numerique(df[c]) >= 0.6):
                    roles[role] = c
                    utilisees.add(c)
                    break
    # Repli sur le contenu : colonne de dates, puis colonne texte peu variée pour le centre
    libres = [c for c in df.columns if c not in utilisees]
    if "periode" not in roles:
        for c in libres:
            if part_numerique(df[c]) < 0.5 and en_periodes(df[c]).notna().mean() >= 0.8:
                roles["periode"] = c
                utilisees.add(c)
                break
    if "centre" not in roles:
        for c in df.columns:
            if c in utilisees or c == roles.get("libelle"):
                continue
            valeurs = df[c].dropna()
            if len(valeurs) and part_numerique(df[c]) < 0.2 and valeurs.nunique() <= max(50, 0.5 * len(valeurs)) \
                    and en_periodes(valeurs).notna().mean() < 0.5:
                roles["centre"] = c
                break
    return roles


def detecter_format(df, roles):
    if len(colonnes_mois(df)) >= 2:
        return "large"
    if roles.keys() & {"budget", "reel"}:
        return "colonnes"
    if roles.keys() & {"montant", "debit", "credit"}:
        return "journal"
    return "ignorer"


def lire_feuilles(contenu, nom):
    if nom.lower().endswith((".csv", ".txt")):
        for encodage in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                brut = pd.read_csv(io.BytesIO(contenu), header=None, sep=None, engine="python",
                                   dtype=str, encoding=encodage, skip_blank_lines=False)
                return {"Fichier": brut}
            except UnicodeDecodeError:
                continue
    return pd.read_excel(io.BytesIO(contenu), sheet_name=None, header=None)


def analyser(contenu, nom):
    """Lit un fichier et propose, pour chaque feuille, une structure et un rôle par colonne."""
    analyses = []
    for feuille, brut in lire_feuilles(contenu, nom).items():
        brut = brut.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
        if len(brut) < 2:
            continue
        ligne = detecter_entete(brut)
        df = _appliquer_entete(brut, ligne)
        roles = detecter_roles(df)
        analyses.append({
            "feuille": feuille,
            "ligne_entete": ligne,
            "df": df,
            "roles": roles,
            "format": detecter_format(df, roles),
            "scenario_feuille": classer_scenario(feuille) if feuille != "Fichier" else None,
            "annee_feuille": (re.search(r"(?:19|20)\d\d", str(feuille)) or [None])[0],
        })
    return analyses


# ==========================================
# Construction : tout ramener à (periode, centre, scenario, nature, montant)
# ==========================================
def _texte_lignes(df, colonnes):
    colonnes = [c for c in colonnes if c in df.columns]
    if not colonnes:
        return pd.Series("", index=df.index)
    return df[colonnes].astype(str).where(df[colonnes].notna(), "").agg(" ".join, axis=1)


def _nature_par_compte(df, roles):
    """Plan comptable : classe 6 = charges, classe 7 = produits, autres classes exclues."""
    if "compte" not in roles:
        return None
    comptes = df[roles["compte"]].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    nature = comptes.str[0].map({"6": "charge", "7": "produit"})
    return nature if nature.notna().any() else None


def _scenarios(df, roles, scenario_feuille, texte):
    defaut = scenario_feuille or "reel"
    if "scenario" in roles:
        s = df[roles["scenario"]].map(lambda v: classer_scenario(v) if pd.notna(v) else None)
    else:
        s = texte.map(classer_scenario)
    return s.fillna(defaut)


def _centres(df, roles):
    if "centre" in roles:
        return df[roles["centre"]].astype(str).str.strip().where(df[roles["centre"]].notna(), "Non affecté")
    return pd.Series("Global", index=df.index)


def _sans_totaux(df, roles, texte):
    garde = ~texte.map(est_total)
    return df[garde], texte[garde]


def construire_colonnes(a):
    df, roles = a["df"], a["roles"]
    texte = _texte_lignes(df, [roles.get(r) for r in ("centre", "libelle", "scenario")])
    df, texte = _sans_totaux(df, roles, texte)
    periode = en_periodes(df[roles["periode"]], df[roles["annee"]] if "annee" in roles else None) \
        if "periode" in roles else (df.groupby(_centres(df, roles)).cumcount() + 1).map(lambda i: f"P{i:03d}")
    centre = _centres(df, roles)
    scenario_ligne = _scenarios(df, roles, a["scenario_feuille"], pd.Series("", index=df.index))
    morceaux = []
    for role, nature in (("budget", "charge"), ("reel", "charge"), ("revenus", "produit")):
        if role not in roles:
            continue
        scenario = "budget" if role == "budget" else scenario_ligne
        morceaux.append(pd.DataFrame({"periode": periode, "centre": centre, "scenario": scenario,
                                      "nature": nature, "montant": en_nombres(df[roles[role]])}))
    return pd.concat(morceaux) if morceaux else pd.DataFrame()


def construire_journal(a):
    df, roles = a["df"], a["roles"]
    if "periode" not in roles:
        raise ValueError(f"Feuille « {a['feuille']} » : aucune colonne de date trouvée.")
    if roles.keys() & {"debit", "credit"}:
        debit = en_nombres(df[roles["debit"]]).fillna(0) if "debit" in roles else 0
        credit = en_nombres(df[roles["credit"]]).fillna(0) if "credit" in roles else 0
        solde, signe = debit - credit, True
    else:
        solde, signe = en_nombres(df[roles["montant"]]), False
    texte = _texte_lignes(df, [roles.get(r) for r in ("compte", "libelle")])
    nature = _nature_par_compte(df, roles)
    if nature is None:
        nature = texte.map(lambda t: "produit" if est_produit(t) else "charge")
    montant = np.where(nature == "produit", -solde if signe else solde.abs(), solde)
    resultat = pd.DataFrame({
        "periode": en_periodes(df[roles["periode"]], df[roles["annee"]] if "annee" in roles else None),
        "centre": _centres(df, roles),
        "scenario": _scenarios(df, roles, a["scenario_feuille"], _texte_lignes(df, [roles.get("libelle")])),
        "nature": nature,
        "montant": montant,
    })
    return resultat.dropna(subset=["nature"])


def construire_large(a):
    df, roles = a["df"], a["roles"]
    mois = colonnes_mois(df)
    ids = [c for c in df.columns if c not in mois]
    texte = _texte_lignes(df, ids)
    df, texte = _sans_totaux(df, roles, texte)
    if "centre" not in roles:
        candidats = [c for c in ids if c not in roles.values() and part_numerique(df[c]) < 0.2]
        roles = {**roles, "centre": candidats[0]} if candidats else roles
    centre = _centres(df, roles)
    scenario = _scenarios(df, roles, a["scenario_feuille"], texte)
    nature = _nature_par_compte(df, roles)
    if nature is None:
        nature = texte.map(lambda t: "produit" if est_produit(t) else "charge")
    annees = df[roles["annee"]] if "annee" in roles else None
    morceaux = []
    for col, (periode, scenario_entete) in mois.items():
        p = pd.Series(periode, index=df.index)
        if annees is not None and periode.startswith("M"):
            p = en_nombres(annees).astype("Int64").astype(str) + "-" + periode[1:]
        elif a.get("annee_feuille") and periode.startswith("M"):
            p = pd.Series(f"{a['annee_feuille']}-{periode[1:]}", index=df.index)
        morceaux.append(pd.DataFrame({
            "periode": p, "centre": centre, "scenario": scenario_entete or scenario,
            "nature": nature, "montant": en_nombres(df[col]),
        }))
    return pd.concat(morceaux)


CONSTRUCTEURS = {"colonnes": construire_colonnes, "journal": construire_journal, "large": construire_large}


def _budget_reconstruit(out):
    """Budget de référence : même mois N-1, sinon moyenne des 3 mois précédents, sinon le réel."""
    reel_par_cle = out.set_index(["centre", "periode"])["reel"].to_dict()

    def n_moins_1(ligne):
        m = re.match(r"^(\d{4})-(\d\d)$", str(ligne["periode"]))
        return reel_par_cle.get((ligne["centre"], f"{int(m.group(1)) - 1}-{m.group(2)}")) if m else None

    n1 = out.apply(n_moins_1, axis=1).astype(float)
    moyenne = out.groupby("centre")["reel"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    return n1.fillna(moyenne).fillna(out["reel"])


def _repartir_revenus_globaux(long):
    """Les lignes de CA sans centre de coûts (ex. « Chiffre d'affaires ») sont réparties
    entre les centres au prorata de leurs charges réelles de la période."""
    avec_charges = set(long.loc[long["nature"] == "charge", "centre"])
    globaux = (long["nature"] == "produit") & (long["scenario"] == "reel") & ~long["centre"].isin(avec_charges)
    if not globaux.any() or not avec_charges:
        return long, None
    ca = long[globaux].groupby("periode")["montant"].sum()
    charges = long[(long["nature"] == "charge") & (long["scenario"] == "reel")] \
        .groupby(["periode", "centre"])["montant"].sum().reset_index()
    charges["part"] = charges["montant"] / charges.groupby("periode")["montant"].transform("sum")
    charges["montant"] = charges["part"] * charges["periode"].map(ca)
    reparti = charges.dropna(subset=["montant"]).assign(scenario="reel", nature="produit")
    lignes = ", ".join(sorted(long.loc[globaux, "centre"].unique()))
    message = f"Revenus sans centre ({lignes}) répartis entre les centres au prorata de leurs charges réelles."
    return pd.concat([long[~globaux], reparti[long.columns]]), message


def monter(analyses):
    """Assemble toutes les feuilles en un tableau standard + un rapport de montage."""
    rapport, morceaux = [], []
    for a in analyses:
        if a["format"] == "ignorer":
            rapport.append(f"Feuille « {a['feuille']} » ignorée.")
            continue
        long = CONSTRUCTEURS[a["format"]](a)
        long = long.dropna(subset=["periode", "montant"])
        morceaux.append(long)
        details = ", ".join(f"{ROLES_AFFICHES[r]} = « {c} »" for r, c in a["roles"].items())
        titres = f", {a['ligne_entete']} ligne(s) de titre ignorée(s)" if a["ligne_entete"] else ""
        rapport.append(f"Feuille « {a['feuille']} » : {FORMATS[a['format']].lower()}{titres}, "
                       f"{len(long)} montants lus ({details}).")
    if not morceaux or all(m.empty for m in morceaux):
        raise ValueError("Aucun montant exploitable n'a été trouvé dans le fichier.")

    long = pd.concat(morceaux)
    long["centre"] = long["centre"].astype(str)
    long, message = _repartir_revenus_globaux(long)
    if message:
        rapport.append(message)
    cumul = long.groupby(["periode", "centre", "scenario", "nature"])["montant"].sum()
    out = pd.DataFrame(index=cumul.droplevel(["scenario", "nature"]).index.unique())
    for nom, (scenario, nature) in {"budget": ("budget", "charge"), "reel": ("reel", "charge"),
                                    "revenus": ("reel", "produit")}.items():
        try:
            out[nom] = cumul.xs((scenario, nature), level=("scenario", "nature"))
        except KeyError:
            out[nom] = np.nan
    out = out.reset_index().sort_values(["centre", "periode"]).reset_index(drop=True)

    if out["reel"].isna().all():
        raise ValueError("Aucune charge réelle trouvée : impossible de calculer des écarts.")
    out = out.dropna(subset=["reel"]).reset_index(drop=True)
    manquants = out["budget"].isna()
    if manquants.all():
        out["budget"] = _budget_reconstruit(out)
        rapport.append("Aucun budget trouvé : budget de référence reconstruit (même mois N-1, "
                       "sinon moyenne des 3 mois précédents).")
    elif manquants.any():
        out.loc[manquants, "budget"] = _budget_reconstruit(out)[manquants]
        rapport.append(f"{int(manquants.sum())} lignes sans budget : budget reconstruit sur l'historique.")
    if out["revenus"].isna().all():
        rapport.append("Aucun revenu trouvé : les indicateurs de marge sont neutralisés.")
    rapport.append(f"Résultat : {out['centre'].nunique()} centres × {out['periode'].nunique()} périodes "
                   f"= {len(out)} lignes de contrôle.")
    return out[["periode", "centre", "budget", "reel", "revenus"]], rapport
