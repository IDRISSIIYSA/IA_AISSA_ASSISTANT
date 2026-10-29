import time

import anthropic
import openai
import streamlit as st

from ia_aissa.acces import verifier_acces
from ia_aissa.autonomie import SEUIL_ETUDE, etudier_seule, noter_si_lacune
from ia_aissa.avatar import avatar
from ia_aissa.assistant import (MOTEURS, NIVEAUX, client_moteur, converser_moteur, meta_conscience,
                                profil_conversation)
from ia_aissa.corrections import corriger, reviser_tout
from ia_aissa.ecole import repondre
from ia_aissa.langues import LANGUES
from ia_aissa.memoire import historique_api
from ia_aissa.partage import memoire, secret
from ia_aissa.parole import charger_oreille, synthetiser, transcrire
from ia_aissa.reconnaissance import moment_de_la_journee
from ia_aissa.visage import SALUTATIONS
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
    # Les valeurs des champs sont effacées quand on change de page : on les garde dans la session de la visite.
    moteurs = list(MOTEURS)
    moteur = st.selectbox("🧠 Moteur de conversation", moteurs,
                          index=moteurs.index(st.session_state.get("moteur_choisi", moteurs[0])),
                          help="IA AISSA garde ses connaissances, ses outils et sa mémoire quel que soit le moteur.")
    st.session_state["moteur_choisi"] = moteur
    config = MOTEURS[moteur]
    cle_visite = f"cle_visite_{config['secret']}"
    cle_api = secret(config["secret"])
    if cle_api:
        st.caption("🔑 Clé API enregistrée dans les secrets de l'application.")
    elif st.session_state.get(cle_visite):
        cle_api = st.session_state[cle_visite]
        st.caption("🔑 Clé gardée pour toute la visite (elle s'efface si vous fermez ou rafraîchissez la page). "
                   "Pour ne plus jamais la saisir, ajoutez-la dans les Secrets de Streamlit Cloud.")
        if st.button("Changer de clé"):
            del st.session_state[cle_visite]
            st.rerun()
    else:
        saisie = st.text_input(f"Clé API ({moteur.split(' (')[0]})", type="password",
                               help=f"Créez une clé sur {config['console']}. Elle est gardée le temps de la visite, "
                                    "jamais enregistrée sur le serveur.")
        if saisie:
            st.session_state[cle_visite] = cle_api = saisie.strip()
            st.rerun()
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
    with st.chat_message(message["role"], avatar="👽" if message["role"] == "assistant" else None):
        if message["role"] == "user" or ecrit or not message.get("audio"):
            st.markdown(message["texte"])
        if message["role"] != "assistant":
            return
        if voir_outils and message.get("outils"):
            with st.expander(f"🔧 {len(message['outils'])} outil(s) utilisé(s)"):
                for o in message["outils"]:
                    st.markdown(f"**{o['outil']}** `{o['entree']}`")
                    st.code(o["resultat"], language="json")
        if message.get("meta"):
            st.caption(f"🧠 Méta-conscience : confiance {message['meta']['confiance']:.0%} · {message['meta']['details']}")
        if message.get("audio") and nouveau:
            image, type_image = memoire().media("avatar")
            st.iframe(avatar(message["texte"], message["audio"], LANGUES[message["langue"]]["voix"], image,
                             type_image or "image/png", bulle=not ecrit, etat=etat_alien,
                             indicateur=message.get("meta")), height=360 if not ecrit else 330)
        elif message.get("audio"):
            st.audio(message["audio"], format="audio/mp3")
        elif vocal:
            st.iframe(bouton_ecouter(message["texte"], LANGUES[message["langue"]]["voix"],
                                     f"🔊 Écouter ({message['langue']})"), height=50)


etat_alien = "hyper" if NIVEAUX.get(niveau) == "invention" else "normal"
if not st.session_state["affichage"]:
    # L'alien accueille la personne, se souvient de la dernière conversation et de ce qu'il sait d'elle
    accueil = [SALUTATIONS["Français"][moment_de_la_journee()].format(nom=utilisateur)]
    precedentes = memoire().lister_conversations(utilisateur, limite=1)
    if precedentes:
        accueil.append(f"La dernière fois, nous parlions de « {precedentes[0]['titre']} ».")
    souvenirs_accueil = [x["fait"] for x in memoire().souvenirs_de(utilisateur)][-2:]
    if souvenirs_accueil:
        accueil.append("Je me souviens que " + " Et aussi : ".join(souvenirs_accueil))
    accueil.append("Comment puis-je t'aider aujourd'hui ?")
    image, type_image = memoire().media("avatar")
    st.iframe(avatar(" ".join(accueil), None, "fr-FR", image, type_image or "image/png", etat=etat_alien,
                     lecture_auto=vocal and not st.session_state.get("alien_a_salue")), height=320)
    st.session_state["alien_a_salue"] = True

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
    noter_si_lacune(memoire(), question)       # IA AISSA repère seule ce qu'elle ne sait pas encore
    journal = []
    debut = time.time()
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

    if len(memoire().lacunes_ouvertes(SEUIL_ETUDE)) >= SEUIL_ETUDE:
        try:
            with st.spinner("🧠 IA AISSA étudie seule ce qu'elle ne savait pas…"):
                etude = etudier_seule(memoire(), config, client_moteur(moteur, cle_api))
            st.toast(f"🧠 Étude autonome : {etude['etudiees']} question(s) étudiée(s), "
                     f"{etude['apprises']} nouvelle(s) connaissance(s).")
        except Exception:
            pass          # l'étude autonome reprendra à la prochaine occasion

    langue = repondre("langues", texte[:300])[0]["reponse"]
    reponse = {"role": "assistant", "texte": texte, "outils": journal, "langue": langue,
               "meta": meta_conscience(journal, time.time() - debut)}
    if vocal:
        try:
            with st.spinner("IA AISSA prépare sa voix…"):
                reponse["audio"] = synthetiser(texte, langue)
        except Exception:
            pass  # sans accès au service vocal, le bouton de lecture du navigateur prend le relais
    st.session_state["affichage"].append(reponse)
    afficher(reponse, nouveau=True)
