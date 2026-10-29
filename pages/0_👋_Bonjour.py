import streamlit as st

from ia_aissa.acces import utilisateurs_autorises, verifier_acces
from ia_aissa.avatar import avatar
from ia_aissa.langues import LANGUES
from ia_aissa.parole import synthetiser
from ia_aissa.partage import memoire
from ia_aissa.reconnaissance import Yeux, moment_de_la_journee, qui_est_ce
from ia_aissa.visage import SALUTATIONS

st.set_page_config(page_title="Bonjour IA AISSA", page_icon="👋", layout="wide")
utilisateur = verifier_acces(st)
mem = memoire()
st.title("👋 IA AISSA vous reconnaît")


@st.cache_resource(show_spinner="IA AISSA ouvre les yeux (premier chargement)…")
def yeux():
    return Yeux()


def visage_ia():
    return mem.media("avatar")


def parler(texte, langue, hauteur=330):
    try:
        audio = synthetiser(texte, langue)
    except Exception:
        audio = None              # sans service vocal, la voix du navigateur prend le relais
    image, type_image = visage_ia()
    st.iframe(avatar(texte, audio, LANGUES[langue]["voix"], image, type_image or "image/png"), height=hauteur)


c1, c2 = st.columns(2)
comptes = utilisateurs_autorises(st)
if comptes:
    prenom = utilisateur
    c1.text_input("Vous êtes", value=prenom, disabled=True)
else:
    prenom = c1.text_input("Votre prénom", value=st.session_state.get("prenom", utilisateur)).strip() or utilisateur
    st.session_state["prenom"] = prenom
langues = list(LANGUES)
langue = c2.selectbox("Langue de salutation", langues,
                      index=langues.index(st.session_state.get("langue_salut", "Darija")))
st.session_state["langue_salut"] = langue

if not mem.persistante:
    st.warning("⚠️ La mémoire d'IA AISSA est temporaire : les visages mémorisés sont effacés à chaque redémarrage "
               "de l'application. Ajoutez le secret `MEMOIRE_URL` (base PostgreSQL gratuite Neon ou Supabase) "
               "pour qu'elle vous reconnaisse pour toujours.")

photo = st.camera_input("Regardez la caméra et prenez une photo : IA AISSA vous regarde")
if photo is None:
    parler("", langue, hauteur=300)
    st.caption("IA AISSA reconnaît les visages qu'elle a mémorisés et salue chaque personne selon l'heure du Maroc.")
else:
    empreinte = yeux().empreinte(photo.getvalue())
    connus = mem.visages_connus()
    if empreinte is None:
        st.warning("🤔 Je ne vois pas de visage. Approchez-vous, face à la lumière, et reprenez la photo.")
    else:
        qui, score = qui_est_ce(empreinte, connus)
        if qui:
            parler(SALUTATIONS[langue][moment_de_la_journee()].format(nom=qui), langue)
            st.success(f"Je vous reconnais, {qui} (ressemblance {score:.0%}).")
            if qui == prenom and st.button("➕ Ajouter cette photo à mon visage (me reconnaître encore mieux)"):
                mem.ajouter_visage(prenom, empreinte)
                st.toast("Photo ajoutée : je vous reconnaîtrai encore mieux.")
        else:
            parler("Je ne vous connais pas encore. Si vous êtes " + prenom +
                   ", mémorisez votre visage et je vous saluerai à chaque visite.", "Français")
            if st.button(f"🧬 Mémoriser ce visage comme {prenom}", type="primary"):
                mem.ajouter_visage(prenom, empreinte)
                st.success(f"C'est noté, {prenom} ! Reprenez une photo : je vais vous reconnaître. "
                           "Ajoutez 2 ou 3 photos (lumières différentes) pour une reconnaissance plus sûre.")
    st.caption(f"Visages mémorisés : {', '.join(f'{n} ({len(e)} photo(s))' for n, e in connus.items()) or 'aucun'}.")

with st.expander("⚙️ Mon visage et le visage d'IA AISSA"):
    if st.button(f"🗑️ Oublier le visage de {prenom}"):
        mem.oublier_visage(prenom)
        st.rerun()
    st.markdown("**Le visage d'IA AISSA** : un petit alien dessiné, ou votre propre image (ex. un rendu réaliste).")
    image = st.file_uploader("Choisir une image pour IA AISSA", type=["png", "jpg", "jpeg", "webp"])
    if image is not None and st.button("Utiliser cette image"):
        mem.sauver_media("avatar", image.getvalue(), image.type or "image/png")
        st.rerun()
    if visage_ia()[0] is not None and st.button("Revenir à l'alien dessiné"):
        mem.supprimer_media("avatar")
        st.rerun()

st.info("🔐 Seule l'empreinte du visage (128 nombres) est gardée, jamais la photo. Une photo pouvant tromper une "
        "caméra, c'est le mot de passe qui protège réellement l'accès.")
