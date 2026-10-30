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
    if etat.get("erreurs"):
        with st.expander(f"⚠️ {len(etat['erreurs'])} souci(s) récent(s) du travailleur autonome"):
            st.write("\n".join(f"- {e}" for e in etat["erreurs"]))


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


# ==========================================
# 📚 Livres
# ==========================================
def livres(mem, ingestion_de_livres):
    from .autodidacte import quarantaine
    from .broutage import Brouteur
    from .livres_libres import manger_livre, recommander
    from .pensee import confirmation_ingestion
    ingestion_de_livres(st.session_state.get("utilisateur") or "Aissa")
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
