import streamlit as st

from ia_aissa.acces import verifier_acces

from ia_aissa.ecole import repondre
from ia_aissa.langues import LANGUES
from ia_aissa.voix import atelier_prononciation, bouton_ecouter

st.set_page_config(page_title="Langues d'IA AISSA", page_icon="🗣️", layout="wide")
utilisateur = verifier_acces(st)
st.title("🗣️ Langues et prononciation")
st.caption("IA AISSA étudie l'arabe, la darija, le français, l'anglais et l'espagnol. Elle reconnaît la "
           "langue d'un texte grâce à ce qu'elle a appris seule, et parle avec les voix de votre navigateur "
           "(Chrome ou Edge recommandés).")

st.subheader("👂 Quelle langue ?")
texte = st.text_input("Écrivez une phrase dans n'importe laquelle des cinq langues",
                      placeholder="ex. : wach kayn chi mochkil f la facture ?")
if texte:
    resultats = repondre("langues", texte)
    meilleure = resultats[0]
    st.write(f"IA AISSA pense que c'est : **{meilleure['reponse']}** (confiance {meilleure['confiance']:.0%})")
    st.iframe(bouton_ecouter(texte, LANGUES[meilleure["reponse"]]["voix"],
                                   "🔊 IA AISSA lit votre phrase"), height=50)

st.subheader("🎙️ Atelier de prononciation")
langue = st.radio("Langue", list(LANGUES), horizontal=True)
phrase = st.selectbox("Phrase à travailler", LANGUES[langue]["phrases"])
st.iframe(atelier_prononciation(phrase, LANGUES[langue]["voix"]), height=190)
st.caption("IA AISSA prononce la phrase, vous la répétez : le navigateur transcrit ce que vous dites, "
           "puis IA AISSA note votre prononciation sur 100 et souligne les mots à retravailler. "
           "La darija utilise une voix arabe marocaine si votre appareil en possède une, sinon une voix arabe.")
