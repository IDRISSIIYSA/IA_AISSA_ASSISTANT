import json

import pandas as pd
import streamlit as st

from ia_aissa.acces import verifier_acces
from ia_aissa.assistant import MOTEURS, client_moteur
from ia_aissa.avatar import avatar
from ia_aissa.bibliotheque import (ErreurBroutage, brouter_fichier, brouter_lien, brouter_wikipedia, chercher, digerer,
                                   explorer_lacunes)
from ia_aissa.partage import memoire, secret

st.set_page_config(page_title="Bibliothèque d'IA AISSA", page_icon="📚", layout="wide")
utilisateur = verifier_acces(st)
st.title("📚 IA AISSA broute, mange les livres et rumine")
st.caption("Donnez-lui une page web, un livre (PDF ou texte), ou laissez-la explorer Wikipédia seule sur ses lacunes. "
           "Elle mange le texte morceau par morceau, le rumine en concepts clés, garde ces concepts (jamais le texte "
           "complet), en tire des exercices pour son école et grandit.")

moteur = st.session_state.get("moteur_choisi", list(MOTEURS)[0])
config = MOTEURS[moteur]
cle_api = secret(config["secret"]) or st.session_state.get(f"cle_visite_{config['secret']}")
image, type_image = memoire().media("avatar")


def manger(source, texte, nb_bouchees):
    barre = st.progress(0.0, text="🐄 IA AISSA mange…")
    bilan = digerer(memoire(), config, client_moteur(moteur, cle_api), source, texte, utilisateur, nb_bouchees,
                    callback=lambda k, n, d: barre.progress(k / n, text=f"🧠 Rumination : bouchée {k}/{n}"))
    barre.empty()
    annoncer(bilan)


def annoncer(bilan):
    if bilan.get("erreur"):
        st.warning(f"{bilan['source']} : {bilan['erreur']}")
        return
    familles = sorted({d["famille"] for d in bilan["digestions"]})
    texte = (f"J'ai mangé « {bilan['source']} » en {bilan['bouchees']} bouchée(s) et j'en ai tiré "
             f"{bilan['concepts']} concept(s) ({', '.join(familles) or 'aucune famille'}). "
             f"{bilan['exercices']} exercice(s) sont partis à mon école.")
    confiance = sum(d["confiance"] for d in bilan["digestions"]) / max(1, len(bilan["digestions"]))
    st.iframe(avatar(texte, None, "fr-FR", image, type_image or "image/png", etat="hyper",
                     indicateur={"confiance": confiance, "details": f"{bilan['bouchees']} bouchée(s) digérée(s)"}),
              height=350)
    for d in bilan["digestions"]:
        with st.expander(f"🧬 {d['famille']} — {len(d['concepts'])} concept(s), digestion {d['confiance']:.0%}"):
            for c in d["concepts"]:
                st.markdown(f"- **{c['nom']}** : {c.get('explication', '')}")
            if d["analogie"]:
                st.caption(f"💡 Analogie avec le contrôle de gestion : {d['analogie']}")


if not cle_api:
    st.info("Pour ruminer, IA AISSA a besoin de son moteur de conversation : ajoutez une clé API dans les secrets, "
            "ou collez-la dans la page « 💬 Parler avec IA AISSA » (elle est gardée pour toute la visite).")
else:
    st.caption(f"Moteur : {moteur} · environ une rumination par bouchée, plus un appel pour les exercices.")
    lien, livre, seule = st.tabs(["🌐 Une page web", "📖 Un livre", "🌍 Explorer seule (Wikipédia)"])
    with lien:
        url = st.text_input("Lien de la page à manger", placeholder="https://…")
        if url and st.button("🐄 Brouter cette page"):
            try:
                source, texte = brouter_lien(url.strip())
                manger(source, texte, 3)
            except (ErreurBroutage, Exception) as e:
                st.error(f"Impossible de brouter cette page : {e}")
    with livre:
        fichier = st.file_uploader("Livre ou document", type=["pdf", "txt", "md", "html"])
        bouchees = st.slider("Bouchées (morceaux répartis du début à la fin du livre)", 2, 12, 6)
        if fichier is not None and st.button("📖 Manger ce livre"):
            try:
                source, texte = brouter_fichier(fichier.name, fichier.getvalue())
                manger(source, texte, bouchees)
            except (ErreurBroutage, Exception) as e:
                st.error(f"Impossible de manger ce livre : {e}")
    with seule:
        sujet = st.text_input("Un sujet précis (sinon IA AISSA choisit parmi ses lacunes)")
        lacunes = memoire().lacunes_ouvertes(5)
        if lacunes:
            st.caption("Ses lacunes du moment : " + " · ".join(l["question"] for l in lacunes))
        if st.button("🌍 Partir explorer"):
            with st.spinner("🌍 IA AISSA explore Wikipédia…"):
                if sujet.strip():
                    try:
                        source, texte = brouter_wikipedia(sujet.strip())
                        bilans = [digerer(memoire(), config, client_moteur(moteur, cle_api), source, texte,
                                          utilisateur, 3)]
                    except ErreurBroutage as e:
                        bilans = [{"source": sujet, "erreur": str(e)}]
                elif lacunes:
                    bilans = explorer_lacunes(memoire(), config, client_moteur(moteur, cle_api))
                else:
                    bilans = []
                    st.info("Aucune lacune en ce moment : donnez-lui un sujet.")
            for b in bilans:
                annoncer(b)

st.subheader("🔎 Interroger la bibliothèque")
question = st.text_input("Ce que vous cherchez dans ce qu'IA AISSA a lu")
if question:
    trouves = chercher(memoire(), question)
    for t in trouves:
        st.markdown(f"- **{t['concept']}** ({t['famille']}) : {t['explication']}  \n  _Source : {t['source']}_")
    if not trouves:
        st.caption("Rien de proche dans sa bibliothèque pour l'instant.")

st.subheader("🗂️ Ce qu'IA AISSA a digéré")
digestions = memoire().digestions(200)
if digestions:
    tableau = pd.DataFrame([{"Date": d["cree_le"], "Source": d["source"], "Famille": d["famille"],
                             "Concepts": len(json.loads(d["concepts"])), "Digestion": d["confiance"]}
                            for d in digestions])
    st.dataframe(tableau, hide_index=True, width="stretch", column_config={
        "Date": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
        "Digestion": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
else:
    st.caption("Sa bibliothèque est encore vide : donnez-lui à manger !")
st.caption("Les livres et pages sont résumés pour l'apprentissage d'IA AISSA ; seuls les concepts sont conservés.")
