"""
L'espace administrateur d'IA AISSA (page /admin), réservé à son propriétaire.

- 📊 Tableau de bord : savoir, travailleur autonome, mémoire vive, fréquentation de l'espace visiteurs.
- 📈 Apprentissage : courbes de croissance, bulletin, vitesse par matière, révisions, lacunes, et les corrections
  proposées par les visiteurs, à valider avant qu'elle les apprenne.
- 📚 Livres : déposer des livres (PDF, EPUB), lui faire lire un lien libre, livres lus, quarantaine, bibliothèque.
- 🕹️ Commandes : lancer maintenant un repas, un livre, des crises, une pratique, un élagage ; régler le broutage.
- 👥 Visiteurs et accès : espace ouvert ou réservé, grand moteur et quota des visiteurs, comptes.
- 🔑 Clés et sécurité : clés API de l'application, déconnexion.
Le contenu des conversations des visiteurs n'est jamais affiché ici : seulement des comptes.
"""

import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from . import admin
from .ecole import MATIERES, charger
from .partage import broutage_autonome, memoire


def espace_admin():
    from .interface import (admin_broutage, admin_cles, admin_connexion, admin_deconnexion, admin_utilisateurs,
                            afficher_element, ingestion_de_livres, pouls_d_ia_aissa)
    st.title("🛡️ Administration d'IA AISSA")
    if not admin_connexion():
        st.caption("Espace réservé à l'administrateur. Les visiteurs parlent avec IA AISSA sur la page d'accueil.")
        return
    mem = memoire()
    c1, c2 = st.columns([4, 1])
    c1.caption(f"Connecté : {admin.proprietaire(mem) or st.session_state.get('utilisateur')}")
    if c2.button("Se déconnecter"):
        admin_deconnexion()
    onglets = st.tabs(["📊 Tableau de bord", "📈 Apprentissage", "📚 Livres", "🕹️ Commandes", "👥 Visiteurs et accès",
                       "🔑 Clés et sécurité"])

    with onglets[0]:
        tableau_de_bord(mem)
        pouls_d_ia_aissa()
    with onglets[1]:
        apprentissage(mem, afficher_element)
    with onglets[2]:
        livres(mem, ingestion_de_livres)
    with onglets[3]:
        commandes(mem)
        st.divider()
        admin_broutage()
    with onglets[4]:
        visiteurs(mem)
        st.divider()
        admin_utilisateurs()
    with onglets[5]:
        admin_cles()
        st.divider()
        tracabilite(mem)


# ==========================================
# 📊 Tableau de bord
# ==========================================
def tableau_de_bord(mem):
    from .croissance import serie
    from .pensee import memoire_vive_mo, propositions
    etat = broutage_autonome()
    lacunes, resolues = mem.compter_lacunes()
    freq = pd.DataFrame(mem.frequentation())
    aujourdhui = datetime.now(timezone.utc).date()
    if not freq.empty:
        freq["jour"] = pd.to_datetime(freq["cree_le"], utc=True).dt.date
    du_jour = freq[freq["jour"] == aujourdhui] if not freq.empty else freq
    ligne1 = st.columns(4)
    ligne1[0].metric("Concepts maîtrisés", int(serie(mem).iloc[-1].sum()))
    ligne1[1].metric("Mémoire vive", f"{memoire_vive_mo() or 0:.0f} Mo")
    ligne1[2].metric("Lacunes ouvertes", lacunes - resolues)
    ligne1[3].metric("Corrections à valider", len(propositions(mem)))
    ligne2 = st.columns(4)
    ligne2[0].metric("Conversations aujourd'hui", len(du_jour))
    ligne2[1].metric("Personnes aujourd'hui", du_jour["utilisateur"].nunique() if not du_jour.empty else 0)
    crises = etat.get("crises") or {}
    ligne2[2].metric("Crises bien pilotées", f"{crises.get('justes', 0)}/{crises.get('resolues', 0)}")
    ligne2[3].metric("Repas aujourd'hui", etat.get("repas_du_jour", 0))
    if not freq.empty:
        par_jour = freq[freq["jour"] >= aujourdhui - timedelta(days=30)].groupby("jour").agg(
            Conversations=("utilisateur", "size"), Personnes=("utilisateur", "nunique"))
        st.bar_chart(par_jour, y_label="Fréquentation (30 jours)")
    from .parametres import alertes
    for alerte in alertes(mem):                         # loi de finances de l'année à intégrer, taux à revérifier
        st.warning(alerte)
    dernier = mem.reglage("moteur:dernier_appel")
    if dernier:
        d = json.loads(dernier)
        (st.caption if d["statut"] == "réponse reçue" else st.warning)(
            f"🧠 Dernier appel au grand moteur ({d['moteur']}) le {d['date']} : {d['statut']} en {d['duree_s']} s.")
    temps_d_ouverture()
    if etat.get("erreurs"):
        with st.expander(f"⚠️ {len(etat['erreurs'])} souci(s) récent(s) du travailleur autonome"):
            st.write("\n".join(f"- {e}" for e in etat["erreurs"]))


def temps_d_ouverture():
    """Temps d'ouverture mesuré de chaque page depuis le démarrage du serveur (objectif < 3 s)."""
    from . import chrono
    t = chrono.tableau()
    froid = chrono.demarrage_a_froid()
    with st.expander("⏱️ Temps d'ouverture des pages (objectif < 3 s)", expanded=bool(len(t)) and "⚠️" in set(
            t["Objectif < 3 s"])):
        if froid is not None:
            st.caption(f"Démarrage à froid du serveur (imports et premier affichage) : {froid:.1f} s — payé une seule "
                       "fois, quand Streamlit Cloud réveille l'application. Les cerveaux sont chargés à la demande, "
                       "au premier usage de chaque matière.")
        if len(t):
            st.dataframe(t, hide_index=True, width="stretch")
        else:
            st.caption("Pas encore de mesure depuis le démarrage du serveur.")


# ==========================================
# 📈 Apprentissage
# ==========================================
def apprentissage(mem, afficher_element):
    from .corrections import corriger, reviser
    from .croissance import afficher, vitesse_apprentissage
    from .pensee import propositions
    st.subheader("✅ Corrections proposées par les visiteurs")
    attente = propositions(mem)
    if not attente:
        st.caption("Aucune correction en attente.")
    for cle, p in attente:
        c1, c2, c3 = st.columns([6, 1, 1])
        c1.markdown(f"« {p['question']} » → **{p['reponse']}** ({p['matiere']}) — _proposé par {p['auteur']}_")
        if c2.button("Valider", key=f"ok_{cle}"):
            corriger(mem, "Aissa", p["matiere"], p["question"], p["reponse"], source="utilisateur")
            reviser(mem, p["matiere"])
            mem.supprimer_reglage(cle)
            st.rerun()
        if c3.button("Rejeter", key=f"non_{cle}"):
            mem.supprimer_reglage(cle)
            st.rerun()
    tester_ses_apprentissages(mem)
    banc_d_essai(mem)
    baremes_historiques(mem)
    mises_a_jour_des_taux(mem)
    st.subheader("📈 Croissance")
    afficher(st, mem)
    afficher_element({"type": "bulletin", "titre": "📒 Bulletin de notes"}, "adm_bulletin")
    st.subheader("🧭 Vitesse d'apprentissage par matière")
    st.dataframe(vitesse_apprentissage(mem), hide_index=True, width="stretch")
    st.subheader("🔁 Révisions et pratiques récentes")
    revisions = pd.DataFrame(mem.revisions(50))
    if not revisions.empty:
        st.dataframe(revisions[["cree_le", "matiere", "examen_avant", "examen_apres", "adoptee"]], hide_index=True,
                     width="stretch")
    st.subheader("❓ Lacunes ouvertes (ce qu'elle ne sait pas encore)")
    st.dataframe(pd.DataFrame(mem.lacunes_ouvertes(50)), hide_index=True, width="stretch")
    st.subheader("✍️ Corrections apprises")
    corrections = pd.DataFrame(mem.corrections_de())
    if not corrections.empty:
        st.dataframe(corrections.sort_values("id", ascending=False)[["cree_le", "matiere", "question", "bonne_reponse",
                                                                     "source", "apprise"]].head(100),
                     hide_index=True, width="stretch")


def tester_ses_apprentissages(mem):
    """L'examen de lecture (automatique) et les questions de test de l'administrateur, suivis dans le temps."""
    from .lecture import examen_lecture, historique_examens
    from .pensee import penser
    st.subheader("🧪 Tester ses apprentissages")
    comptes = pd.DataFrame(mem.compter_passages())
    if comptes.empty:
        st.warning("Sa mémoire de lecture est vide : déposez des livres dans l'onglet 📚 Livres. (Sans MEMOIRE_URL, elle "
                   "est effacée à chaque redémarrage du serveur.)")
    else:
        st.caption(f"Mémoire de lecture : {int(comptes['passages'].sum())} passages, {len(comptes)} document(s).")
        st.dataframe(comptes, hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    if c1.button("📝 Examen de lecture (20 phrases à trous)", width="stretch"):
        b = examen_lecture(mem)
        st.session_state["dernier_examen"] = b
    b = st.session_state.get("dernier_examen")
    if b:
        c2.metric("Mots cachés retrouvés", f"{b['mot_retrouve']}/{b['questions']}",
                  help=f"Passage d'origine retrouvé : {b['passage_retrouve']}/{b['questions']}")
        st.dataframe(pd.DataFrame(b["exemples"]), hide_index=True, width="stretch")
    historique = pd.DataFrame(historique_examens(mem))
    if len(historique) > 1:
        historique["quand"] = pd.to_datetime(historique["quand"], unit="s")
        st.line_chart(historique.set_index("quand")["score"], y_label="Score de l'examen de lecture")
    st.markdown("**Votre question de test** (elle répond comme à un visiteur, sans grand moteur)")
    c1, c2 = st.columns([3, 2])
    question = c1.text_input("Question", key="test_q", placeholder="Quels sont les taux de TVA en 2026 ?")
    attendu = c2.text_input("Mot ou chiffre attendu dans la réponse", key="test_a", placeholder="20 %")
    if st.button("▶️ Lui poser la question") and question:
        reponse, etapes, confiance = penser(question, mem, utilisateur="Bibliothèque")
        reussi = bool(attendu) and attendu.lower() in reponse.lower()
        mem.definir_reglage(f"test_question:{int(datetime.now().timestamp() * 1000)}", json.dumps(
            {"question": question, "attendu": attendu, "reussi": reussi, "confiance": confiance}, ensure_ascii=False))
        (st.success if reussi else st.error)(("✅ Réussi" if reussi else "❌ Pas trouvé") + f" — confiance {confiance:.0%}")
        st.markdown(reponse)
        st.caption(" → ".join(etapes))
    tests = [json.loads(v) for _, v in sorted(mem.reglages("test_question:").items())]
    if tests:
        st.caption(f"Vos questions de test : {sum(t['reussi'] for t in tests)}/{len(tests)} réussies")
        st.dataframe(pd.DataFrame(tests[::-1]), hide_index=True, width="stretch")


# ==========================================
# 📚 Livres
# ==========================================
def livres(mem, ingestion_de_livres):
    from .autodidacte import quarantaine
    from .broutage import Brouteur
    from .livres_libres import manger_livre, recommander
    from .pensee import confirmation_ingestion
    ingestion_de_livres("Bibliothèque")             # les livres de l'administrateur servent à tous les visiteurs
    st.subheader("🔗 Lui faire lire un livre libre en ligne")
    lien = st.text_input("Lien direct vers un PDF ou un EPUB libre (OpenStax, Wikilivres…)", key="adm_lien_livre")
    if st.button("📖 Lire ce livre maintenant") and lien:
        with st.spinner("Je vérifie que le site m'autorise, puis je lis…"):
            try:
                st.success(confirmation_ingestion(manger_livre(mem, Brouteur(), lien.strip(), utilisateur="IA AISSA")))
            except Exception as e:
                st.error(f"Refusé ou impossible : {e}")
    st.subheader("📗 Livres lus seule (ou refusés)")
    lus = [{"lien": k.split(":", 1)[1], **json.loads(v)} for k, v in mem.reglages("livre_lu:").items()]
    st.dataframe(pd.DataFrame(lus), hide_index=True, width="stretch") if lus else st.caption("Aucun pour l'instant.")
    st.subheader("🧪 Quarantaine (hors de son programme)")
    q = quarantaine(mem)
    st.dataframe(pd.DataFrame(q), hide_index=True, width="stretch") if q else st.caption("Rien en quarantaine.")
    st.subheader("🏛️ Bibliothèque")
    lignes = [{"date": d["cree_le"], "source": d["source"], "lecteur": d["utilisateur"], "famille": d["famille"],
               "concepts": len(json.loads(d["concepts"])), "confiance": d["confiance"]} for d in mem.digestions(300)]
    if lignes:
        st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")
    with st.expander("📌 Bibliothèques libres recommandées"):
        st.markdown(recommander())


# ==========================================
# 🕹️ Commandes
# ==========================================
def commandes(mem):
    from .autodidacte import pratiquer, resoudre_crises
    from .broutage import Brouteur, cycle
    from .livres_libres import repas_de_livre
    from .pensee import alleger, elaguer
    st.caption("Lancer tout de suite ce que le travailleur autonome fait d'habitude tout seul.")
    c = st.columns(3)
    if c[0].button("🌿 Un repas sur le web", width="stretch"):
        with st.spinner("Je broute…"):
            try:
                b = cycle(mem, None, None, Brouteur())
                st.success(f"« {b['sujet']} » : {b['concepts']} concept(s)" + (" (quarantaine)" if b.get("quarantaine")
                                                                                   is not None else ""))
            except Exception as e:
                st.error(str(e))
    if c[1].button("📖 Un manuel libre", width="stretch"):
        with st.spinner("Je cherche un manuel libre autorisé…"):
            try:
                b = repas_de_livre(mem, Brouteur())
                st.success(f"{b['source']} : {b['concepts']} concepts" if b["source"] else
                           "Rien de nouveau à lire. " + " ; ".join(b["refus"]))
            except Exception as e:
                st.error(str(e))
    if c[2].button("🚨 5 crises budgétaires", width="stretch"):
        b = resoudre_crises(mem)
        st.success(f"{b['justes']}/{b['crises']} bien pilotées" + (" — pratique lancée" if b["pratique"] else ""))
    c = st.columns(3)
    matieres = ["(celle où elle progresse le plus)"] + [m.cle for m in MATIERES if m.cle != "orientation"]
    choix = c[0].selectbox("Matière", matieres, label_visibility="collapsed")
    if c[0].button("🏋️ Séance de pratique", width="stretch"):
        with st.spinner("Je m'exerce…"):
            b = pratiquer(mem, None if choix.startswith("(") else choix)
            st.success(f"{b['nom']} : {b['avant']:.0%} → {b['apres']:.0%} " + ("✅ adoptée" if b["adoptee"] else
                                                                              "(non adoptée : pas de progrès)")
                       if b else "Rien à pratiquer.")
    if c[1].button("🧹 Élaguer la mémoire", width="stretch"):
        b = elaguer(mem, forcer=True)
        st.success(f"{b['fusionnes']} doublon(s) fusionné(s), {b['oublies']} fait(s) oublié(s)")
    if c[2].button("🪶 Alléger la mémoire vive", width="stretch"):
        b = alleger(plafond=0)
        st.success(f"{b['avant']} Mo → {b['apres']} Mo")
    repas_du_jour_admin(mem)


def repas_du_jour_admin(mem):
    """Le repas du jour : une lacune, l'article de Wikipédia qui y répond, lu et vérifié."""
    from .nourrir import historique, nourrir_du_jour
    st.subheader("🍽️ Nourrir IA AISSA chaque jour")
    st.caption("À la première visite de la journée, elle choisit une de ses lacunes, lit l'article de Wikipédia qui y "
               "répond et vérifie qu'elle sait désormais y répondre (au plus un appel au grand moteur par jour).")
    if st.button("🍽️ Nourrir IA AISSA maintenant (une lacune)"):
        with st.spinner("Je choisis une lacune et je lis l'article qui y répond…"):
            from .assistant import MOTEURS, client_moteur
            from .partage import secret
            moteur = next((m for m, c in MOTEURS.items() if secret(c["secret"]) and not c.get("local")), None)
            b = nourrir_du_jour(mem, MOTEURS[moteur] if moteur else None,
                                client_moteur(moteur, secret(MOTEURS[moteur]["secret"])) if moteur else None, forcer=True)
        if b["source"]:
            st.success(f"« {b['lacune']} » → {b['source']} : {b['concepts']} concept(s), "
                       + ("lacune résolue ✅" if b["resolue"] else "pas encore assez pour y répondre"))
        else:
            st.info("Aucune lacune à nourrir aujourd'hui." if not b["essais"] else
                    "Aucun article trouvé : " + " ; ".join(b["essais"]))
    if st.button("📊 Mettre à jour les données ouvertes (Banque mondiale)"):
        from .donnees_ouvertes import repas_donnees_ouvertes
        with st.spinner("Je lis les derniers indicateurs du Maroc…"):
            try:
                b = repas_donnees_ouvertes(mem, forcer=True)
                st.success(f"{b['indicateurs']} indicateurs lus (jusqu'à {b['annee_la_plus_recente']}) et rangés dans ma "
                           "mémoire de lecture.")
            except Exception as e:
                st.error(f"Impossible pour l'instant : {e}")
    if st.button("🇲🇦 Mettre à jour les données officielles marocaines (HCP, Bank Al-Maghrib, CNSS)"):
        from .donnees_maroc import repas_donnees_maroc
        with st.spinner("Je lis les catalogues et les tableaux de data.gov.ma…"):
            try:
                b = repas_donnees_maroc(mem, forcer=True)
                st.success(f"Catalogues : {b['catalogues']} ; {len(b['tableaux'])} tableau(x) lu(s)."
                           + (f" Refus : {' ; '.join(b['refus'])}" if b["refus"] else ""))
            except Exception as e:
                st.error(f"Impossible pour l'instant : {e}")
    maroc = mem.reglage("donnees_maroc:derniere")
    if maroc:
        d = json.loads(maroc)
        st.caption(f"Données officielles marocaines lues le {d['date']} : catalogues {d['catalogues']}, "
                   + ", ".join(f"{t['institution']} — {t['titre']}" for t in d["tableaux"]) + " (licence ODbL).")
    derniere = mem.reglage("donnees_ouvertes:derniere")
    if derniere:
        d = json.loads(derniere)
        st.caption(f"Données ouvertes : {d['indicateurs']} indicateurs de la Banque mondiale, lus le {d['date']} "
                   "(mises à jour chaque semaine, licence CC BY 4.0).")
    repas = historique(mem)
    if repas:
        st.dataframe(pd.DataFrame([{"Jour": r["date"], "Lacune": r["lacune"], "Article lu": r["source"],
                                    "Concepts": r["concepts"], "Résolue": "✅" if r["resolue"] else "—",
                                    "Appel au moteur": "oui" if r["moteur_utilise"] else "non"} for r in repas]),
                     hide_index=True, width="stretch")


# ==========================================
# 👥 Visiteurs et accès
# ==========================================
def visiteurs(mem):
    from .interface import QUOTA_VISITEUR
    acces = admin.valeur_app(mem, "ACCES_VISITEURS") or "ouvert"
    choix = st.radio("Espace visiteurs", ["ouvert", "reserve"], index=["ouvert", "reserve"].index(acces),
                     format_func=lambda v: "🌍 Ouvert à tous" if v == "ouvert" else "🔒 Réservé aux comptes autorisés",
                     horizontal=True)
    if choix != acces:
        admin.definir_valeur_app(mem, "ACCES_VISITEURS", choix)
        st.rerun()
    moteur = (admin.valeur_app(mem, "VISITEURS_MOTEUR") or "oui") != "non"
    if st.toggle("Les visiteurs profitent du grand moteur (clé de l'application)", value=moteur) != moteur:
        admin.definir_valeur_app(mem, "VISITEURS_MOTEUR", "non" if moteur else "oui")
        st.rerun()
    quota = int(admin.valeur_app(mem, "QUOTA_VISITEUR") or QUOTA_VISITEUR)
    nouveau = st.number_input("Messages par visiteur et par jour avec le grand moteur", 0, 1000, quota)
    if nouveau != quota:
        admin.definir_valeur_app(mem, "QUOTA_VISITEUR", nouveau)
    st.caption("Au-delà du quota, IA AISSA répond avec son propre cerveau. Les conversations des visiteurs restent "
               "privées : ici, seulement des comptes.")


# ==========================================
# Traçabilité des rapports et barèmes historiques
# ==========================================
def tracabilite(mem):
    """Journal des rapports de simulation émis (démarche qualité) et vérification de l'intégrité d'un rapport."""
    from .rapports import journal, verifier
    st.subheader("🧾 Journal des rapports de simulation")
    st.caption("Chaque PDF téléchargé est enregistré avec son numéro, sa date, sa version et son empreinte SHA-256.")
    lignes = journal(mem)
    if lignes:
        st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch")
    else:
        st.caption("Aucun rapport émis pour l'instant.")
    c1, c2, c3 = st.columns([2, 3, 1])
    numero = c1.text_input("N° du rapport", key="verif_num", placeholder="IAA-20261030-…")
    empreinte = c2.text_input("Empreinte SHA-256 lue sur le PDF", key="verif_sha")
    if c3.button("Vérifier") and numero and empreinte:
        if verifier(mem, numero, empreinte):
            st.success("✅ Rapport authentique : numéro et empreinte correspondent au journal.")
        else:
            st.error("❌ Rapport inconnu ou modifié : l'empreinte ne correspond pas.")


def banc_d_essai(mem):
    """Le banc d'essai permanent : questions libres jamais vues, aux deux niveaux, et l'évolution séance après séance."""
    from . import banc
    st.subheader("🧪 Banc d'essai des questions libres")
    st.caption(f"{len(banc.TOUTES)} questions en français et en darija, jamais vues telles quelles. « Pensée propre » = "
               "ce qu'un visiteur reçoit sans clé ; « cerveaux d'école » = l'aiguilleur et les matières seuls.")
    seances = banc.historique(mem)
    if seances:
        suivi = pd.DataFrame([{"Séance": s["date"], "Pensée propre (%)": round(100 * s["pensee"] / s["questions"], 1),
                               "Cerveaux d'école (%)": round(100 * s["ecole"] / s["questions"], 1)} for s in seances])
        st.line_chart(suivi.set_index("Séance"), y_label="Réussite (%)")
        derniere = seances[-1]
        st.caption(f"Dernière séance ({derniere['date']}) : pensée propre {derniere['pensee']}/{derniere['questions']}, "
                   f"cerveaux d'école {derniere['ecole']}/{derniere['questions']}.")
    if st.button("▶️ Lancer le banc d'essai maintenant"):
        with st.spinner("IA AISSA répond aux questions du banc…"):
            r = banc.evaluer(memoire=mem)
            banc.garder(r, mem)
        st.success(f"Pensée propre {r['pensee']}/{r['questions']} · cerveaux d'école {r['ecole']}/{r['questions']}")
        if r["ratees_pensee"]:
            st.warning("Ratées par la pensée propre : " + " ; ".join(r["ratees_pensee"]))
        st.dataframe(pd.DataFrame(r["lignes"]), hide_index=True, width="stretch")


def mises_a_jour_des_taux(mem):
    """Mettre à jour un taux ou un seuil (SMIG, CNSS, AMO…) avec son texte légal et sa source : appliqué aussitôt."""
    from . import parametres as P
    st.subheader("📅 Mises à jour des taux et seuils")
    for alerte in P.alertes(mem):
        st.warning(alerte)
    st.dataframe(P.registre(mem).drop(columns=["Clé"]), hide_index=True, width="stretch")
    with st.form("mise_a_jour_taux"):
        cles = [p[0] for p in P.PARAMETRES]
        cle = st.selectbox("Paramètre", cles, format_func=lambda k: P.PAR_CLE[k][3])
        c = st.columns(2)
        valeur = c[0].number_input("Nouvelle valeur (un taux en décimal : 0,0448 pour 4,48 %)", 0.0, value=0.0,
                                   format="%.4f")
        depuis = c[1].text_input("En vigueur depuis (ex. 01/01/2027)")
        texte = st.text_input("Texte légal (décret, loi de finances, article…)")
        source = st.text_input("Source consultée (Bulletin officiel n° …, site de la DGI, de la CNSS…)")
        if st.form_submit_button("Enregistrer et appliquer"):
            try:
                P.mettre_a_jour(mem, cle, valeur, depuis or "—", texte, source)
                st.success(f"{P.PAR_CLE[cle][3]} : {P.afficher_valeur(valeur, P.PAR_CLE[cle][4])} appliqué à toutes "
                           "les simulations.")
            except ValueError as e:
                st.error(f"Mise à jour refusée : {e}")
    modifies = [k for k in P.PAR_CLE if P.historique(mem, k)]
    if modifies:
        c = st.columns([3, 1])
        cle = c[0].selectbox("Annuler la dernière mise à jour de", modifies, format_func=lambda k: P.PAR_CLE[k][3])
        if c[1].button("↩️ Annuler", width="stretch"):
            P.annuler(mem, cle)
            st.rerun()


def baremes_historiques(mem):
    """Ajouter un barème d'IR d'une autre période, lu dans un texte officiel, avec sa source (obligatoire)."""
    from .baremes import ajouter_bareme_ir, annees_couvertes
    st.subheader("📏 Barèmes historiques de l'IR")
    st.caption("Années couvertes : " + ", ".join(map(str, annees_couvertes("ir", mem))) + ". Pour une autre période "
               "(années 90, 2000…), recopiez le barème du Bulletin officiel ou de la loi de finances, avec sa référence.")
    with st.form("bareme_ir"):
        c = st.columns(2)
        de = c[0].number_input("De l'année", 1950, 2100, 1996)
        a = c[1].number_input("À l'année", 1950, 2100, 1996)
        loi = st.text_input("Texte de loi (ex. : loi de finances n° …, article …)")
        source = st.text_input("Source consultée (ex. : Bulletin officiel n° … du …)")
        tranches = st.text_area("Tranches : une par ligne « plafond ; taux % ; somme à déduire » (dernière tranche : "
                                "plafond vide)", "30000 ; 0 ; 0\n50000 ; 10 ; 3000\n ; 38 ; 24400")
        if st.form_submit_button("Ajouter ce barème"):
            try:
                lues = []
                for ligne in tranches.splitlines():
                    if ligne.strip():
                        p, t, d = [x.strip().replace(" ", "") for x in ligne.split(";")]
                        lues.append((float(p) if p else None, float(t.replace(",", ".")) / 100, float(d or 0)))
                ajouter_bareme_ir(mem, de, a, loi, source, lues)
                st.success(f"Barème {de}–{a} ajouté avec sa source.")
            except ValueError as e:
                st.error(f"Barème refusé : {e}")
