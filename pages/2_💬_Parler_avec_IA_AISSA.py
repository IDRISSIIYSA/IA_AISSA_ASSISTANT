import anthropic
import openai
import streamlit as st

from ia_aissa.acces import verifier_acces
from ia_aissa.assistant import MOTEURS, NIVEAUX, client_moteur, converser_moteur, profil_conversation
from ia_aissa.corrections import corriger, reviser_tout
from ia_aissa.ecole import repondre
from ia_aissa.langues import LANGUES
from ia_aissa.memoire import historique_api
from ia_aissa.partage import memoire, secret
from ia_aissa.parole import charger_oreille, synthetiser, transcrire
from ia_aissa.voix import bouton_ecouter

st.set_page_config(page_title="Parler avec IA AISSA", page_icon="💬", layout="wide")
utilisateur = verifier_acces(st)
st.title("💬 Parler avec IA AISSA")
st.caption(f"Bonjour {utilisateur} ! Écrivez ou parlez (🎙️ dans la barre de message), en arabe, darija, français, "
           "anglais ou espagnol. IA AISSA vous répond par écrit, à voix haute, ou les deux.")



def ouvrir_conversation(conversation_id):
    lignes = memoire().messages_de(utilisateur, conversation_id) if conversation_id else []
    st.session_state["conversation_id"] = conversation_id
    st.session_state["affichage"] = [{"role": l["role"], "texte": l["texte"], "langue": "Français"} for l in lignes]
    st.session_state["messages_api"] = historique_api(lignes)
    st.session_state["moteur_historique"] = None


with st.sidebar:
    moteur = st.selectbox("🧠 Moteur de conversation", list(MOTEURS),
                          help="IA AISSA garde ses connaissances, ses outils et sa mémoire quel que soit le moteur.")
    config = MOTEURS[moteur]
    cle_api = secret(config["secret"]) or st.text_input(
        f"Clé API ({moteur.split(' (')[0]})", type="password", key=f"cle_{config['secret']}",
        help=f"Créez une clé sur {config['console']}. Elle reste dans votre session et n'est pas enregistrée.")
    mode = st.radio("Je veux mes réponses", ["✍️ Écrites", "🔊 Vocales", "✍️🔊 Écrites et vocales"], index=2)
    niveau = st.selectbox("Accompagnement", list(NIVEAUX),
                          help="Choisissez un niveau scolaire pour qu'IA AISSA devienne votre professeur.")
    voir_outils = st.toggle("Montrer le raisonnement (outils utilisés)", value=False)

    st.subheader("📚 Mes conversations")
    if not memoire().persistante:
        st.caption("⚠️ Mémoire temporaire : ajoutez le secret `MEMOIRE_URL` (base PostgreSQL) pour qu'IA AISSA "
                   "se souvienne même après un redémarrage.")
    if st.button("➕ Nouvelle conversation", width="stretch"):
        ouvrir_conversation(None)
        st.rerun()
    for conv in memoire().lister_conversations(utilisateur):
        actuelle = conv["id"] == st.session_state.get("conversation_id")
        if st.button(("▶ " if actuelle else "") + conv["titre"][:40], key=f"conv{conv['id']}", width="stretch",
                     type="primary" if actuelle else "secondary"):
            ouvrir_conversation(conv["id"])
            st.rerun()
    if st.session_state.get("conversation_id") and st.button("🗑️ Supprimer cette conversation"):
        memoire().supprimer_conversation(utilisateur, st.session_state["conversation_id"])
        ouvrir_conversation(None)
        st.rerun()

    with st.expander("🧠 Ce dont IA AISSA se souvient"):
        for souvenir in memoire().souvenirs_de(utilisateur):
            c1, c2 = st.columns([5, 1])
            c1.write(souvenir["fait"])
            if c2.button("✖", key=f"oubli{souvenir['id']}", help="Oublier"):
                memoire().oublier(utilisateur, souvenir["id"])
                st.rerun()
        nouveau = st.text_input("Lui apprendre quelque chose", placeholder="ex. : je travaille dans le textile à Fès")
        if nouveau and st.button("Retenir"):
            memoire().memoriser(utilisateur, nouveau)
            st.rerun()

if not cle_api:
    st.info(f"Ajoutez une clé API pour {moteur} dans la barre latérale (ou dans les *Secrets* de Streamlit Cloud "
            f"sous le nom `{config['secret']}`) pour parler avec IA AISSA.")
    st.stop()

ecrit, vocal = "Écrites" in mode, "Vocales" in mode or "vocales" in mode
if "affichage" not in st.session_state:
    ouvrir_conversation(None)


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
    if st.session_state.get("moteur_historique") not in (None, moteur):
        # changement de moteur en cours de conversation : on repart de l'historique écrit, compris par tous
        st.session_state["messages_api"] = historique_api(
            [{"role": m["role"], "texte": m["texte"].removeprefix("🎙️ ")} for m in st.session_state["affichage"][:-1]])
    st.session_state["moteur_historique"] = moteur
    st.session_state["messages_api"].append({"role": "user", "content": question})
    journal = []
    with st.spinner("IA AISSA réfléchit…"):
        try:
            souvenirs = [x["fait"] for x in memoire().souvenirs_de(utilisateur)]
            texte = converser_moteur(moteur, client_moteur(moteur, cle_api), st.session_state["messages_api"],
                                     journal=journal,
                                     profil=profil_conversation(utilisateur, niveau, vocal and not ecrit, souvenirs),
                                     memoriser=lambda fait: memoire().memoriser(utilisateur, fait),
                                     corriger=lambda cle, q, rep: corriger(memoire(), utilisateur, cle, q, rep))
        except (anthropic.AuthenticationError, openai.AuthenticationError):
            st.session_state["messages_api"].pop()
            st.error("Clé API invalide.")
            st.stop()
        except (anthropic.APIError, openai.APIError) as e:
            st.session_state["messages_api"].pop()
            st.error(f"Erreur de l'API : {e}")
            st.stop()

    if not st.session_state.get("conversation_id"):
        st.session_state["conversation_id"] = memoire().nouvelle_conversation(utilisateur, question)
    memoire().ajouter_message(utilisateur, st.session_state["conversation_id"], "user", question)
    memoire().ajouter_message(utilisateur, st.session_state["conversation_id"], "assistant", texte)

    if any(o["outil"] == "corriger_ia_aissa" for o in journal):
        with st.spinner("📚 IA AISSA révise à partir de sa correction…"):
            bilans = reviser_tout(memoire())
        for b in bilans:
            st.toast(("✅ Révision adoptée" if b["adoptee"] else "↩️ Révision refusée (régression)")
                     + f" : {b['matiere']} — corrections retenues {b['corrections_apres']:.0%}")

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
