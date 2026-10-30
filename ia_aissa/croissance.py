"""
Croissance d'IA AISSA : concepts maîtrisés par grande famille de sciences, au fil du temps.

Point de départ : ce que chaque cerveau a appris à l'école (nombre de réponses possibles × note d'examen).
Ensuite, chaque correction apprise (par l'utilisateur, l'assistante, l'étude autonome ou la lecture) ajoute un
concept à la famille de sa matière, et chaque concept digéré en lisant (pages web, livres, Wikipédia) aussi. Le ratio d'autonomie compare ce qu'IA AISSA a appris seule à ses lacunes repérées.
"""

import json

import pandas as pd

from .ecole import MATIERES, charger

FAMILLES = {
    "Sciences formelles": {"maths_financieres", "statistiques", "ia", "structures_donnees", "complexite", "fractions",
                           "discriminant", "derivee", "suites", "orientation", "investissement", "elasticite",
                           "probabilite", "limites"},
    "Sciences naturelles": {"sciences", "familles_sciences", "corps_humain", "unites", "mouvement", "ph", "genetique",
                            "ohm", "equilibrer"},
    "Sciences appliquées": {"production", "logistique", "transit", "incoterms", "credit", "cycle_de_vie", "bcg",
                            "commercial", "creation", "transport", "triz"},
}
HUMAINES = "Sciences humaines et gestion"


def famille(cle):
    return next((f for f, cles in FAMILLES.items() if cle in cles), HUMAINES)


def concepts_ecole():
    """Concepts maîtrisés à la sortie de l'école, par famille."""
    total = {f: 0.0 for f in [*FAMILLES, HUMAINES]}
    for m in MATIERES:
        _, historique = charger(m.cle)
        notes = [h["precision"] for h in historique or [] if isinstance(h.get("pas"), int)]
        if notes:
            total[famille(m.cle)] += len(m.actions) * notes[-1]
    return {f: round(v) for f, v in total.items()}


def serie(memoire):
    """Cumul des concepts maîtrisés par famille et par date (DataFrame large : une colonne par famille)."""
    base = concepts_ecole()
    evenements = [{"date": c["cree_le"], "famille": famille(c["matiere"]), "n": 1}
                  for c in memoire.corrections_de() if c["apprise"] and c["matiere"] != "orientation"]
    evenements += [{"date": d["cree_le"], "famille": d["famille"], "n": len(json.loads(d["concepts"]))}
                   for d in memoire.digestions()]                  # concepts digérés en lisant
    if not evenements:
        return pd.DataFrame([base], index=pd.DatetimeIndex([pd.Timestamp.now(tz="UTC")], name="date"))
    df = pd.DataFrame(evenements)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    cumul = df.pivot_table(index="date", columns="famille", values="n", aggfunc="sum").fillna(0).cumsum()
    for f, v in base.items():
        cumul[f] = cumul.get(f, 0) + v
    depart = pd.DataFrame([base], index=pd.DatetimeIndex([cumul.index.min() - pd.Timedelta(hours=1)], name="date"))
    return pd.concat([depart, cumul[list(base)]]).ffill()


def vitesse_apprentissage(memoire, jours=14):
    """Courbe de progrès de chaque matière (curiosité guidée par le progrès, à la Oudeyer) :
    - pente de fin de courbe d'école : ce que le cerveau gagnait encore à la fin de son entraînement ;
    - corrections apprises ces derniers jours : ce qu'il apprend en ce moment.
    Renvoie un DataFrame trié du plus grand progrès au plus petit."""
    maintenant = pd.Timestamp.now(tz="UTC")
    recentes = {}
    for c in memoire.corrections_de():
        if c["apprise"] and c["matiere"] != "orientation":
            date = pd.Timestamp(c["cree_le"])
            date = date.tz_localize("UTC") if date.tzinfo is None else date
            if date > maintenant - pd.Timedelta(days=jours):
                recentes[c["matiere"]] = recentes.get(c["matiere"], 0) + 1
    lignes = []
    for m in MATIERES:
        if m.cle == "orientation":
            continue
        _, historique = charger(m.cle)
        notes = [h["precision"] for h in historique or [] if isinstance(h.get("pas"), int)]
        if not notes:
            continue
        mi = len(notes) // 2
        pente = max(0.0, notes[-1] - notes[mi])                    # progrès de la deuxième moitié de l'école
        lignes.append({"matiere": m.cle, "nom": m.nom, "note": notes[-1], "progres_ecole": pente,
                       "appris_recemment": recentes.get(m.cle, 0),
                       "progres": pente + 0.05 * recentes.get(m.cle, 0) + 0.5 * (1 - notes[-1])})
    return pd.DataFrame(lignes).sort_values("progres", ascending=False).reset_index(drop=True)


def indicateurs(memoire):
    lacunes_total, _ = memoire.compter_lacunes()
    toutes = memoire.corrections_de()
    autonomes = sum(1 for c in toutes if c["source"] == "étude autonome" and c["matiere"] != "orientation")
    dates = pd.to_datetime(pd.Series([c["cree_le"] for c in toutes if c["apprise"]], dtype="object"), utc=True)
    maintenant = pd.Timestamp.now(tz="UTC")
    recentes = int((dates > maintenant - pd.Timedelta(days=7)).sum())
    avant = int(((dates <= maintenant - pd.Timedelta(days=7)) & (dates > maintenant - pd.Timedelta(days=14))).sum())
    return {"lacunes": lacunes_total, "autonomes": autonomes,
            "ratio_autonomie": autonomes / lacunes_total if lacunes_total else 0.0,
            "recentes": recentes, "acceleration": recentes - avant}


def afficher(st, memoire):
    s = serie(memoire)
    i = indicateurs(memoire)
    c1, c2, c3 = st.columns(3)
    c1.metric("Concepts maîtrisés", int(s.iloc[-1].sum()))
    c2.metric("Ratio d'autonomie (appris seule / lacunes)", f"{i['ratio_autonomie']:.0%}",
              help=f"{i['autonomes']} concept(s) appris en étude autonome pour {i['lacunes']} lacune(s) repérée(s).")
    c3.metric("Appris ces 7 derniers jours", i["recentes"], delta=i["acceleration"],
              help="Comparé aux 7 jours précédents : un delta positif signifie que l'apprentissage accélère.")
    if len(s) > 1:
        st.area_chart(s, y_label="Concepts maîtrisés (cumul)")
        par_jour = s.sum(axis=1).diff().fillna(0).clip(lower=0)
        par_jour = par_jour.groupby(par_jour.index.floor("D")).sum().rename("Nouveaux concepts par jour")
        st.bar_chart(par_jour, y_label="Nouveaux concepts par jour")
    else:
        st.bar_chart(s.iloc[-1], y_label="Concepts maîtrisés", horizontal=True)
    vitesses = vitesse_apprentissage(memoire)
    if not vitesses.empty:
        st.caption("🧭 Curiosité guidée par le progrès : IA AISSA étudie d'abord les matières où elle progresse le plus.")
        st.dataframe(vitesses.head(8)[["nom", "note", "progres_ecole", "appris_recemment"]].rename(columns={
            "nom": "Matière", "note": "Note", "progres_ecole": "Progrès en fin d'école",
            "appris_recemment": "Appris (14 j)"}), hide_index=True,
            column_config={"Note": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
    st.caption("Chaque famille part de ce qu'IA AISSA a appris à l'école, puis grandit à chaque correction apprise. "
               "Plus on lui parle, plus elle repère de lacunes et plus elle apprend vite.")
