import numpy as np
import pandas as pd
import streamlit as st

from ia_aissa.acces import verifier_acces
from ia_aissa.assistant import MOTEURS, client_moteur
from ia_aissa.autonomie import etudier_seule, noter_si_lacune
from ia_aissa.corrections import ORIENTATION, corriger, reviser_tout
from ia_aissa.ecole import (MATIERES, PAR_CLE, SEUIL_CONFIANCE, charger, entrainer, repondre,
                            repondre_automatiquement, sauvegarder)
from ia_aissa.partage import memoire, secret

st.set_page_config(page_title="École d'IA AISSA", page_icon="🎓", layout="wide")
utilisateur = verifier_acces(st)
memoire()      # branche la mémoire durable : les cerveaux révisés y sont lus et écrits
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
        noter_si_lacune(memoire(), question_libre, propositions)
        st.warning(f"🤔 Je ne suis pas sûre (ma meilleure idée : « {meilleure['reponse']} », "
                   f"{meilleure['matiere']}, {meilleure['confiance']:.0%}). Posez plutôt la question dans "
                   "« 💬 Parler avec IA AISSA » : l'assistante comprend toutes les formulations.")
    with st.expander("Mes autres pistes"):
        for p in propositions[1:]:
            st.write(f"- {p['matiere']} : {p['reponse']} ({p['confiance']:.0%})")

    def apprendre(cle, reponse):
        corriger(memoire(), utilisateur, cle, question_libre, reponse, source="utilisateur")
        with st.spinner("📚 IA AISSA révise…"):
            for b in reviser_tout(memoire()):
                (st.success if b["adoptee"] else st.warning)(
                    f"{PAR_CLE[b['matiere']].nom} : révision {'adoptée' if b['adoptee'] else 'refusée (elle régressait)'}"
                    f" — corrections retenues {b['corrections_apres']:.0%}, examen {b['examen_avant']:.1%} → "
                    f"{b['examen_apres']:.1%}")

    j, c = st.columns([1, 3])
    if j.button("✅ C'est juste"):
        apprendre(meilleure["cle"], meilleure["reponse"])
    with c.popover("❌ Corriger IA AISSA"):
        textuelles = [m.cle for m in MATIERES if m.texte and m.cle not in (ORIENTATION, "langues")]
        cle_juste = st.selectbox("La bonne matière", textuelles, index=textuelles.index(meilleure["cle"])
                                 if meilleure["cle"] in textuelles else 0, format_func=lambda k: PAR_CLE[k].nom)
        reponse_juste = st.selectbox("La bonne réponse", PAR_CLE[cle_juste].actions)
        if st.button("Apprendre cette correction"):
            apprendre(cle_juste, reponse_juste)

# Croissance et autonomie
st.subheader("🚀 IA AISSA grandit seule")
lacunes = memoire().lacunes_ouvertes(100)
croissance = pd.DataFrame(memoire().croissance())
a1, a2, a3 = st.columns(3)
a1.metric("Lacunes repérées à étudier", len(lacunes))
if not croissance.empty:
    croissance["cree_le"] = pd.to_datetime(croissance["cree_le"], utc=True)
    maintenant = pd.Timestamp.now(tz="UTC")
    recentes = (croissance["cree_le"] > maintenant - pd.Timedelta(days=7)).sum()
    avant = ((croissance["cree_le"] <= maintenant - pd.Timedelta(days=7))
             & (croissance["cree_le"] > maintenant - pd.Timedelta(days=14))).sum()
    a2.metric("Connaissances acquises (7 derniers jours)", int(recentes), delta=int(recentes - avant))
    a3.metric("Dont par étude autonome", int((croissance["source"] == "étude autonome").sum()))
    courbe = croissance.set_index("cree_le").assign(n=1)["n"].cumsum().rename("Connaissances acquises")
    st.area_chart(courbe, y_label="Connaissances acquises (cumul)")
moteur_etude = st.session_state.get("moteur_choisi", list(MOTEURS)[0])
config_etude = MOTEURS[moteur_etude]
cle_etude = secret(config_etude["secret"]) or st.session_state.get(f"cle_visite_{config_etude['secret']}")
if lacunes and cle_etude and st.button(f"🧠 Étudier seule maintenant ({len(lacunes)} lacune(s), avec {moteur_etude})"):
    with st.spinner("🧠 IA AISSA étudie seule…"):
        etude = etudier_seule(memoire(), config_etude, client_moteur(moteur_etude, cle_etude))
    st.success(f"{etude['etudiees']} question(s) étudiée(s) : {etude['apprises']} nouvelle(s) connaissance(s), "
               f"{etude['hors_programme']} hors programme.")
elif lacunes and not cle_etude:
    st.caption("Pour étudier seule, IA AISSA a besoin d'une clé API (secrets, ou page 💬 Parler avec IA AISSA).")
st.caption("IA AISSA note chaque question à laquelle elle ne sait pas répondre avec assurance. Dès que trois "
           "lacunes s'accumulent pendant une conversation, elle les étudie d'elle-même puis révise : plus on lui "
           "parle, plus elle apprend vite.")

# Apprentissage par les corrections
st.subheader("📚 Ce qu'IA AISSA apprend de ses corrections")
toutes = memoire().corrections_de()
en_attente = [x for x in toutes if not x["apprise"]]
k1, k2 = st.columns(2)
k1.metric("Corrections reçues", len(toutes))
k2.metric("En attente de révision", len(en_attente))
if en_attente and st.button("🌙 Réviser maintenant"):
    with st.spinner("📚 IA AISSA révise…"):
        reviser_tout(memoire())
    st.rerun()
revisions = memoire().revisions()
if revisions:
    st.dataframe(pd.DataFrame(revisions)[["cree_le", "matiere", "nb_corrections", "examen_avant", "examen_apres",
                                          "corrections_avant", "corrections_apres", "adoptee"]],
                 hide_index=True, width="stretch", column_config={
                     "cree_le": st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm"),
                     "examen_avant": st.column_config.NumberColumn("Examen avant", format="percent"),
                     "examen_apres": st.column_config.NumberColumn("Examen après", format="percent"),
                     "corrections_avant": st.column_config.NumberColumn("Corrections avant", format="percent"),
                     "corrections_apres": st.column_config.NumberColumn("Corrections après", format="percent"),
                     "adoptee": st.column_config.CheckboxColumn("Adoptée")})
st.caption("Chaque correction (de l'assistante ou de vous) devient un exercice. IA AISSA révise à partir de son "
           "cerveau actuel, puis repasse son examen habituel : si elle a régressé, elle garde l'ancien cerveau.")

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
    courbe = pd.DataFrame([h for h in historique if isinstance(h["pas"], int)])
    st.line_chart(courbe.set_index("pas")["precision"] * 100, y_label="Bonnes réponses (%)",
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
