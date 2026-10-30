"""
L'espace unique d'IA AISSA : un seul écran, l'alien et une ligne de conversation.

Selon ce qu'on lui donne, IA AISSA change de rôle (sa « matrice » intérieure) :
- 💻 Programmeur senior : une demande de code (avec Claude, le code est exécuté dans un bac à sable sécurisé) ;
- 🎓 Prof / Savant : une question de science ou d'école ;
- 📊 Contrôleur de gestion : un fichier de données (CSV, Excel) ou une question de budget, d'écarts, de coûts ;
- 💡 Inventeur : « invente… », « une idée pour… » ;
- 📚 Lecteur : un lien internet ou un document (PDF, texte) à manger et ruminer ;
- 👽 Compagnon : tout le reste.
"""

import re

from .ecole import SEUIL_CONFIANCE, repondre_automatiquement

ROLES = {
    "compagnon": ("👽 Compagnon", ""),
    "programmeur": ("💻 Programmeur senior", (
        "Rôle actuel : programmeur senior. Écris du code propre, commenté et robuste, explique les choix, signale les "
        "cas limites. Quand l'outil d'exécution de code est disponible, exécute ton code pour le vérifier et montre le "
        "résultat réel ; ne prétends jamais avoir exécuté du code sans l'avoir fait.")),
    "savant": ("🎓 Prof / Savant", (
        "Rôle actuel : professeur et savant. Explique pas à pas, du plus simple au plus profond, avec des exemples, "
        "des exercices corrigés si utile, les formules et leurs unités, et les limites des connaissances actuelles.")),
    "controleur": ("📊 Contrôleur de gestion", (
        "Rôle actuel : contrôleur de gestion. Calcule avec les outils (pas de tête), analyse les écarts budget/réel, "
        "repère les erreurs et incohérences dans les chiffres, explique leurs causes probables, chiffre leur impact "
        "et propose des actions correctives priorisées. Termine par un diagnostic clair.")),
    "inventeur": ("💡 Inventeur", (
        "Rôle actuel : inventeur. Croise des domaines éloignés (TRIZ, SCAMPER, analogies), puis critique sans "
        "complaisance (faisabilité, coût, équilibre financier) avant de proposer la meilleure idée.")),
    "lecteur": ("📚 Lecteur", "Rôle actuel : lecteur. Résume fidèlement, extrais les concepts clés et cite la source."),
}

SEUIL_ROLE = 0.5            # confiance minimale d'un cerveau d'école pour changer de rôle à partir d'une question
EXTENSIONS_DONNEES = (".csv", ".xlsx", ".xlsm", ".xls")
EXTENSIONS_LECTURE = (".pdf", ".txt", ".md", ".html", ".htm")
MOTIF_URL = re.compile(r"https?://[^\s<>\"']+")
MOTIFS = {
    "programmeur": re.compile(r"\b(code|coder|python|javascript|typescript|java|sql|php|html|css|script|programm\w*|"
                              r"algorithme|fonction python|bug|débogu\w*|debug\w*|regex|api|vba|compil\w*)\b", re.I),
    "inventeur": re.compile(r"\b(invent\w*|innov\w*|brevet|imagine[rz]?|une idée (de|pour)|des idées (de|pour))\b", re.I),
    "controleur": re.compile(r"(budget|écart|ecart|contr[ôo]le de gestion|réalisé|realise|charges? (fixes|variables)|"
                             r"co[ûu]ts?\b|marge|rentabilit|tableau de bord|kpi|chiffre d'affaires|trésorerie|"
                             r"seuil de rentabilité|bilan|compte de résultat)", re.I),
    "savant": re.compile(r"\b(qu'est[- ]ce qu|explique|expliquer|démontr\w*|théorème|équation|formule|cellule|atome|"
                         r"molécule|physique|chimie|biologie|svt|math\w*|géométrie|histoire|géographie|philosoph\w*|"
                         r"cours|exercice|leçon|bac|examen|photosynth\w*|planète|univers|énergie|science\w*)\b", re.I),
}
INTENTIONS = {
    "bulletin": re.compile(r"(bulletin|ta croissance|tes progrès|tes notes|ce que tu (as appris|sais)|ton école)", re.I),
    "bibliotheque": re.compile(r"(ta bibliothèque|qu'as[- ]tu lu|ce que tu as lu|tes lectures)", re.I),
    "prononciation": re.compile(r"(pronon\w+|apprends?[- ]moi à (dire|parler)|accent)", re.I),
}
DOMAINES_GESTION = ("Comptabilité", "Fiscalité", "Finance", "Contrôle de gestion", "Ressources humaines", "Commercial",
                    "Gestion", "Banque", "Stratégie", "Marketing", "Logistique", "Transit", "Commerce international",
                    "Création d'entreprise", "Université — gestion")


def urls(texte):
    return MOTIF_URL.findall(texte or "")


def intention(texte):
    return next((nom for nom, motif in INTENTIONS.items() if motif.search(texte or "")), None)


def detecter_role(texte, noms_fichiers=()):
    """Choisit le rôle d'IA AISSA d'après la demande : fichiers, liens, mots-clés, puis ses propres cerveaux."""
    noms = [n.lower() for n in noms_fichiers]
    if any(n.endswith(EXTENSIONS_DONNEES) for n in noms):
        return "controleur"
    if any(n.endswith(EXTENSIONS_LECTURE) for n in noms) or urls(texte):
        return "lecteur"
    for role in ("programmeur", "inventeur", "controleur", "savant"):
        if MOTIFS[role].search(texte or ""):
            return role
    if len((texte or "").strip()) >= 6:
        meilleure = repondre_automatiquement(texte)[0]
        if meilleure["confiance"] >= SEUIL_ROLE:
            if meilleure["domaine"].startswith(DOMAINES_GESTION):
                return "controleur"
            return "savant"
    return "compagnon"


def reponse_locale(texte, memoire=None, conclusion=None):
    """Sans clé API : IA AISSA pense avec ses propres cerveaux (calcul, analogie, école, bibliothèque),
    montre son raisonnement et dit honnêtement quand elle ne sait pas."""
    from .pensee import penser
    reponse, etapes, confiance = penser(texte, memoire, conclusion)
    return reponse, etapes, confiance


def analyser_controle(nom, contenu, n_episodes=None):
    """Le Contrôleur de gestion : montage des données brutes, agent méta-intelligent, diagnostic.
    Renvoie un résumé texte (pour la voix et le moteur) et des éléments à afficher dans la conversation."""
    import controle_gestion_ia as cg
    from montage import analyser, monter

    standard, rapport = monter(analyser(contenu, nom))
    df = cg.preparer(standard)
    if df.empty:
        raise ValueError("aucune ligne exploitable après le montage.")
    # petit fichier = plus d'épisodes pour apprendre (environ 1 500 décisions au total), dans une limite raisonnable
    n_episodes = n_episodes or min(60, max(15, 1500 // len(df)))
    conseil, historique, journal = cg.entrainer(df, n_episodes=n_episodes)
    decisions, confiance = cg.decider(conseil, df)
    df["decision_ia"] = [cg.ACTIONS[a] for a in decisions]
    df["statut"] = [cg.statut(p) for p in confiance]
    budget, reel = float(df["budget"].sum()), float(df["reel"].sum())
    graves = df[df["decision_ia"] == cg.ACTIONS[0]]
    lisible = df.assign(ecart_pct=df["ecart_pct"].map(lambda v: f"{v:+.1%}"))       # écarts affichés en %
    doutes = int((df["statut"] == cg.STATUTS["doute"]).sum())
    intrigues = cg.curiosites(df)
    principes = cg.principes_decouverts(conseil, df)
    par_centre = (df.groupby("centre")[["budget", "reel"]].sum()
                  .assign(ecart_pct=lambda d: (d["reel"] - d["budget"]) / d["budget"]).sort_values("ecart_pct"))
    pire = par_centre.index[-1]
    previsions = cg.prevoir(df)
    montant = lambda v: f"{v:,.0f}".replace(",", " ")
    resume = (f"Fichier « {nom} » : {df['centre'].nunique()} centre(s), {df['periode'].nunique()} période(s). "
              f"Budget {montant(budget)}, réalisé {montant(reel)}, écart global {(reel - budget) / budget:+.1%}. "
              f"Centre le plus en dérive : {pire} ({par_centre.loc[pire, 'ecart_pct']:+.1%}). "
              f"{len(graves)} alerte(s) d'écart grave, {doutes} décision(s) dont je doute, "
              f"{len(intrigues)} écart(s) inhabituel(s) à vérifier. Principes découverts : "
              + (" ".join(principes[:2]) or "pas encore assez d'épisodes pour en énoncer.")
              + ("" if previsions.empty else
                 f" Prévision du réalisé pour {previsions['periode'].iloc[0]} : "
                 + ", ".join(f"{p.centre} {montant(p.prevision)} (entre {montant(p.bas_95)} et {montant(p.haut_95)})"
                             for p in previsions.itertuples()) + "."))
    elements = [
        {"type": "metriques", "valeurs": [("Budget", f"{budget:,.0f}".replace(",", " ")),
                                         ("Réalisé", f"{reel:,.0f}".replace(",", " ")),
                                         ("Écart global", f"{(reel - budget) / budget:+.1%}"),
                                         ("Alertes graves", str(len(graves)))]},
        {"type": "graphique", "titre": "Écart budgétaire par centre (%)",
         "donnees": df.pivot_table(index="periode", columns="centre", values="ecart_pct", aggfunc="mean") * 100},
        {"type": "liste", "titre": "📜 Principes découverts par IA AISSA", "lignes": principes},
        {"type": "tableau", "titre": "🔮 Prévision du réalisé de la période suivante (intervalle de confiance 95 %)",
         "donnees": previsions},
        {"type": "liste", "titre": "🔧 Montage des données brutes", "lignes": rapport},
        {"type": "tableau", "titre": "🚨 Alertes et décisions dont je doute",
         "donnees": lisible[(df["decision_ia"] == cg.ACTIONS[0]) | (df["statut"] != cg.STATUTS["sur"])]
         [["periode", "centre", "budget", "reel", "ecart_pct", "decision_ia", "statut"]].head(30)},
        {"type": "telechargement", "libelle": "Exporter toutes les décisions (CSV)", "nom": "decisions_ia_aissa.csv",
         "donnees": df.to_csv(index=False).encode("utf-8")},
    ]
    if not intrigues.empty:
        elements.insert(4, {"type": "tableau", "titre": "🔍 Ce qui intrigue IA AISSA",
                            "donnees": lisible.loc[intrigues.index, ["periode", "centre", "budget", "reel", "ecart_pct"]]})
    return resume, elements, float(historique["precision"].iloc[-1])
