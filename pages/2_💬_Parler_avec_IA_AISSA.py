import os

import anthropic
import streamlit as st

from ia_aissa.acces import verifier_acces
from ia_aissa.assistant import NIVEAUX, client_anthropic, converser, profil_conversation
from ia_aissa.ecole import repondre
from ia_aissa.langues import LANGUES
from ia_aissa.parole import charger_oreille, synthetiser, transcrire
from ia_aissa.voix import bouton_ecouter

st.set_page_config(page_title="Parler avec IA AISSA", page_icon="💬", layout="wide")
utilisateur = verifier_acces(st)
st.title("💬 Parler avec IA AISSA")
st.caption(f"Bonjour {utilisateur} ! Écrivez ou parlez (🎙️ dans la barre de message), en arabe, darija, français, "
           "anglais ou espagnol. IA AISSA vous répond par écrit, à voix haute, ou les deux.")

try:
    cle_secrets = st.secrets.get("ANTHROPIC_API_KEY")
except Exception:
    cle_secrets = None
with st.sidebar:
    cle_api = cle_secrets or os.environ.get("ANTHROPIC_API_KEY") or st.text_input(
        "Clé API Anthropic", type="password", help="Créez une clé sur console.anthropic.com. "
        "Elle reste dans votre session et n'est pas enregistrée.")
    mode = st.radio("Je veux mes réponses", ["✍️ Écrites", "🔊 Vocales", "✍️🔊 Écrites et vocales"], index=2)
    niveau = st.selectbox("Accompagnement", list(NIVEAUX),
                          help="Choisissez un niveau scolaire pour qu'IA AISSA devienne votre professeur.")
    voir_outils = st.toggle("Montrer le raisonnement (outils utilisés)", value=False)
    if st.button("🗑️ Nouvelle conversation"):
        for cle in ("messages_api", "affichage"):
            st.session_state.pop(cle, None)
        st.rerun()

if not cle_api:
    st.info("Ajoutez une clé API Anthropic dans la barre latérale (ou dans les *Secrets* de Streamlit Cloud "
            "sous le nom `ANTHROPIC_API_KEY`) pour parler avec IA AISSA.")
    st.stop()

ecrit, vocal = "Écrites" in mode, "Vocales" in mode or "vocales" in mode
st.session_state.setdefault("messages_api", [])
st.session_state.setdefault("affichage", [])


@st.cache_resource(show_spinner="IA AISSA apprend à écouter (premier chargement)…")
def oreille():
    return charger_oreille()


def afficher(message, nouveau=False):
    with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else None):
        if message["role"] == "user" or ecrit or not message.get("audio"):
            st.markdown(message["texte"])
        if message["role"] != "assistant":
            return
        if voir_outils and message.get("outils"):
            with st.expander(f"🔧 {len(message['outils'])} outil(s) utilisé(s)"):
                for o in message["outils"]:
                    st.markdown(f"**{o['outil']}** `{o['entree']}`")
                    st.code(o["resultat"], language="json")
        if message.get("audio"):
            st.audio(message["audio"], format="audio/mp3", autoplay=nouveau)
        elif vocal:
            st.iframe(bouton_ecouter(message["texte"], LANGUES[message["langue"]]["voix"],
                                     f"🔊 Écouter ({message['langue']})"), height=50)


for message in st.session_state["affichage"]:
    afficher(message)

saisie = st.chat_input("Écrivez ou cliquez sur 🎙️ pour parler…", accept_audio=True, submit_mode="disable")
if saisie:
    question = saisie if isinstance(saisie, str) else (saisie.text or "")
    audio = None if isinstance(saisie, str) else getattr(saisie, "audio", None)
    if audio is not None:
        with st.spinner("IA AISSA vous écoute…"):
            dit, _ = transcrire(oreille(), audio)
        question = f"{question} {dit}".strip()
        if not question:
            st.warning("Je n'ai rien entendu, pouvez-vous répéter ?")
            st.stop()
        question_affichee = f"🎙️ {question}"
    else:
        question_affichee = question

    st.session_state["affichage"].append({"role": "user", "texte": question_affichee})
    afficher(st.session_state["affichage"][-1])
    st.session_state["messages_api"].append({"role": "user", "content": question})
    journal = []
    with st.spinner("IA AISSA réfléchit…"):
        try:
            texte = converser(client_anthropic(cle_api), st.session_state["messages_api"], journal=journal,
                              profil=profil_conversation(utilisateur, niveau, vocal and not ecrit))
        except anthropic.AuthenticationError:
            st.session_state["messages_api"].pop()
            st.error("Clé API invalide.")
            st.stop()
        except anthropic.APIError as e:
            st.session_state["messages_api"].pop()
            st.error(f"Erreur de l'API : {e}")
            st.stop()

    langue = repondre("langues", texte[:300])[0]["reponse"]
    reponse = {"role": "assistant", "texte": texte, "outils": journal, "langue": langue}
    if vocal:
        try:
            with st.spinner("IA AISSA prépare sa voix…"):
                reponse["audio"] = synthetiser(texte, langue)
        except Exception:
            pass  # sans accès au service vocal, le bouton de lecture du navigateur prend le relais
    st.session_state["affichage"].append(reponse)
    afficher(reponse, nouveau=True)
