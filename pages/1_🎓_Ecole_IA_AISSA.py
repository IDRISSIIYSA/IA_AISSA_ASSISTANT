import numpy as np
import pandas as pd
import streamlit as st

from ia_aissa.acces import verifier_acces

from ia_aissa.ecole import (MATIERES, PAR_CLE, SEUIL_CONFIANCE, charger, entrainer, repondre,
                            repondre_automatiquement, sauvegarder)

st.set_page_config(page_title="École d'IA AISSA", page_icon="🎓", layout="wide")
utilisateur = verifier_acces(st)
st.title("🎓 L'école d'IA AISSA")
st.caption("IA AISSA est née vide. Dans chaque matière, elle reçoit des exercices, répond, gagne +1 ou perd 1, "
           "et retient ses expériences dans sa mémoire. Personne ne lui donne les règles : elle les découvre.")

# Une seule question, sans choisir de matière
st.subheader("💬 Posez n'importe quelle question")
question_libre = st.text_input("IA AISSA devine seule la matière, puis répond",
                               placeholder="ex. : qui a construit la Koutoubia ? · dernier entré premier sorti · agadir")
if question_libre:
    propositions = repondre_automatiquement(question_libre)
    meilleure = propositions[0]
    if meilleure["confiance"] >= SEUIL_CONFIANCE:
        st.success(f"**{meilleure['reponse']}**  \n"
                   f"Matière reconnue : {meilleure['domaine']} — {meilleure['matiere']} · confiance {meilleure['confiance']:.0%}")
    else:
        st.warning(f"🤔 Je ne suis pas sûre (ma meilleure idée : « {meilleure['reponse']} », "
                   f"{meilleure['matiere']}, {meilleure['confiance']:.0%}). Posez plutôt la question dans "
                   "« 💬 Parler avec IA AISSA » : l'assistante comprend toutes les formulations.")
    with st.expander("Mes autres pistes"):
        for p in propositions[1:]:
            st.write(f"- {p['matiere']} : {p['reponse']} ({p['confiance']:.0%})")

# Bulletin de notes
lignes = []
for m in MATIERES:
    _, historique = charger(m.cle)
    lignes.append({"Domaine": m.domaine, "Matière": m.nom,
                   "À la naissance": historique[0]["precision"] if historique else np.nan,
                   "Aujourd'hui": historique[-1]["precision"] if historique else np.nan,
                   "Réponses possibles": len(m.actions)})
bulletin = pd.DataFrame(lignes)
c1, c2, c3 = st.columns(3)
AUJOURDHUI = "Aujourd'hui"
c1.metric("Matières étudiées", f"{bulletin[AUJOURDHUI].notna().sum()} / {len(MATIERES)}")
c2.metric("Moyenne à la naissance", f"{bulletin['À la naissance'].mean():.0%}")
c3.metric("Moyenne aujourd'hui", f"{bulletin[AUJOURDHUI].mean():.0%}")
st.subheader("📒 Bulletin de notes")
st.dataframe(bulletin, hide_index=True, width="stretch", column_config={
    "À la naissance": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
    "Aujourd'hui": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
})
st.caption("Note = taux de bonnes réponses à un examen de 400 exercices jamais vus pendant l'entraînement.")

# Une matière en détail
st.subheader("🔎 Une matière en détail")
cle = st.selectbox("Matière", [m.cle for m in MATIERES],
                   format_func=lambda c: f"{PAR_CLE[c].domaine} — {PAR_CLE[c].nom}")
m = PAR_CLE[cle]
st.write(f"**Règle à découvrir :** {m.note}  \n**Réponses possibles :** {', '.join(m.actions)}")

cerveau, historique = charger(cle)
if st.session_state.get("reentraine", {}).get(cle):
    cerveau, historique = st.session_state["reentraine"][cle]
if historique:
    st.line_chart(pd.DataFrame(historique).set_index("pas")["precision"] * 100, y_label="Bonnes réponses (%)",
                  x_label="Exercices effectués")

if st.button("🧬 Faire renaître IA AISSA dans cette matière et la regarder apprendre"):
    barre = st.progress(0.0)
    cerveau, historique = entrainer(m, callback=lambda t, total, p: barre.progress(
        t / total, text=f"Exercice {t}/{total} — {p:.0%} de bonnes réponses"))
    sauvegarder(m, cerveau, historique)
    st.session_state.setdefault("reentraine", {})[cle] = (cerveau, historique)
    st.rerun()

st.subheader("✍️ Interroger IA AISSA")
if cerveau is None:
    st.info("IA AISSA n'a pas encore étudié cette matière.")
elif m.texte:
    question = st.text_input("Votre question", placeholder="ex. : paiement du loyer du dépôt de Tanger")
    if question:
        for r in repondre(cle, question, cerveau):
            st.write(f"- **{r['reponse']}** — confiance {r['confiance']:.0%}")
        st.caption("Une confiance faible signifie qu'IA AISSA n'a jamais vu de formulation proche : "
                   "posez la question à l'assistante pour une réponse vérifiée.")
if cerveau is not None and st.button("🎲 Exercice surprise"):
    x, y, enonce = m.generer(np.random.default_rng())
    r = repondre(cle, enonce if m.texte else x, cerveau)[0]
    st.write(f"**Énoncé :** {enonce}")
    st.write(f"**IA AISSA répond :** {r['reponse']} (confiance {r['confiance']:.0%})")
    (st.success if r["reponse"] == m.actions[y] else st.error)(f"Bonne réponse : {m.actions[y]}")
