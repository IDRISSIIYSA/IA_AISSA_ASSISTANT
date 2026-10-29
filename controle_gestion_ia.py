"""
Contrôle de Gestion IA — un agent "tabula rasa" qui apprend seul à surveiller les écarts budgétaires.

L'agent naît sans aucune connaissance en contrôle de gestion. Il observe chaque ligne
(centre de coûts × période), choisit une décision, reçoit une récompense ou une pénalité,
et range chaque expérience dans sa mémoire profonde (replay memory) pour la réapprendre.

Lancement :
    pip install -r requirements.txt
    streamlit run controle_gestion_ia.py

Format attendu du fichier (CSV ou Excel), une ligne par centre et par période :
    periode, centre, budget, reel, revenus
"""

import io
import random
import unicodedata
from collections import deque

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

# ==========================================
# 1. Règles du métier (la "loi du monde" que l'agent doit découvrir)
# ==========================================
ACTIONS = {0: "🚨 Alerte écart", 1: "✅ Statu quo", 2: "✂️ Optimiser coûts"}
SEUIL_ALERTE = 0.10     # écart > 10 % du budget : dérive grave
SEUIL_VIGILANCE = 0.03  # écart > 3 % du budget : dérive modérée
FEATURES = ["ecart_pct", "tendance", "marge_pct", "ratio_cout_revenus"]

# Récompenses selon (situation réelle, décision prise)
RECOMPENSES = {
    "grave":   {0: 10.0, 2: 4.0, 1: -10.0},
    "moderee": {2: 6.0, 0: 2.0, 1: -4.0},
    "normale": {1: 5.0, 2: -1.0, 0: -3.0},
}
DECISION_IDEALE = {"grave": 0, "moderee": 2, "normale": 1}

ALIAS_COLONNES = {
    "periode": ["periode", "période", "mois", "date", "period"],
    "centre": ["centre", "centre_cout", "departement", "département", "service", "section"],
    "budget": ["budget", "budget_prevu", "prevu", "prévu", "budgete", "budgété"],
    "reel": ["reel", "réel", "realise", "réalisé", "cout_reel", "coût_réel", "actual", "cout"],
    "revenus": ["revenus", "revenu", "ca", "chiffre_affaires", "chiffre_d_affaires", "revenue", "ventes"],
}


def sans_accents(texte):
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def normaliser_colonnes(df):
    """Renomme les colonnes du fichier utilisateur vers le format interne."""
    correspondance = {}
    for col in df.columns:
        cle = sans_accents(str(col).strip().lower().replace(" ", "_").replace("'", "_"))
        for cible, alias in ALIAS_COLONNES.items():
            if cle in map(sans_accents, alias) and cible not in correspondance.values():
                correspondance[col] = cible
                break
    df = df.rename(columns=correspondance)
    manquantes = [c for c in ("budget", "reel", "revenus") if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {', '.join(manquantes)}")
    if "centre" not in df.columns:
        df["centre"] = "Global"
    if "periode" not in df.columns:
        df["periode"] = df.groupby("centre").cumcount() + 1
    return df[["periode", "centre", "budget", "reel", "revenus"]]


def generer_donnees_exemple(n_mois=36, seed=42):
    """Données réalistes : saisonnalité, dérives progressives et pics ponctuels."""
    rng = np.random.default_rng(seed)
    centres = {"Production": 120_000, "Commercial": 60_000, "Administration": 35_000, "R&D": 45_000}
    periodes = pd.period_range("2023-01", periods=n_mois, freq="M").astype(str)
    lignes = []
    for centre, base in centres.items():
        debut_derive = rng.integers(n_mois // 4, max(n_mois // 4 + 1, n_mois - 6))
        for i, periode in enumerate(periodes):
            saison = 1 + 0.08 * np.sin(2 * np.pi * i / 12)
            budget = base * saison
            derive = 0.012 * max(0, i - debut_derive)        # dérive qui s'aggrave
            pic = rng.choice([0, 0.18], p=[0.93, 0.07])       # incident ponctuel
            reel = budget * (1 + rng.normal(0, 0.025) + derive + pic)
            revenus = budget * rng.uniform(1.25, 1.45)
            lignes.append((periode, centre, round(budget, 2), round(reel, 2), round(revenus, 2)))
    return pd.DataFrame(lignes, columns=["periode", "centre", "budget", "reel", "revenus"])


def preparer(df):
    """Transforme les chiffres bruts en 'sens' que l'agent peut percevoir."""
    df = df.copy()
    for col in ("budget", "reel", "revenus"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["budget", "reel", "revenus"])
    df = df[df["budget"] > 0].sort_values(["centre", "periode"]).reset_index(drop=True)

    df["ecart"] = df["reel"] - df["budget"]
    df["ecart_pct"] = df["ecart"] / df["budget"]
    df["marge_pct"] = np.where(df["revenus"] > 0, (df["revenus"] - df["reel"]) / df["revenus"], -1.0)
    df["ratio_cout_revenus"] = np.where(df["revenus"] > 0, df["reel"] / df["revenus"], 2.0)
    # Tendance : évolution de l'écart sur les 3 dernières périodes du même centre
    moyenne_glissante = df.groupby("centre")["ecart_pct"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    df["tendance"] = moyenne_glissante.groupby(df["centre"]).diff().fillna(0.0)

    df["situation"] = df.apply(classer_situation, axis=1)
    return df


def classer_situation(ligne):
    e, t = ligne["ecart_pct"], ligne["tendance"]
    if e > SEUIL_ALERTE or (e > SEUIL_VIGILANCE and t > 0.03):
        return "grave"
    if e > SEUIL_VIGILANCE:
        return "moderee"
    return "normale"


def etats(df):
    return np.clip(df[FEATURES].to_numpy(dtype=np.float32), -3, 3)


# ==========================================
# 2. L'univers de l'agent
# ==========================================
class ControleGestionEnv:
    """Chaque épisode parcourt les lignes dans un ordre aléatoire."""

    def __init__(self, df):
        self.etats = etats(df)
        self.situations = df["situation"].tolist()
        self.ordre = []
        self.pos = 0

    def reset(self):
        self.ordre = np.random.permutation(len(self.etats))
        self.pos = 0
        return self.etats[self.ordre[0]]

    def step(self, action):
        reward = RECOMPENSES[self.situations[self.ordre[self.pos]]][action]
        self.pos += 1
        done = self.pos >= len(self.ordre)
        next_state = self.etats[self.ordre[min(self.pos, len(self.ordre) - 1)]]
        return next_state, reward, done


# ==========================================
# 3. Le cerveau vide et la mémoire profonde
# ==========================================
class Cerveau(nn.Module):
    def __init__(self, n_entrees=len(FEATURES), n_actions=len(ACTIONS)):
        super().__init__()
        self.reseau = nn.Sequential(
            nn.Linear(n_entrees, 64), nn.ReLU(),
            nn.Linear(64, 64), nn.ReLU(),
            nn.Linear(64, n_actions),
        )

    def forward(self, x):
        return self.reseau(x)


class MemoireProfonde:
    def __init__(self, capacite=10_000):
        self.buffer = deque(maxlen=capacite)

    def stocker(self, *experience):
        self.buffer.append(experience)

    def echantillon(self, taille):
        s, a, r, s2, d = zip(*random.sample(self.buffer, taille))
        return (torch.tensor(np.array(s)), torch.tensor(a), torch.tensor(r, dtype=torch.float32),
                torch.tensor(np.array(s2)), torch.tensor(d, dtype=torch.float32))

    def __len__(self):
        return len(self.buffer)


def entrainer(df, n_episodes=30, gamma=0.5, lr=1e-3, batch=64, seed=0, callback=None):
    """Apprentissage DQN avec mémoire profonde et réseau cible."""
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    env = ControleGestionEnv(df)
    cerveau, cible = Cerveau(), Cerveau()
    cible.load_state_dict(cerveau.state_dict())
    optimiseur = optim.Adam(cerveau.parameters(), lr=lr)
    memoire = MemoireProfonde()
    epsilon, eps_min = 1.0, 0.02
    eps_decay = (eps_min / epsilon) ** (1 / max(1, n_episodes * 0.7))
    historique, pas = [], 0

    for episode in range(n_episodes):
        etat, total, done = env.reset(), 0.0, False
        while not done:
            if random.random() < epsilon:
                action = random.randrange(len(ACTIONS))      # curiosité : essai au hasard
            else:
                with torch.no_grad():
                    action = int(cerveau(torch.from_numpy(etat)).argmax())
            etat_suivant, reward, done = env.step(action)
            memoire.stocker(etat, action, reward, etat_suivant, done)
            etat, total, pas = etat_suivant, total + reward, pas + 1

            if len(memoire) >= batch:
                s, a, r, s2, d = memoire.echantillon(batch)
                with torch.no_grad():
                    objectif = r + gamma * cible(s2).max(1).values * (1 - d)
                prediction = cerveau(s).gather(1, a.unsqueeze(1)).squeeze(1)
                perte = nn.functional.smooth_l1_loss(prediction, objectif)
                optimiseur.zero_grad(); perte.backward(); optimiseur.step()
            if pas % 200 == 0:
                cible.load_state_dict(cerveau.state_dict())

        epsilon = max(eps_min, epsilon * eps_decay)
        actions, _ = decider(cerveau, df)
        precision = float(np.mean(actions == df["situation"].map(DECISION_IDEALE).to_numpy()))
        historique.append({"episode": episode + 1, "recompense": total, "epsilon": epsilon, "precision": precision})
        if callback:
            callback(episode + 1, n_episodes, historique[-1])

    return cerveau, pd.DataFrame(historique)


def decider(cerveau, df):
    with torch.no_grad():
        q = cerveau(torch.from_numpy(etats(df)))
    confiance = torch.softmax(q, dim=1).max(1).values.numpy()
    return q.argmax(1).numpy(), confiance


# ==========================================
# 4. Le tableau de bord (Streamlit)
# ==========================================
def main():
    import streamlit as st

    st.set_page_config(page_title="Contrôle de Gestion IA", page_icon="📊", layout="wide")
    st.title("📊 Contrôle de Gestion IA")
    st.caption("Un agent né vide qui apprend seul à détecter les écarts et à rééquilibrer le budget.")

    with st.sidebar:
        st.header("1. Données")
        fichier = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx", "xls"])
        st.download_button("Télécharger un modèle de fichier",
                           generer_donnees_exemple(6).to_csv(index=False).encode("utf-8"),
                           "modele_controle_gestion.csv", "text/csv")
        st.header("2. Apprentissage")
        n_episodes = st.slider("Nombre de générations (épisodes)", 5, 100, 30)
        lancer = st.button("🧬 Faire naître et entraîner l'agent", type="primary", width="stretch")

    try:
        if fichier is None:
            brut = generer_donnees_exemple()
            st.info("Aucun fichier importé : utilisation de données d'exemple (4 centres × 36 mois).")
        elif fichier.name.endswith(".csv"):
            contenu = fichier.getvalue()
            brut = pd.read_csv(io.BytesIO(contenu), sep=None, engine="python")
        else:
            brut = pd.read_excel(fichier)
        df = preparer(normaliser_colonnes(brut))
    except Exception as e:
        st.error(f"Impossible de lire le fichier : {e}")
        st.stop()

    if df.empty:
        st.error("Aucune ligne exploitable dans le fichier.")
        st.stop()

    # Indicateurs globaux
    c1, c2, c3, c4 = st.columns(4)
    budget, reel = df["budget"].sum(), df["reel"].sum()
    c1.metric("Budget total", f"{budget:,.0f}".replace(",", " "))
    c2.metric("Réalisé total", f"{reel:,.0f}".replace(",", " "),
              f"{(reel - budget) / budget:+.1%}", delta_color="inverse")
    c3.metric("Marge moyenne", f"{df['marge_pct'].mean():.1%}")
    c4.metric("Lignes en dérive grave", int((df["situation"] == "grave").sum()))

    st.subheader("Écarts budgétaires par centre")
    pivot = df.pivot_table(index="periode", columns="centre", values="ecart_pct", aggfunc="mean")
    st.line_chart(pivot * 100, y_label="Écart (%)")

    if lancer:
        barre = st.progress(0.0, text="L'agent ouvre les yeux…")

        def suivi(ep, total, h):
            barre.progress(ep / total, text=f"Génération {ep}/{total} — précision {h['precision']:.0%}")

        cerveau, historique = entrainer(df, n_episodes=n_episodes, callback=suivi)
        st.session_state["cerveau"] = cerveau
        st.session_state["historique"] = historique
        st.session_state["cle_donnees"] = len(df), float(df["reel"].sum())
        barre.empty()

    if "cerveau" not in st.session_state:
        st.warning("Cliquez sur « Faire naître et entraîner l'agent » pour lancer l'apprentissage.")
        return
    if st.session_state.get("cle_donnees") != (len(df), float(df["reel"].sum())):
        st.warning("Les données ont changé : relancez l'entraînement.")
        return

    historique = st.session_state["historique"]
    actions, confiance = decider(st.session_state["cerveau"], df)
    df["decision_ia"] = [ACTIONS[a] for a in actions]
    df["confiance"] = confiance
    df["decision_reference"] = df["situation"].map(DECISION_IDEALE).map(ACTIONS)

    st.subheader("🧠 Croissance de l'intelligence")
    g1, g2 = st.columns(2)
    g1.line_chart(historique.set_index("episode")["precision"] * 100, y_label="Précision (%)")
    g2.line_chart(historique.set_index("episode")["recompense"], y_label="Récompense totale")
    st.caption(f"Précision finale par rapport aux règles métier : {historique['precision'].iloc[-1]:.1%}")

    st.subheader("📋 Décisions de l'agent")
    filtre = st.multiselect("Filtrer par décision", list(ACTIONS.values()), default=[ACTIONS[0], ACTIONS[2]])
    vue = df[df["decision_ia"].isin(filtre)] if filtre else df
    st.dataframe(
        vue[["periode", "centre", "budget", "reel", "ecart", "ecart_pct", "tendance",
             "decision_ia", "confiance", "decision_reference"]],
        width="stretch", hide_index=True,
        column_config={
            "ecart_pct": st.column_config.NumberColumn("Écart %", format="percent"),
            "tendance": st.column_config.NumberColumn("Tendance", format="%.3f"),
            "confiance": st.column_config.ProgressColumn("Confiance", min_value=0, max_value=1),
        },
    )
    st.download_button("Exporter les décisions (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "decisions_ia.csv", "text/csv")

    buffer = io.BytesIO()
    torch.save(st.session_state["cerveau"].state_dict(), buffer)
    st.download_button("Sauvegarder le cerveau de l'agent (.pt)", buffer.getvalue(), "cerveau_controle_gestion.pt")


if __name__ == "__main__":
    main()
