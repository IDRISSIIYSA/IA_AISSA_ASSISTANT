"""
Contrôle de Gestion IA — un agent "tabula rasa" qui apprend seul à surveiller les écarts budgétaires.

L'agent naît sans aucune connaissance en contrôle de gestion. Il observe chaque ligne
(centre de coûts × période), choisit une décision, reçoit une récompense ou une pénalité,
et range chaque expérience dans sa mémoire profonde (replay memory) pour la réapprendre.

Lancement :
    pip install -r requirements.txt
    streamlit run controle_gestion_ia.py

Données brutes acceptées quelle que soit leur structure (voir montage.py) : journal comptable,
tableau mensuel avec les mois en colonnes, classeur Budget / Réalisé, tableau par indicateurs…
Elles sont ramenées au format standard : periode, centre, budget, reel, revenus.
"""

import io
import random
from pathlib import Path
from collections import deque

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from ia_aissa.acces import verifier_acces
from ia_aissa.croissance import afficher as afficher_croissance
from ia_aissa.partage import memoire
from montage import FORMATS, ROLES_AFFICHES, analyser, monter

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
    df = df.dropna(subset=["budget", "reel"])
    df = df[df["budget"] > 0].sort_values(["centre", "periode"]).reset_index(drop=True)

    df["ecart"] = df["reel"] - df["budget"]
    df["ecart_pct"] = df["ecart"] / df["budget"]
    # Sans revenus connus, les indicateurs de marge restent neutres
    df["marge_pct"] = np.where(df["revenus"].isna(), 0.0,
                               np.where(df["revenus"] > 0, (df["revenus"] - df["reel"]) / df["revenus"], -1.0))
    df["ratio_cout_revenus"] = np.where(df["revenus"].isna(), 1.0,
                                        np.where(df["revenus"] > 0, df["reel"] / df["revenus"], 2.0))
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
        s, a, r, s2, d, m = zip(*random.sample(self.buffer, taille))
        return (torch.tensor(np.array(s)), torch.tensor(a), torch.tensor(r, dtype=torch.float32),
                torch.tensor(np.array(s2)), torch.tensor(d, dtype=torch.float32), torch.tensor(np.array(m)))

    def __len__(self):
        return len(self.buffer)


# ==========================================
# 3 bis. Méta-intelligence : Sutton (curiosité), Dalio (conseil pondéré par la crédibilité),
#        Hofstadter / GEB (boucle étrange : l'agent apprend à juger sa propre pensée)
# ==========================================
N_CERVEAUX = 5
STATUTS = {"sur": "✅ Sûr", "confirmer": "🟡 À confirmer", "doute": "🤔 Je ne sais pas"}


class Conseil:
    """Plusieurs cerveaux nés vides, chacun formé sur une partie différente de la mémoire (bootstrap).
    Leur désaccord mesure ce que l'agent ignore ; leur crédibilité pondère leur vote (Dalio)."""

    def __init__(self, n=N_CERVEAUX):
        self.cerveaux = [Cerveau() for _ in range(n)]
        self.credibilite = np.ones(n) / n
        self.meta = nn.Sequential(nn.Linear(len(FEATURES) + 2, 32), nn.ReLU(), nn.Linear(32, 1))

    def votes(self, x):
        with torch.no_grad():
            return torch.stack([c(x) for c in self.cerveaux])          # (cerveaux, lignes, actions)

    def deliberer(self, x):
        q = self.votes(x)
        choix = q.argmax(-1).numpy()                                    # (cerveaux, lignes)
        poids = np.zeros((x.shape[0], len(ACTIONS)))
        for k in range(len(self.cerveaux)):
            poids[np.arange(x.shape[0]), choix[k]] += self.credibilite[k]
        poids /= poids.sum(1, keepdims=True)
        decision = poids.argmax(1)
        accord = poids.max(1)                                           # 1 = unanimité
        marge = torch.softmax(q.mean(0), -1).max(-1).values.numpy()
        return decision, accord, marge

    def desaccord(self, x):
        return 1 - self.deliberer(x)[1]

    def entree_meta(self, x, accord, marge):
        return torch.cat([x, torch.tensor(accord, dtype=torch.float32)[:, None],
                          torch.tensor(marge, dtype=torch.float32)[:, None]], 1)

    def auto_evaluation(self, x):
        """La boucle étrange : l'agent estime la probabilité que sa propre décision soit juste."""
        decision, accord, marge = self.deliberer(x)
        with torch.no_grad():
            p = torch.sigmoid(self.meta(self.entree_meta(x, accord, marge))).squeeze(1).numpy()
        return decision, p, accord

    def state_dict(self):
        return {"cerveaux": [c.state_dict() for c in self.cerveaux], "credibilite": self.credibilite.tolist(),
                "meta": self.meta.state_dict()}


def statut(p):
    return STATUTS["sur"] if p >= 0.8 else STATUTS["confirmer"] if p >= 0.5 else STATUTS["doute"]


def entrainer(df, n_episodes=30, gamma=0.5, lr=1e-3, batch=64, seed=0, curiosite=1.0, callback=None):
    """Bootstrapped DQN + bonus de curiosité + méta-cerveau qui apprend des erreurs de l'agent."""
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    env = ControleGestionEnv(df)
    conseil = Conseil()
    cibles = [Cerveau() for _ in conseil.cerveaux]
    for c, t in zip(conseil.cerveaux, cibles):
        t.load_state_dict(c.state_dict())
    optimiseurs = [optim.Adam(c.parameters(), lr=lr) for c in conseil.cerveaux]
    opt_meta = optim.Adam(conseil.meta.parameters(), lr=3e-3)
    memoire = MemoireProfonde()
    epsilon, eps_min = 0.5, 0.02
    eps_decay = (eps_min / epsilon) ** (1 / max(1, n_episodes * 0.6))
    historique, journal, pas = [], [], 0
    tous_etats = torch.from_numpy(etats(df))
    ideal = df["situation"].map(DECISION_IDEALE).to_numpy()

    for episode in range(n_episodes):
        etat, total, bonus_total, done = env.reset(), 0.0, 0.0, False
        guide = random.randrange(len(conseil.cerveaux))                # exploration profonde : un cerveau mène l'épisode
        beta = curiosite * (1 - episode / n_episodes)                   # la curiosité s'apaise avec l'expérience
        while not done:
            x = torch.from_numpy(etat)
            if random.random() < epsilon:
                action = random.randrange(len(ACTIONS))
            else:
                with torch.no_grad():
                    action = int(conseil.cerveaux[guide](x).argmax())
            etat_suivant, reward, done = env.step(action)
            bonus = beta * float(conseil.desaccord(x[None])[0])         # récompense intrinsèque : la curiosité
            masque = (np.random.rand(len(conseil.cerveaux)) < 0.5).astype(np.float32)
            memoire.stocker(etat, action, reward + bonus, etat_suivant, done, masque)
            etat, total, bonus_total, pas = etat_suivant, total + reward, bonus_total + bonus, pas + 1

            if len(memoire) >= batch:
                s, a, r, s2, d, m = memoire.echantillon(batch)
                for k, (c, t, o) in enumerate(zip(conseil.cerveaux, cibles, optimiseurs)):
                    with torch.no_grad():
                        objectif = r + gamma * t(s2).max(1).values * (1 - d)
                    prediction = c(s).gather(1, a.unsqueeze(1)).squeeze(1)
                    perte = (nn.functional.smooth_l1_loss(prediction, objectif, reduction="none") * m[:, k]).mean()
                    o.zero_grad(); perte.backward(); o.step()
            if pas % 200 == 0:
                for c, t in zip(conseil.cerveaux, cibles):
                    t.load_state_dict(c.state_dict())

        epsilon = max(eps_min, epsilon * eps_decay)
        # Dalio : chaque cerveau gagne en crédibilité selon ses résultats
        votes = conseil.votes(tous_etats).argmax(-1).numpy()
        justesse = (votes == ideal).mean(1)
        conseil.credibilite = np.exp(8 * justesse) / np.exp(8 * justesse).sum()
        # GEB : le méta-cerveau apprend à reconnaître quand l'agent se trompe
        decision, accord, marge = conseil.deliberer(tous_etats)
        juste = torch.tensor((decision == ideal).astype(np.float32))
        entree = conseil.entree_meta(tous_etats, accord, marge)
        for _ in range(30):
            perte_meta = nn.functional.binary_cross_entropy_with_logits(conseil.meta(entree).squeeze(1), juste)
            opt_meta.zero_grad(); perte_meta.backward(); opt_meta.step()
        erreurs = int((decision != ideal).sum())
        journal.append({"episode": episode + 1, "erreurs": erreurs,
                        "confusions": pd.Series([f"{ACTIONS[i]} → {ACTIONS[d]}" for i, d in zip(ideal, decision) if i != d])
                        .value_counts().head(3).to_dict()})
        precision = float((decision == ideal).mean())
        historique.append({"episode": episode + 1, "recompense": total, "curiosite": bonus_total,
                           "epsilon": epsilon, "precision": precision, "desaccord": float((1 - accord).mean())})
        if callback:
            callback(episode + 1, n_episodes, historique[-1])

    return conseil, pd.DataFrame(historique), journal


def decider(conseil, df):
    decision, p, _ = conseil.auto_evaluation(torch.from_numpy(etats(df)))
    return decision, p


def principes_decouverts(conseil, df):
    """Dalio + GEB : l'agent décrit lui-même les règles qu'il a découvertes, en balayant l'écart budgétaire."""
    base = np.median(etats(df), axis=0)
    principes = []
    for tendance, contexte in ((0.0, "quand l'écart est stable"), (0.05, "quand l'écart s'aggrave vite")):
        grille = np.linspace(-0.2, 0.4, 241)
        x = np.tile(base, (len(grille), 1)).astype(np.float32)
        x[:, 0], x[:, 1] = grille, tendance
        decision, _, _ = conseil.deliberer(torch.from_numpy(x))
        for i in range(1, len(grille)):
            if decision[i] != decision[i - 1]:
                principes.append(f"{contexte.capitalize()}, au-delà d'un écart de {grille[i]:+.1%}, "
                                 f"je passe de « {ACTIONS[decision[i - 1]]} » à « {ACTIONS[decision[i]]} ».")
    return principes


def curiosites(df, n=8):
    """Ce qui intrigue l'agent : des écarts inhabituels pour leur centre, même sous les seuils d'alerte."""
    z = df.groupby("centre")["ecart_pct"].transform(lambda s: (s - s.mean()) / (s.std() or 1))
    intrigant = df.assign(singularite=z.abs())
    intrigant = intrigant[(intrigant["singularite"] > 1.5) & (intrigant["situation"] != "grave")]
    return intrigant.sort_values("singularite", ascending=False).head(n)


# ==========================================
# 4. Le tableau de bord (Streamlit)
# ==========================================
DOSSIER_EXEMPLES = Path(__file__).resolve().parent / "exemples"


def monter_interface(st, nom, contenu):
    """Affiche la structure détectée, permet de la corriger et renvoie le tableau standard."""
    analyses = analyser(contenu, nom)
    if not analyses:
        raise ValueError("le fichier est vide.")
    with st.expander("🔧 Montage du contrôle de gestion à partir des données brutes", expanded=True):
        st.caption("La structure et le rôle de chaque colonne sont détectés automatiquement. "
                   "Corrigez-les ici si besoin.")
        for a in analyses:
            cle_widget = f"{nom}|{a['feuille']}"
            st.markdown(f"**Feuille « {a['feuille']} »** — {len(a['df'])} lignes, {a['df'].shape[1]} colonnes")
            formats = list(FORMATS)
            a["format"] = st.selectbox("Structure", formats, index=formats.index(a["format"]),
                                       format_func=FORMATS.get, key=f"format|{cle_widget}")
            if a["format"] != "ignorer":
                options = ["(aucune)"] + list(a["df"].columns)
                colonnes = st.columns(4)
                for i, (role, libelle) in enumerate(ROLES_AFFICHES.items()):
                    actuelle = a["roles"].get(role, "(aucune)")
                    choix = colonnes[i % 4].selectbox(libelle, options, index=options.index(actuelle),
                                                      key=f"role|{role}|{cle_widget}")
                    if choix == "(aucune)":
                        a["roles"].pop(role, None)
                    else:
                        a["roles"][role] = choix
            with st.popover("Aperçu des données brutes"):
                st.dataframe(a["df"].head(15), hide_index=True)
        standard, rapport = monter(analyses)
        st.markdown("**Rapport de montage**")
        st.markdown("\n".join(f"- {ligne}" for ligne in rapport))
        st.dataframe(standard.head(10), hide_index=True)
        st.download_button("Télécharger le tableau monté (CSV)", standard.to_csv(index=False).encode("utf-8"),
                           "controle_gestion_monte.csv", "text/csv")
    return standard


def main():
    import streamlit as st

    st.set_page_config(page_title="IA AISSA — Contrôle de gestion", page_icon="📊", layout="wide")
    verifier_acces(st)
    st.title("📊 IA AISSA — Contrôle de gestion")
    with st.expander("🚀 Croissance d'IA AISSA (concepts maîtrisés par famille de sciences)"):
        afficher_croissance(st, memoire())
    st.caption("Un agent né vide qui apprend seul à détecter les écarts et à rééquilibrer le budget.")

    exemples = {f.name: f for f in sorted(DOSSIER_EXEMPLES.glob("*")) if f.is_file()}
    with st.sidebar:
        st.header("1. Données brutes")
        fichier = st.file_uploader("Fichier CSV ou Excel, quelle que soit sa structure",
                                   type=["csv", "txt", "xlsx", "xlsm", "xls"])
        exemple = st.selectbox("…ou un exemple de données brutes", ["Données simulées"] + list(exemples),
                               disabled=fichier is not None)
        st.header("2. Apprentissage")
        n_episodes = st.slider("Nombre de générations (épisodes)", 5, 100, 30)
        lancer = st.button("🧬 Faire naître et entraîner l'agent", type="primary", width="stretch")

    if fichier is not None:
        nom, contenu = fichier.name, fichier.getvalue()
    elif exemple in exemples:
        nom, contenu = exemple, exemples[exemple].read_bytes()
    else:
        nom = contenu = None
        st.info("Aucun fichier importé : utilisation de données simulées (4 centres × 36 mois).")

    try:
        if contenu is None:
            standard = generer_donnees_exemple()
        else:
            standard = monter_interface(st, nom, contenu)
        df = preparer(standard)
    except Exception as e:
        st.error(f"Impossible de monter le contrôle de gestion : {e}")
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
    avec_ca = df["revenus"].notna()
    c3.metric("Marge moyenne", f"{df.loc[avec_ca, 'marge_pct'].mean():.1%}" if avec_ca.any() else "—")
    c4.metric("Lignes en dérive grave", int((df["situation"] == "grave").sum()))

    st.subheader("Écarts budgétaires par centre")
    pivot = df.pivot_table(index="periode", columns="centre", values="ecart_pct", aggfunc="mean")
    st.line_chart(pivot * 100, y_label="Écart (%)")

    if lancer:
        barre = st.progress(0.0, text="L'agent ouvre les yeux…")

        def suivi(ep, total, h):
            barre.progress(ep / total, text=f"Génération {ep}/{total} — précision {h['precision']:.0%}")

        conseil, historique, journal = entrainer(df, n_episodes=n_episodes, callback=suivi)
        st.session_state["cerveau"] = conseil
        st.session_state["historique"] = historique
        st.session_state["journal"] = journal
        st.session_state["cle_donnees"] = len(df), float(df["reel"].sum())
        barre.empty()

    if "cerveau" not in st.session_state:
        st.warning("Cliquez sur « Faire naître et entraîner l'agent » pour lancer l'apprentissage.")
        return
    if st.session_state.get("cle_donnees") != (len(df), float(df["reel"].sum())):
        st.warning("Les données ont changé : relancez l'entraînement.")
        return

    historique = st.session_state["historique"]
    conseil = st.session_state["cerveau"]
    actions, confiance = decider(conseil, df)
    df["decision_ia"] = [ACTIONS[a] for a in actions]
    df["confiance"] = confiance
    df["statut"] = [statut(p) for p in confiance]
    df["decision_reference"] = df["situation"].map(DECISION_IDEALE).map(ACTIONS)

    st.subheader("🧠 Croissance de l'intelligence")
    g1, g2 = st.columns(2)
    g1.line_chart(historique.set_index("episode")["precision"] * 100, y_label="Précision (%)")
    g2.line_chart(historique.set_index("episode")[["recompense", "curiosite"]],
                  y_label="Récompense / bonus de curiosité")
    st.caption(f"Précision finale par rapport aux règles métier : {historique['precision'].iloc[-1]:.1%}. "
               "Le bonus de curiosité récompense l'exploration de ce que les cerveaux du conseil ignorent : "
               "il s'éteint à mesure qu'ils s'accordent.")

    st.subheader("🪞 Méta-intelligence : IA AISSA juge sa propre pensée")
    parts = df["statut"].value_counts(normalize=True)
    m1, m2, m3 = st.columns(3)
    m1.metric(STATUTS["sur"], f"{parts.get(STATUTS['sur'], 0):.0%}")
    m2.metric(STATUTS["confirmer"], f"{parts.get(STATUTS['confirmer'], 0):.0%}")
    m3.metric(STATUTS["doute"], f"{parts.get(STATUTS['doute'], 0):.0%}")
    if parts.get(STATUTS["doute"], 0) > 0.10:
        st.warning("🤔 Je doute de plus de 10 % de mes décisions sur ces données : je dois réapprendre "
                   "(augmentez le nombre de générations et relancez l'entraînement).")
    else:
        st.success("Je connais mes limites : les décisions marquées « À confirmer » ou « Je ne sais pas » "
                   "méritent l'œil du contrôleur de gestion.")
    st.caption(f"{N_CERVEAUX} cerveaux délibèrent ; chaque vote pèse selon la crédibilité gagnée par ses résultats "
               "(Dalio). Un méta-cerveau, formé sur les erreurs passées du conseil, estime la probabilité que "
               "chaque décision soit juste (boucle étrange de Hofstadter).")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📜 Principes découverts et énoncés par IA AISSA**")
        for principe in principes_decouverts(conseil, df):
            st.markdown(f"- {principe}")
        st.caption("Personne ne lui a donné ces seuils : elle les a trouvés par essais et erreurs.")
    with c2:
        st.markdown("**📓 Journal des erreurs (douleur + réflexion = progrès)**")
        journal = pd.DataFrame(st.session_state.get("journal", []))
        if not journal.empty:
            st.line_chart(journal.set_index("episode")["erreurs"], y_label="Erreurs", height=180)
            confusions = journal["confusions"].iloc[-1]
            st.caption("Confusions restantes : " + (", ".join(f"{k} ({v})" for k, v in confusions.items())
                                                     if confusions else "aucune."))

    st.subheader("🔍 Ce qui intrigue IA AISSA")
    intrigues = curiosites(df)
    if intrigues.empty:
        st.caption("Rien d'inhabituel : chaque centre se comporte comme d'habitude.")
    else:
        st.caption("Des écarts sous les seuils d'alerte, mais inhabituels pour leur centre : la curiosité "
                   "d'IA AISSA les signale pour enquête.")
        st.dataframe(intrigues[["periode", "centre", "budget", "reel", "ecart_pct", "singularite"]], hide_index=True,
                     width="stretch", column_config={
                         "ecart_pct": st.column_config.NumberColumn("Écart %", format="percent"),
                         "singularite": st.column_config.NumberColumn("Singularité (écarts-types)", format="%.1f")})

    st.subheader("📋 Décisions de l'agent")
    f1, f2 = st.columns(2)
    filtre = f1.multiselect("Filtrer par décision", list(ACTIONS.values()), default=[ACTIONS[0], ACTIONS[2]])
    filtre_statut = f2.multiselect("Filtrer par certitude", list(STATUTS.values()))
    vue = df[df["decision_ia"].isin(filtre)] if filtre else df
    vue = vue[vue["statut"].isin(filtre_statut)] if filtre_statut else vue
    st.dataframe(
        vue[["periode", "centre", "budget", "reel", "ecart", "ecart_pct", "tendance",
             "decision_ia", "statut", "confiance", "decision_reference"]],
        width="stretch", hide_index=True,
        column_config={
            "ecart_pct": st.column_config.NumberColumn("Écart %", format="percent"),
            "tendance": st.column_config.NumberColumn("Tendance", format="%.3f"),
            "confiance": st.column_config.ProgressColumn("Confiance (méta)", min_value=0, max_value=1),
        },
    )
    st.download_button("Exporter les décisions (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "decisions_ia.csv", "text/csv")

    buffer = io.BytesIO()
    torch.save(conseil.state_dict(), buffer)
    st.download_button("Sauvegarder le cerveau de l'agent (.pt)", buffer.getvalue(), "cerveau_controle_gestion.pt")


if __name__ == "__main__":
    main()
