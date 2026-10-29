import json
import time

import pandas as pd
import streamlit as st

from ia_aissa.acces import verifier_acces
from ia_aissa.assistant import MOTEURS, client_moteur
from ia_aissa.avatar import avatar
from ia_aissa.invention import annonce_darija, debattre, evoluer
from ia_aissa.parole import synthetiser
from ia_aissa.partage import memoire, secret

st.set_page_config(page_title="Laboratoire d'invention", page_icon="💡", layout="wide")
utilisateur = verifier_acces(st)
st.title("💡 Laboratoire d'invention d'IA AISSA")
st.caption("IA AISSA se dédouble dans son univers : le **Créateur** croise des domaines éloignés (TRIZ, SCAMPER, "
           "analogies), le **Critique** applique la règle de Dalio (faisabilité, ressources, équilibre financier, "
           "affirmations douteuses). Les idées évoluent comme des gènes, puis la meilleure est affinée par un débat.")

moteurs = list(MOTEURS)
moteur = st.session_state.get("moteur_choisi", moteurs[0])
config = MOTEURS[moteur]
cle_api = secret(config["secret"]) or st.session_state.get(f"cle_visite_{config['secret']}")

probleme = st.text_area("Quel problème voulez-vous résoudre ? (tous domaines)",
                        placeholder="ex. : réduire les retards de paiement des clients d'une PME marocaine")
c1, c2, c3 = st.columns(3)
generations = c1.slider("Générations d'idées", 1, 4, 2)
taille = c2.slider("Idées par génération", 4, 8, 4)
tours = c3.slider("Tours de débat Créateur × Critique", 1, 4, 3)
st.caption(f"Moteur : {moteur} · environ {2 * generations + 2 * tours} appels au moteur pour cette invention.")

if not cle_api:
    st.info("Le laboratoire a besoin d'une clé API : ajoutez-la dans les secrets, ou collez-la dans la page "
            "« 💬 Parler avec IA AISSA » (elle est gardée pour toute la visite).")
elif probleme.strip() and st.button("🚀 Lancer l'invention", type="primary"):
    client = client_moteur(moteur, cle_api)
    portail = st.empty()
    portail.iframe(avatar("Hyper-propulsion activée : mon Créateur et mon Critique se mettent au travail…",
                          etat="hyper", lecture_auto=False), height=330)
    debut = time.time()
    suivi = st.progress(0.0, text="Génération 1…")
    courbe = []

    def apres_generation(g, total, population):
        scores = [i["score"] for i in population]
        courbe.append({"génération": g, "meilleure": max(scores), "moyenne": sum(scores) / len(scores)})
        suivi.progress(g / (total + 1), text=f"Génération {g}/{total} : meilleure idée {max(scores):.1f}/10")

    with st.spinner("🧬 Évolution des idées…"):
        historique, meilleure = evoluer(config, client, probleme, generations, taille, callback=apres_generation)
    with st.spinner("⚔️ Débat entre le Créateur et le Critique…"):
        finale, debat, meta = debattre(config, client, probleme, meilleure, tours,
                                       callback=lambda t, n, i: suivi.progress(
                                           0.5 + 0.5 * t / n, text=f"Débat : tour {t}/{n}"))
    duree = time.time() - debut
    suivi.empty()
    texte_darija, sens = annonce_darija(finale, meta, nom=utilisateur)
    try:
        audio = synthetiser(texte_darija, "Darija")
    except Exception:
        audio = None
    image, type_image = memoire().media("avatar")
    portail.iframe(avatar(texte_darija, audio, "ar-MA", image, type_image or "image/png", etat="hyper",
                          indicateur={"confiance": meta["confiance"],
                                      "details": f"{generations} génération(s) · débat {tours} tours · {duree:.0f} s"}),
                   height=360)
    st.caption(f"Proverbe : {sens}")

    st.subheader(f"🏆 {finale['titre']}")
    st.write(finale.get("description", ""))
    m1, m2, m3 = st.columns(3)
    m1.metric("Score de confiance (méta-intelligence)", f"{meta['confiance']:.0%}")
    m2.metric("Faisabilité (Critique)", f"{meta['faisabilite']:.0%}")
    m3.metric("Affirmations encore douteuses", meta["doutes_restants"])
    if courbe:
        st.line_chart(pd.DataFrame(courbe).set_index("génération"), y_label="Score des idées (/10)")
    with st.expander("⚔️ Le débat intérieur"):
        for tour in debat:
            if tour["agent"] == "Critique":
                st.markdown(f"**Tour {tour['tour']} — Critique** (faisabilité {tour['faisabilite']:.0f}, efficience "
                            f"{tour['efficience']:.0f}, équilibre financier {tour['equilibre_financier']:.0f} /10)")
                for o in tour["objections"]:
                    st.markdown(f"- ❌ {o}")
                for a in tour["affirmations_a_verifier"]:
                    st.markdown(f"- ⚠️ À vérifier : {a}")
            else:
                st.markdown(f"**Tour {tour['tour']} — Créateur** : {tour['titre']}")
                for r in tour["reponses"]:
                    st.markdown(f"- ✅ {r}")
    with st.expander("🧬 Toutes les idées de l'évolution"):
        for g, gen in enumerate(historique, 1):
            for i in gen:
                st.markdown(f"G{g} · **{i['titre']}** ({i['score']:.1f}/10) — {i.get('description', '')}")
    memoire().garder_idee(utilisateur, probleme, finale["titre"], finale.get("description", ""), meta["confiance"],
                          meta["faisabilite"], json.dumps({"debat": debat, "meta": meta}, ensure_ascii=False))
    st.caption("Ces idées sont des pistes à valider : vérifiez l'existant (brevets, produits), les coûts et la "
               "réglementation avant de vous lancer.")

st.subheader("🗂️ Galerie de mes inventions")
galerie = memoire().idees_de(utilisateur)
if galerie:
    for i in galerie:
        with st.expander(f"{i['titre']} — confiance {i['confiance']:.0%} · {i['cree_le']:%d/%m/%Y}"):
            st.caption(f"Problème : {i['probleme']}")
            st.write(i["description"])
else:
    st.caption("Aucune invention pour l'instant.")
