import streamlit as st

from ia_aissa.acces import verifier_acces
from ia_aissa.langues import LANGUES
from ia_aissa.visage import accueil

st.set_page_config(page_title="Bonjour IA AISSA", page_icon="👋", layout="wide")
utilisateur = verifier_acces(st)
st.title("👋 IA AISSA vous reconnaît")
st.caption("Chaque personne autorisée mémorise son visage une fois : ensuite, dès qu'IA AISSA la voit, elle la "
           "reconnaît et la salue par son prénom, à voix haute, selon le moment de la journée (matin, après-midi, "
           "soir ou nuit) et dans sa langue. Un visage inconnu n'est pas salué.")

c1, c2 = st.columns(2)
nom = c1.text_input("Votre prénom", value=st.session_state.get("prenom", utilisateur))
langue = c2.selectbox("Langue de salutation", list(LANGUES), index=list(LANGUES).index("Darija"))
st.session_state["prenom"] = nom
st.iframe(accueil(nom or "", langue, LANGUES[langue]["voix"]), height=300)

st.info("🔐 **Confidentialité** : la reconnaissance se fait dans votre navigateur. L'empreinte de votre visage "
        "reste sur cet appareil et n'est jamais envoyée au serveur.  \n"
        "⚠️ Une photo peut tromper une caméra : pour qu'IA AISSA ne parle **réellement** qu'avec vous, "
        "l'application est protégée par un mot de passe (secret `MOT_DE_PASSE`) et peut être rendue privée "
        "sur Streamlit Cloud.")
