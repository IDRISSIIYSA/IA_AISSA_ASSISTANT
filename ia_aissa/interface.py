"""
L'espace unique d'IA AISSA (« Seul Espace ») : l'alien dans son portail cosmique et une seule ligne de conversation.

Tout passe par cette ligne : texte, voix (🎙️) et fichiers (📎). IA AISSA choisit seule son rôle
(programmeur, prof/savant, contrôleur de gestion, inventeur, lecteur, compagnon), répond par écrit et à voix haute,
calcule, exécute du code (avec Claude, dans le bac à sable d'Anthropic), lit, invente, et apprend de chaque échange
(lacunes, corrections, étude autonome, lectures). Les réglages tiennent dans un seul panneau ⚙️.
"""

import json
import random
import re
import time

from urllib.parse import urlparse

import anthropic
import openai
import pandas as pd
import streamlit as st

from . import coffre
from .acces import verifier_acces
from .assistant import MOTEURS, NIVEAUX, client_moteur, converser_moteur, meta_conscience, profil_conversation
from .autonomie import SEUIL_ETUDE, etudier_seule, noter_si_lacune
from .avatar import avatar
from .bibliotheque import ErreurBroutage, brouter_fichier, brouter_lien, chercher, digerer, visible_par
from .corrections import corriger, reviser_tout
from .croissance import afficher as afficher_croissance
from .croissance import serie as serie_croissance
from .ecole import MATIERES, charger, repondre
from .espace import EXTENSIONS_DONNEES, EXTENSIONS_LECTURE, ROLES, analyser_controle, detecter_role, intention, \
    reponse_locale, urls
from .invention import annonce_darija, debattre, evoluer
from .langues import LANGUES, PHRASES_PRO_DARIJA
from .memoire import historique_api
from .partage import broutage_autonome, etat_memoire, memoire, secret
from .parole import charger_oreille, synthetiser, transcrire
from .reconnaissance import Yeux, moment_de_la_journee, qui_est_ce
from .visage import SALUTATIONS
from .autodidacte import apprendre_de_soi
from .voix import atelier_prononciation, atelier_suivi, noter_prononciation, suivi_prononciation

STYLE = """<style>
  @import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@400;500;600&family=Orbitron:wght@500;700&display=swap');
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
  .block-container { padding-top: 1rem; max-width: 860px; }
  html, body, [data-testid="stAppViewContainer"], .stMarkdown, textarea, input, button { font-family: 'Exo 2', sans-serif; }

  /* ---------- Thème clair : ciel d'aube, voiles pastel et poussière d'étoiles discrète ---------- */
  [data-testid="stAppViewContainer"], [data-testid="stApp"], .stApp {
    background:
      radial-gradient(1100px 620px at 12% -10%, rgba(167,139,250,.22), transparent 62%),
      radial-gradient(900px 520px at 95% 4%, rgba(56,189,248,.20), transparent 60%),
      radial-gradient(800px 480px at 50% 115%, rgba(244,114,182,.12), transparent 62%),
      #f7f9ff !important; color: #0f172a; }
  [data-testid="stAppViewContainer"]::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .7;
    background-image:
      radial-gradient(1.6px 1.6px at 8% 14%, #93c5fd, transparent), radial-gradient(1.4px 1.4px at 27% 9%, #c4b5fd, transparent),
      radial-gradient(1.6px 1.6px at 46% 24%, #93c5fd, transparent), radial-gradient(1.4px 1.4px at 68% 13%, #c4b5fd, transparent),
      radial-gradient(1.6px 1.6px at 86% 31%, #93c5fd, transparent), radial-gradient(1.4px 1.4px at 93% 72%, #f9a8d4, transparent),
      radial-gradient(1.4px 1.4px at 12% 86%, #c4b5fd, transparent), radial-gradient(1.6px 1.6px at 58% 84%, #93c5fd, transparent);
    background-size: 100% 100%; animation: cosmos-scintille 6s ease-in-out infinite; }
  @keyframes cosmos-scintille { 50% { opacity: .3; } }
  [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div { background: transparent !important; }
  [data-testid="stBottomBlockContainer"] { background: linear-gradient(to top, rgba(247,249,255,.97), rgba(247,249,255,0)) !important; }

  /* ---------- Messages en verre dépoli clair ---------- */
  [data-testid="stChatMessage"] { background: rgba(255,255,255,.78) !important; backdrop-filter: blur(12px);
    border: 1px solid rgba(56,189,248,.28); border-radius: 18px; padding: 14px 16px;
    box-shadow: 0 6px 22px rgba(30,64,175,.08), inset 0 1px 0 rgba(255,255,255,.9); }
  [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]),
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    border-color: rgba(167,139,250,.35); background: rgba(245,243,255,.85) !important; }
  .role { display:inline-block; font-family:'Orbitron', sans-serif; font-size:11.5px; letter-spacing:.06em;
          padding:4px 12px; border-radius:999px; color:#0369a1; text-transform: uppercase;
          border:1px solid rgba(14,165,233,.5); background: rgba(14,165,233,.08); box-shadow: 0 2px 10px rgba(14,165,233,.15); }
  [data-testid="stPopover"] button { border-radius: 999px !important; border: 1px solid rgba(14,165,233,.45) !important;
    background: rgba(255,255,255,.85) !important; box-shadow: 0 2px 10px rgba(14,165,233,.15); }
  [data-testid="stCaptionContainer"] { color: #475569 !important; }

  /* ---------- Barre de conversation : boutons en 3D, grands et lisibles ---------- */
  [data-testid="stChatInput"] { border-radius: 28px !important; background: rgba(255,255,255,.95) !important;
                                border: 1px solid rgba(14,165,233,.5) !important;
                                box-shadow: 0 0 0 1px rgba(14,165,233,.10), 0 8px 26px rgba(30,64,175,.12) !important;
                                transition: box-shadow .3s, border-color .3s; }
  [data-testid="stChatInput"]:focus-within { box-shadow: 0 0 0 3px rgba(14,165,233,.28), 0 8px 30px rgba(14,165,233,.22) !important; }
  [data-testid="stChatInputTextArea"] { color: #0f172a !important; }
  [data-testid="stChatInputTextArea"] { font-size: 16.5px !important; }
  [data-testid="stChatInputMicButton"], [data-testid="stChatInputSubmitButton"],
  [data-testid="stChatInputApproveButton"], [data-testid="stChatInputCancelButton"],
  [data-testid="stChatInputFileUploadButton"] button {
    width: 48px !important; height: 48px !important; min-width: 48px !important; border-radius: 50% !important;
    border: none !important; color: #fff !important; margin: 0 3px !important; position: relative;
    box-shadow: 0 6px 0 rgba(0,0,0,.18), 0 10px 18px rgba(15,23,42,.28),
                inset 0 2px 3px rgba(255,255,255,.55), inset 0 -4px 6px rgba(0,0,0,.22) !important;
    transition: transform .12s, box-shadow .12s, filter .2s;
  }
  [data-testid="stChatInputMicButton"] svg, [data-testid="stChatInputSubmitButton"] svg,
  [data-testid="stChatInputApproveButton"] svg, [data-testid="stChatInputCancelButton"] svg,
  [data-testid="stChatInputFileUploadButton"] button svg { width: 24px !important; height: 24px !important;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,.35)); }
  /* le micro : bleu cosmique bombé, qui respire pour attirer le regard */
  [data-testid="stChatInputMicButton"] {
    background: radial-gradient(circle at 32% 28%, #bae6fd 0%, #38bdf8 28%, #2563eb 62%, #1e3a8a 100%) !important;
    animation: micro-respire 2.8s ease-in-out infinite; }
  @keyframes micro-respire { 50% { box-shadow: 0 6px 0 rgba(0,0,0,.18), 0 0 0 7px rgba(56,189,248,.22),
    0 10px 22px rgba(37,99,235,.45), inset 0 2px 3px rgba(255,255,255,.55), inset 0 -4px 6px rgba(0,0,0,.22); } }
  /* l'envoi : vert émeraude bombé, terne tant qu'il n'y a rien à envoyer */
  [data-testid="stChatInputSubmitButton"] {
    background: radial-gradient(circle at 32% 28%, #bbf7d0 0%, #34d399 30%, #059669 65%, #064e3b 100%) !important; }
  [data-testid="stChatInputSubmitButton"]:disabled { filter: grayscale(.85) opacity(.5); }
  [data-testid="stChatInputFileUploadButton"] button {
    background: radial-gradient(circle at 32% 28%, #f5f5f4 0%, #d6d3d1 40%, #a8a29e 75%, #57534e 100%) !important; }
  [data-testid="stChatInputMicButton"]:hover, [data-testid="stChatInputSubmitButton"]:not(:disabled):hover,
  [data-testid="stChatInputApproveButton"]:hover, [data-testid="stChatInputFileUploadButton"] button:hover {
    transform: translateY(-2px) scale(1.06); }
  [data-testid="stChatInputMicButton"]:active, [data-testid="stChatInputSubmitButton"]:active,
  [data-testid="stChatInputApproveButton"]:active, [data-testid="stChatInputCancelButton"]:active {
    transform: translateY(4px); box-shadow: 0 2px 0 rgba(0,0,0,.18), inset 0 2px 6px rgba(0,0,0,.3) !important; }

  /* ---------- Enregistrement en cours : impossible de le manquer ---------- */
  [data-testid="stChatInput"]:has([data-testid="stChatInputApproveButton"]) {
    border: 2px solid #ef4444 !important; animation: rec-halo 1.2s ease-in-out infinite; }
  @keyframes rec-halo { 50% { box-shadow: 0 0 0 8px rgba(239,68,68,.22), 0 6px 24px rgba(239,68,68,.35); } }
  [data-testid="stChatInput"]:has([data-testid="stChatInputApproveButton"])::before {
    content: "● Enregistrement… parle, puis appuie sur ✅ pour envoyer (✖ pour annuler)";
    position: absolute; left: 16px; top: -34px; z-index: 5; pointer-events: none; white-space: nowrap;
    padding: 4px 12px; border-radius: 999px; background: #dc2626; color: #fff;
    font-size: 13.5px; font-weight: 600; box-shadow: 0 4px 12px rgba(220,38,38,.35);
    animation: rec-clignote 1s steps(1) infinite; }
  @keyframes rec-clignote { 50% { opacity: .55; } }
  [data-testid="stChatInput"]:has([data-testid="stChatInputApproveButton"]) { overflow: visible !important; }
  [data-testid="stChatInputApproveButton"] {
    width: 56px !important; height: 56px !important; min-width: 56px !important;
    background: radial-gradient(circle at 32% 28%, #bbf7d0 0%, #22c55e 35%, #15803d 70%, #14532d 100%) !important;
    animation: envoi-pulse 1.2s ease-in-out infinite; }
  @keyframes envoi-pulse { 50% { box-shadow: 0 6px 0 rgba(0,0,0,.18), 0 0 0 9px rgba(34,197,94,.28),
    inset 0 2px 3px rgba(255,255,255,.55), inset 0 -4px 6px rgba(0,0,0,.22); } }
  [data-testid="stChatInputCancelButton"] {
    background: radial-gradient(circle at 32% 28%, #fecaca 0%, #f87171 35%, #b91c1c 75%, #7f1d1d 100%) !important; }

  /* ---------- Icônes redessinées, nettes et pleines (le dessin d'origine est masqué) ---------- */
  [data-testid="stChatInputMicButton"] svg, [data-testid="stChatInputSubmitButton"] svg, [data-testid="stChatInputApproveButton"] svg, [data-testid="stChatInputCancelButton"] svg, [data-testid="stChatInputFileUploadButton"] button svg { opacity: 0 !important; }
  [data-testid="stChatInputMicButton"]::after { content: ""; position: absolute; inset: 0; margin: auto; width: 23px; height: 23px;
    background: #fff; -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Crect x=%279%27 y=%272.5%27 width=%276%27 height=%2712%27 rx=%273%27 fill=%27black%27/%3E%3Cpath d=%27M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21.5M8.5 21.5h7%27/%3E%3C/svg%3E") center/contain no-repeat; mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Crect x=%279%27 y=%272.5%27 width=%276%27 height=%2712%27 rx=%273%27 fill=%27black%27/%3E%3Cpath d=%27M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21.5M8.5 21.5h7%27/%3E%3C/svg%3E") center/contain no-repeat;
    filter: drop-shadow(0 1px 1.5px rgba(0,0,0,.45)); pointer-events: none; }
  [data-testid="stChatInputSubmitButton"]::after { content: ""; position: absolute; inset: 0; margin: auto; width: 23px; height: 23px;
    background: #fff; -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M4 12 20 4l-4.5 16-3.5-6.5L4 12z%27 fill=%27black%27/%3E%3Cpath d=%27M12 13.5 20 4%27/%3E%3C/svg%3E") center/contain no-repeat; mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M4 12 20 4l-4.5 16-3.5-6.5L4 12z%27 fill=%27black%27/%3E%3Cpath d=%27M12 13.5 20 4%27/%3E%3C/svg%3E") center/contain no-repeat;
    filter: drop-shadow(0 1px 1.5px rgba(0,0,0,.45)); pointer-events: none; }
  [data-testid="stChatInputApproveButton"]::after { content: ""; position: absolute; inset: 0; margin: auto; width: 26px; height: 26px;
    background: #fff; -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M4.5 12.5 9.5 17.5 19.5 6.5%27 stroke-width=%273%27/%3E%3C/svg%3E") center/contain no-repeat; mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M4.5 12.5 9.5 17.5 19.5 6.5%27 stroke-width=%273%27/%3E%3C/svg%3E") center/contain no-repeat;
    filter: drop-shadow(0 1px 1.5px rgba(0,0,0,.45)); pointer-events: none; }
  [data-testid="stChatInputCancelButton"]::after { content: ""; position: absolute; inset: 0; margin: auto; width: 23px; height: 23px;
    background: #fff; -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M6 6 18 18M18 6 6 18%27 stroke-width=%273%27/%3E%3C/svg%3E") center/contain no-repeat; mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M6 6 18 18M18 6 6 18%27 stroke-width=%273%27/%3E%3C/svg%3E") center/contain no-repeat;
    filter: drop-shadow(0 1px 1.5px rgba(0,0,0,.45)); pointer-events: none; }
  [data-testid="stChatInputFileUploadButton"] button::after { content: ""; position: absolute; inset: 0; margin: auto; width: 23px; height: 23px;
    background: #fff; -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M20 11.5 12.2 19.3a5 5 0 0 1-7.1-7.1l8.1-8.1a3.4 3.4 0 0 1 4.8 4.8l-8 8a1.7 1.7 0 0 1-2.4-2.4l7.3-7.3%27/%3E%3C/svg%3E") center/contain no-repeat; mask: url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27black%27 stroke-width=%272.2%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3E%3Cpath d=%27M20 11.5 12.2 19.3a5 5 0 0 1-7.1-7.1l8.1-8.1a3.4 3.4 0 0 1 4.8 4.8l-8 8a1.7 1.7 0 0 1-2.4-2.4l7.3-7.3%27/%3E%3C/svg%3E") center/contain no-repeat;
    filter: drop-shadow(0 1px 1.5px rgba(0,0,0,.45)); pointer-events: none; }
  [data-testid="stChatInputMicButton"]::before, [data-testid="stChatInputSubmitButton"]::before, [data-testid="stChatInputCancelButton"]::before, [data-testid="stChatInputFileUploadButton"] button::before { content: ""; position: absolute; left: 18%; top: 7%; width: 64%; height: 38%;
    border-radius: 50%; background: linear-gradient(180deg, rgba(255,255,255,.55), rgba(255,255,255,0));
    pointer-events: none; }
  [data-testid="stChatInputFileUploadButton"] button::after { background: #1f2937; filter: none; }
  [data-testid="stChatInputMicButton"]:focus-visible, [data-testid="stChatInputSubmitButton"]:focus-visible { outline: 3px solid #fde68a !important; outline-offset: 2px; }

  .astuce { font-size: 13px; color: #475569; text-align: center; margin-top: -4px; }
  @media (max-width: 640px) {
    /* chiffres clés deux par ligne au lieu d'une longue colonne */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) {
      flex-direction: row !important; flex-wrap: wrap !important; gap: .4rem .8rem !important; }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) > [data-testid="stColumn"] {
      flex: 1 1 calc(50% - .8rem) !important; min-width: calc(50% - .8rem) !important; width: auto !important; }
    [data-testid="stMetricValue"] { font-size: 1.45rem !important; }
    h1 { font-size: 1.7rem !important; }
    [data-testid="stIFrame"] { height: 470px !important; }
    [data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]) { height: 470px !important; max-height: 470px !important; min-height: 0 !important; }
    .block-container { padding-left: 12px; padding-right: 12px; }
    [data-testid="stChatInputTextArea"] { font-size: 15px !important; }
    [data-testid="stChatInputTextArea"]::placeholder { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    [data-testid="stChatInput"]:has([data-testid="stChatInputApproveButton"])::before {
      content: "● Enregistrement… ✅ envoyer · ✖ annuler"; } }
  @media (prefers-reduced-motion: reduce) { [data-testid="stChatInputMicButton"],
    [data-testid="stChatInputApproveButton"], [data-testid="stChatInput"] { animation: none !important; } }
</style>"""


@st.cache_resource(show_spinner="IA AISSA apprend à écouter (premier chargement)…")
def oreille():
    return charger_oreille()


@st.cache_resource(show_spinner="IA AISSA ouvre les yeux (premier chargement)…")
def yeux():
    return Yeux()


def _dire(texte, langue):
    try:
        return synthetiser(texte, langue)
    except Exception:
        return None                # sans service vocal, la voix du navigateur prend le relais


def ouvrir_conversation(utilisateur, conversation_id):
    lignes = memoire().messages_de(utilisateur, conversation_id) if conversation_id else []
    st.session_state["conversation_id"] = conversation_id
    st.session_state["affichage"] = [{"role": l["role"], "texte": l["texte"], "langue": "Français"} for l in lignes]
    st.session_state["messages_api"] = historique_api(lignes)
    st.session_state["moteur_historique"] = None


# ==========================================
# La clé API gardée sur l'appareil (cookie du navigateur), pour survivre au rechargement de la page
# ==========================================
def nom_cookie(nom_secret):
    return f"ia_aissa_{nom_secret.lower()}"


def lire_cle_cookie(nom):
    """Valeur gardée sur cet appareil (stockage local du navigateur, via le coffre)."""
    return coffre.lire(nom)


def ecrire_cookie(nom, valeur):
    """Garde (ou efface si valeur est None) une valeur sur cet appareil ; appliqué au prochain affichage."""
    coffre.ecrire(nom, valeur)


# ==========================================
# L'espace administrateur
# ==========================================
COOKIE_ADMIN = "ia_aissa_admin"


def est_admin():
    from . import admin
    if st.session_state.get("admin"):
        return True
    authentifie = st.session_state.get("authentifie")          # le compte d'Aissa est le compte administrateur
    if authentifie and authentifie == admin.proprietaire(memoire()):
        st.session_state["admin"] = True
        return True
    if st.session_state.get("cookie_oublie") != COOKIE_ADMIN and admin.jeton_valide(memoire(), lire_cle_cookie(COOKIE_ADMIN)):
        st.session_state["admin"] = True
    return bool(st.session_state.get("admin"))


def admin_connexion():
    """Création du compte administrateur, ou connexion. Renvoie True si la personne est administrateur."""
    from . import admin
    mem = memoire()
    if est_admin():
        return True
    if not mem.persistante:
        st.warning("⚠️ Mémoire temporaire : sans `MEMOIRE_URL` dans les Secrets de Streamlit, tout (compte administrateur "
                   "compris) est effacé à chaque redémarrage du serveur.")
    if not admin.admin_existe(mem):
        code_attendu = secret("ADMIN_CODE")
        if not code_attendu:
            st.error("🔒 Création de l'administrateur bloquée : ajoutez d'abord `ADMIN_CODE = \"un code secret\"` dans les "
                     "Secrets de Streamlit Cloud (Settings → Secrets). Sans ce code, le premier visiteur venu pourrait "
                     "se déclarer administrateur.")
            return False
        st.caption("Aucun administrateur : créez votre compte, il sera le compte administrateur de l'application.")
        code = st.text_input("Code de création (ADMIN_CODE des Secrets)", type="password", key="adm_code")
        prenom_admin = st.text_input("Votre prénom", value=st.session_state.get("utilisateur") or "Aissa",
                                     key="adm_prenom")
        mdp = st.text_input("Nouveau mot de passe admin (8 caractères au moins)", type="password", key="adm_new")
        mdp2 = st.text_input("Confirmer", type="password", key="adm_new2")
        if st.button("Créer l'administrateur") and mdp:
            import hmac
            if not hmac.compare_digest(code, str(code_attendu)):
                st.error("Code de création incorrect.")
            elif mdp != mdp2:
                st.error("Les deux mots de passe diffèrent.")
            else:
                try:
                    ecrire_cookie(COOKIE_ADMIN, admin.creer_admin(mem, mdp, prenom_admin))
                    prenom_admin = prenom_admin.strip()
                    coffre.ecrire("ia_aissa_session", admin.ouvrir_session(mem, prenom_admin))
                    st.session_state.update(admin=True, utilisateur=prenom_admin, authentifie=prenom_admin)
                    st.rerun()
                except (ValueError, PermissionError) as e:
                    st.error(str(e))
    else:
        mdp = st.text_input("Mot de passe administrateur", type="password", key="adm_mdp")
        if mdp:
            jeton = admin.connexion_admin(mem, mdp)
            if jeton:
                proprio = admin.proprietaire(mem)
                if not proprio:                              # ce compte administrateur devient le vôtre
                    admin.lier_proprietaire(mem, st.session_state.get("utilisateur"), mdp)
                    proprio = admin.proprietaire(mem)
                ecrire_cookie(COOKIE_ADMIN, jeton)
                st.session_state.update(admin=True, utilisateur=proprio, authentifie=proprio)
                st.session_state.pop("cookie_oublie", None)
                st.rerun()
            st.error("Mot de passe incorrect.")
    return False


def admin_cles():
    from . import admin
    mem = memoire()
    if not mem.persistante:
        st.warning("Mémoire temporaire : ces réglages seront effacés au prochain redémarrage (ajoutez MEMOIRE_URL).")
    st.caption("Clés API de l'application : valables sur tous les appareils, pour l'espace visiteurs et le broutage.")
    for nom, libelle in (("ANTHROPIC_API_KEY", "Claude"), ("OPENAI_API_KEY", "GPT-4o"), ("MINIMAX_API_KEY", "MiniMax")):
        actuelle = admin.valeur_app(mem, nom)
        c1, c2 = st.columns([3, 1])
        nouvelle = c1.text_input(f"{libelle} ({admin.masquer(actuelle) if actuelle else 'aucune'})", type="password",
                                 key=f"adm_{nom}")
        if c2.button("Enregistrer", key=f"adm_ok_{nom}") and nouvelle:
            admin.definir_valeur_app(mem, nom, nouvelle)
            st.rerun()
        if actuelle and c2.button("Retirer", key=f"adm_del_{nom}"):
            admin.definir_valeur_app(mem, nom, None)
            st.rerun()


def admin_broutage():
    from . import admin
    mem = memoire()
    actif = (admin.valeur_app(mem, "BROUTAGE_AUTONOME") or "oui") != "non"
    if st.toggle("Broutage autonome (lecture seule sur le web, pratique, crises synthétiques)", value=actif,
                 key="adm_brout") != actif:
        admin.definir_valeur_app(mem, "BROUTAGE_AUTONOME", "oui" if not actif else "non")
        st.rerun()
    par_jour = int(admin.valeur_app(mem, "BROUTAGE_PAR_JOUR") or 24)
    nouveau = st.number_input("Repas par jour", 1, 48, par_jour, key="adm_repas")
    if nouveau != par_jour:
        admin.definir_valeur_app(mem, "BROUTAGE_PAR_JOUR", nouveau)


def admin_utilisateurs():
    from . import admin
    mem = memoire()
    st.caption("Comptes (prénom + mot de passe) : nécessaires seulement si l'espace visiteurs est réservé.")
    for prenom in admin.utilisateurs(mem):
        c1, c2 = st.columns([3, 1])
        c1.write(prenom)
        if prenom != admin.proprietaire(mem) and c2.button("Retirer", key=f"adm_u_{prenom}"):
            admin.retirer_utilisateur(mem, prenom)
            st.rerun()
    c1, c2, c3 = st.columns([2, 2, 1])
    prenom = c1.text_input("Prénom", key="adm_u_nom")
    mdp_u = c2.text_input("Mot de passe", type="password", key="adm_u_mdp")
    if c3.button("Ajouter") and prenom and mdp_u:
        try:
            admin.ajouter_utilisateur(mem, prenom, mdp_u)
            st.rerun()
        except ValueError as e:
            st.error(str(e))


def admin_deconnexion():
    from . import admin
    mem = memoire()
    admin.deconnexion(mem)
    admin.fermer_session(mem, coffre.lire("ia_aissa_session"))
    st.session_state["cookie_oublie"] = COOKIE_ADMIN
    ecrire_cookie(COOKIE_ADMIN, None)
    coffre.ecrire("ia_aissa_session", None)
    for nom in ("admin", "utilisateur", "authentifie"):
        st.session_state.pop(nom, None)
    st.rerun()


# ==========================================
# Les réglages : visiteurs et administrateur
# ==========================================
PAGE_ADMIN = None                   # la page d'administration (st.Page), fixée par application()
QUOTA_VISITEUR = 30                 # messages par visiteur et par jour avec le grand moteur (réglable par l'admin)


def moteur_pour_visiteur(utilisateur):
    """Visiteurs : le grand moteur de l'application (clé de l'admin) dans la limite du quota quotidien, sinon
    la pensée propre d'IA AISSA. Renvoie (moteur, config, clé API ou None, messages restants)."""
    from datetime import date
    from . import admin
    mem = memoire()
    if (admin.valeur_app(mem, "VISITEURS_MOTEUR") or "oui") == "non":
        return list(MOTEURS)[0], MOTEURS[list(MOTEURS)[0]], None, 0
    quota = int(admin.valeur_app(mem, "QUOTA_VISITEUR") or QUOTA_VISITEUR)
    utilises = int(mem.reglage(f"quota:{date.today().isoformat()}:{utilisateur}") or 0)
    for moteur, config in MOTEURS.items():
        if secret(config["secret"]):
            return moteur, config, (secret(config["secret"]) if utilises < quota else None), max(0, quota - utilises)
    return list(MOTEURS)[0], MOTEURS[list(MOTEURS)[0]], None, 0


def compter_message_visiteur(utilisateur):
    from datetime import date
    mem = memoire()
    cle = f"quota:{date.today().isoformat()}:{utilisateur}"
    mem.definir_reglage(cle, str(int(mem.reglage(cle) or 0) + 1))


def reglages_visiteur(utilisateur):
    """Le panneau des visiteurs : comment IA AISSA répond, et leurs conversations. Rien d'autre."""
    mem = memoire()
    moteur, config, cle_api, restants = moteur_pour_visiteur(utilisateur)
    with st.popover("⚙️ Réglages", width="content"):
        modes = ["✍️🔊 Écrites et vocales", "✍️ Écrites", "🔊 Vocales"]
        mode = st.radio("Réponses", modes, index=modes.index(st.session_state.get("mode_reponse", modes[0])),
                        horizontal=True)
        st.session_state["mode_reponse"] = mode
        niveaux = list(NIVEAUX)
        niveau = st.selectbox("Accompagnement (niveau scolaire, invention…)", niveaux,
                              index=niveaux.index(st.session_state.get("niveau", niveaux[0])))
        st.session_state["niveau"] = niveau
        st.caption(f"🧠 Grand moteur : {restants} message(s) restant(s) aujourd'hui" if cle_api else
                   "🧠 Je réponds avec mon propre cerveau.")
        st.markdown("**📚 Mes conversations**")
        if st.button("➕ Nouvelle conversation", width="stretch"):
            ouvrir_conversation(utilisateur, None)
            st.rerun()
        for conv in mem.lister_conversations(utilisateur, limite=8):
            if st.button(conv["titre"][:45], key=f"conv{conv['id']}", width="stretch"):
                ouvrir_conversation(utilisateur, conv["id"])
                st.rerun()
        st.caption("🔒 Tes conversations et tes documents ne sont visibles que par toi.")
        if PAGE_ADMIN is not None:
            st.page_link(PAGE_ADMIN, label="🛡️ Administration")
    return {"moteur": moteur, "config": config, "cle_api": cle_api, "niveau": niveau, "voir_outils": False,
            "ecrit": "Écrites" in mode, "vocal": "Vocales" in mode or "vocales" in mode, "admin": False}


def reglages(utilisateur):
    mem = memoire()
    with st.popover("⚙️ Réglages", width="content"):
        moteurs = list(MOTEURS)
        moteur = st.selectbox("🧠 Moteur", moteurs, index=moteurs.index(st.session_state.get("moteur_choisi", moteurs[0])))
        st.session_state["moteur_choisi"] = moteur
        config = MOTEURS[moteur]
        cle_visite = f"cle_visite_{config['secret']}"
        cookie = nom_cookie(config["secret"])
        compte = st.session_state.get("authentifie")       # personne connectée : sa clé suit son compte
        cle_compte = f"cle:{compte}:{config['secret']}" if compte else None
        gardee_compte = mem.reglage(cle_compte) if cle_compte else None
        gardee_appareil = lire_cle_cookie(cookie)
        cle_api = secret(config["secret"]) or st.session_state.get(cle_visite) or gardee_compte or gardee_appareil
        if cle_compte and cle_api and not secret(config["secret"]) and not gardee_compte:
            mem.definir_reglage(cle_compte, cle_api)       # une clé connue de l'appareil rejoint le compte
            gardee_compte = cle_api
        if secret(config["secret"]):
            st.caption("🔑 Clé de l'application (secrets ou administration).")
        elif not cle_api:
            saisie = st.text_input(f"Clé API ({moteur.split(' (')[0]})", type="password",
                                   help=f"Créez une clé sur {config['console']}.")
            souvenir = st.checkbox("🔐 Ne jamais oublier ma clé", value=True,
                                   help="Gardée avec votre compte (tous vos appareils, même après une nouvelle "
                                        "session) et sur cet appareil. N'utilisez pas cette option sur un appareil partagé.")
            if saisie:
                st.session_state[cle_visite] = cle_api = saisie.strip()
                if souvenir:
                    if cle_compte:
                        mem.definir_reglage(cle_compte, cle_api)
                    ecrire_cookie(cookie, cle_api)
                    st.rerun()                  # retenue tout de suite
        else:
            st.session_state[cle_visite] = cle_api
            st.caption("🔑 Clé gardée avec votre compte." if gardee_compte else
                       "🔑 Clé gardée sur cet appareil." if gardee_appareil else "🔑 Clé gardée pour cette visite.")
            if gardee_compte and not mem.persistante:
                st.caption("⚠️ Mémoire temporaire : ajoutez MEMOIRE_URL dans les secrets pour qu'elle survive aux redémarrages.")
            if st.button("🗑️ Oublier ma clé"):
                st.session_state.pop(cle_visite, None)
                st.session_state["cookie_oublie"] = cookie
                if cle_compte:
                    mem.supprimer_reglage(cle_compte)
                ecrire_cookie(cookie, None)
                st.rerun()
        modes = ["✍️🔊 Écrites et vocales", "✍️ Écrites", "🔊 Vocales"]
        mode = st.radio("Réponses", modes, index=modes.index(st.session_state.get("mode_reponse", modes[0])),
                        horizontal=True)
        st.session_state["mode_reponse"] = mode
        niveaux = list(NIVEAUX)
        niveau = st.selectbox("Accompagnement (niveau scolaire, invention…)", niveaux,
                              index=niveaux.index(st.session_state.get("niveau", niveaux[0])))
        st.session_state["niveau"] = niveau
        voir_outils = st.toggle("Montrer le raisonnement (outils)", value=st.session_state.get("voir_outils", False))
        st.session_state["voir_outils"] = voir_outils
        etat_memoire(st)

        st.markdown("**📚 Conversations**")
        if st.button("➕ Nouvelle conversation", width="stretch"):
            ouvrir_conversation(utilisateur, None)
            st.rerun()
        for conv in mem.lister_conversations(utilisateur, limite=12):
            if st.button(conv["titre"][:45], key=f"conv{conv['id']}", width="stretch"):
                ouvrir_conversation(utilisateur, conv["id"])
                st.rerun()

        st.markdown("**🧠 Ce dont je me souviens**")
        for s in mem.souvenirs_de(utilisateur):
            c1, c2 = st.columns([6, 1])
            c1.caption(s["fait"])
            if c2.button("✖", key=f"oubli{s['id']}"):
                mem.oublier(utilisateur, s["id"])
                st.rerun()

        st.markdown("**📷 Me reconnaître**")
        photo = st.camera_input("Montre ton visage", label_visibility="collapsed")
        if photo is not None and st.session_state.get("photo_vue") != photo.file_id:
            st.session_state["photo_vue"] = photo.file_id
            empreinte = yeux().empreinte(photo.getvalue())
            if empreinte is None:
                st.warning("Je ne vois pas de visage.")
            else:
                qui, score = qui_est_ce(empreinte, mem.visages_connus())
                if qui:
                    texte = SALUTATIONS["Darija"][moment_de_la_journee()].format(nom=qui)
                    st.session_state["parole"] = {"texte": texte, "audio": _dire(texte, "Darija"), "voix": "ar-MA",
                                                  "nouveau": True}
                else:
                    mem.ajouter_visage(utilisateur, empreinte)
                    st.success(f"Visage mémorisé : je te reconnaîtrai, {utilisateur}.")
        image = st.file_uploader("🖼️ Mon visage d'alien (image)", type=["png", "jpg", "jpeg", "webp"])
        if image is not None and st.button("Utiliser cette image"):
            mem.sauver_media("avatar", image.getvalue(), image.type or "image/png")
            st.rerun()
    return {"moteur": moteur, "config": config, "cle_api": cle_api, "niveau": niveau, "voir_outils": voir_outils,
            "ecrit": "Écrites" in mode, "vocal": "Vocales" in mode or "vocales" in mode, "admin": True}


# ==========================================
# Les éléments affichés dans la conversation
# ==========================================
REPLIABLES = ("graphique", "tableau", "liste")


def afficher_element(e, cle):
    """Les graphiques, tableaux et listes se replient : la conversation reste compacte, surtout sur téléphone."""
    t = e["type"]
    if t in REPLIABLES and e.get("titre"):
        with st.expander(e["titre"], expanded=t == "graphique"):
            afficher_element({k: v for k, v in e.items() if k != "titre"}, cle)
        return
    if e.get("titre") and t not in ("telechargement",):
        st.markdown(f"**{e['titre']}**")
    if t == "metriques":
        for col, (libelle, valeur) in zip(st.columns(len(e["valeurs"])), e["valeurs"]):
            col.metric(libelle, valeur)
    elif t == "graphique":
        st.line_chart(e["donnees"])
    elif t == "tableau":
        st.dataframe(e["donnees"], hide_index=True, width="stretch")
    elif t == "liste":
        st.markdown("\n".join(f"- {l}" for l in e["lignes"]) or "_(rien)_")
    elif t == "telechargement":
        st.download_button(e["libelle"], e["donnees"], e["nom"], key=f"dl{cle}")
    elif t == "croissance":
        afficher_croissance(st, memoire())
    elif t == "bulletin":
        lignes = []
        for m in MATIERES:
            _, h = charger(m.cle)
            notes = [x["precision"] for x in h or [] if isinstance(x.get("pas"), int)]
            if notes:
                lignes.append({"Domaine": m.domaine, "Matière": m.nom, "Naissance": notes[0], "Aujourd'hui": notes[-1]})
        st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch", column_config={
            "Naissance": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
            "Aujourd'hui": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
    elif t == "atelier" and e.get("suivi"):
        utilisateur = st.session_state.get("utilisateur", "Aissa")
        essai = atelier_suivi(st, e["phrase"], LANGUES[e["langue"]]["voix"], e.get("sens", ""), cle=f"atelier{cle}")
        if essai and essai.get("quand"):
            noter_prononciation(memoire(), utilisateur, e["langue"], essai)
        essais = [x for x in suivi_prononciation(memoire(), utilisateur) if x["langue"] == e["langue"]]
        if essais:
            scores = [x["score"] for x in essais]
            recents, avant = scores[-5:], scores[-10:-5]
            delta = f"{sum(recents) / len(recents) - sum(avant) / len(avant):+.0f}" if avant else None
            st.metric(f"Ma prononciation en {e['langue']} (moyenne des 5 derniers essais)",
                      f"{sum(recents) / len(recents):.0f} / 100", delta=delta)
            if len(scores) > 1:
                st.line_chart(pd.DataFrame({"Score": scores}, index=pd.RangeIndex(1, len(scores) + 1, name="Essai")),
                              y_label="Score / 100")
    elif t == "atelier":
        st.iframe(atelier_prononciation(e["phrase"], LANGUES[e["langue"]]["voix"]), height=190)


def afficher_message(m, i, voir_outils):
    with st.chat_message(m["role"], avatar="👽" if m["role"] == "assistant" else None):
        if m.get("role_ia"):
            st.markdown(f'<span class="role">{ROLES[m["role_ia"]][0]}</span>', unsafe_allow_html=True)
        st.markdown(m["texte"])
        for k, e in enumerate(m.get("elements", [])):
            afficher_element(e, f"{i}_{k}")
        codes = [o for o in m.get("outils", []) if o["outil"] == "exécution de code"]
        for o in codes:
            with st.expander("💻 Code exécuté dans le bac à sable"):
                commande = o["entree"].get("command") or o["entree"].get("code") or json.dumps(o["entree"])
                st.code(commande)
                st.code(o["resultat"] or "(en cours)", language="text")
        autres = [o for o in m.get("outils", []) if o["outil"] != "exécution de code"]
        if voir_outils and autres:
            with st.expander(f"🔧 {len(autres)} outil(s) utilisé(s)"):
                for o in autres:
                    st.markdown(f"**{o['outil']}** `{o['entree']}`")
                    st.code(o["resultat"], language="json")
        if m.get("meta"):
            st.caption(f"🧠 Méta-conscience : confiance {m['meta']['confiance']:.0%} · {m['meta']['details']}")


# ==========================================
# Le traitement d'une demande : IA AISSA choisit son rôle et agit
# ==========================================
def converser_avec_moteur(r, utilisateur, question, role, journal):
    mem = memoire()
    if st.session_state.get("moteur_historique") not in (None, r["moteur"]):
        st.session_state["messages_api"] = historique_api(
            [{"role": m["role"], "texte": m["texte"]} for m in st.session_state["affichage"][:-1]])
    st.session_state["moteur_historique"] = r["moteur"]
    st.session_state["messages_api"].append({"role": "user", "content": question})
    profil = profil_conversation(utilisateur, r["niveau"], r["vocal"] and not r["ecrit"],
                                 [s["fait"] for s in mem.souvenirs_de(utilisateur)])
    profil += "\n" + ROLES[role][1]
    try:
        return converser_moteur(r["moteur"], client_moteur(r["moteur"], r["cle_api"]), st.session_state["messages_api"],
                                journal=journal, profil=profil,
                                memoriser=lambda fait: mem.memoriser(utilisateur, fait),
                                corriger=lambda cle, q, rep: corriger(mem, utilisateur, cle, q, rep),
                                bibliotheque=lambda q: chercher(mem, q, utilisateur=utilisateur),
                                execution_code=role == "programmeur" and r["config"]["type"] == "anthropic")
    except (anthropic.AuthenticationError, openai.AuthenticationError):
        st.session_state["messages_api"].pop()
        return "🔑 Ma clé API est refusée : vérifie-la dans ⚙️ Réglages."
    except (anthropic.APIError, openai.APIError) as e:
        st.session_state["messages_api"].pop()
        return f"Je n'arrive pas à joindre mon grand moteur ({e}). Réessaie dans un instant."


def traiter(r, utilisateur, texte, fichiers):
    """Renvoie (texte de la réponse, éléments à afficher, journal des outils, rôle, état du portail)."""
    mem = memoire()
    noms = [f.name for f in fichiers]
    role = detecter_role(texte, noms)
    if r["niveau"] and NIVEAUX.get(r["niveau"]) == "invention" and role == "compagnon":
        role = "inventeur"
    elements, journal = [], []
    client = client_moteur(r["moteur"], r["cle_api"]) if r["cle_api"] else None
    if client and not r.get("admin"):
        compter_message_visiteur(utilisateur)           # quota quotidien du grand moteur pour les visiteurs

    from .ecoute import SECURITE, ecoute_locale, en_detresse
    if en_detresse(texte):                              # la sécurité d'abord, avant toute autre réponse
        suite = converser_avec_moteur(r, utilisateur, texte, "psy", journal) if client else ""
        return SECURITE + (f"\n\n{suite}" if suite else ""), [], journal, "psy", "normal"
    if role == "psy" and not client and not fichiers:
        return ecoute_locale(texte), [], [], "psy", "normal"

    donnees = [f for f in fichiers if f.name.lower().endswith(EXTENSIONS_DONNEES)]
    lectures = [f for f in fichiers if f.name.lower().endswith(EXTENSIONS_LECTURE)]
    if donnees:
        resumes = []
        for f in donnees:
            try:
                resume, els, _ = analyser_controle(f.name, f.getvalue())
                resumes.append(resume)
                elements += els
            except Exception as e:
                resumes.append(f"Je n'ai pas pu analyser « {f.name} » : {e}")
        if client:
            reponse = converser_avec_moteur(r, utilisateur, (texte or "Analyse ces données de contrôle de gestion.")
                                            + "\n\nRésultats de mon agent de contrôle de gestion :\n" + "\n".join(resumes),
                                            "controleur", journal)
        else:
            reponse = "📊 " + "\n\n".join(resumes)
        return reponse, elements, journal, "controleur", "normal"

    if lectures and not client:          # sans moteur : elle lit elle-même le livre entier
        from .pensee import confirmation_ingestion, ingerer_pdf
        messages = []
        for f in lectures:
            try:
                if f.name.lower().endswith((".pdf", ".epub", ".txt")):
                    messages.append(confirmation_ingestion(ingerer_pdf(mem, f.name, f.getvalue(), utilisateur)))
                else:
                    source, contenu = brouter_fichier(f.name, f.getvalue())
                    b = digerer(mem, None, None, source, contenu, utilisateur, nb_bouchees=20)
                    messages.append(f"J'ai lu « {source} » : {b['concepts']} concept(s) gardés dans ma mémoire.")
            except (ValueError, ErreurBroutage) as e:
                messages.append(f"Je n'ai pas pu lire « {f.name} » : {e}")
        return "\n\n".join(messages), [], [], "lecteur", "hyper"
    if urls(texte) and not client:       # sans moteur : elle va voir seule, si le site l'autorise
        from .broutage import Brouteur
        from .livres_libres import manger_livre, recommander, site_refuse
        from .pensee import confirmation_ingestion
        brouteur, messages = Brouteur(), []
        for u in urls(texte):
            try:
                if urlparse(u).path.lower().endswith((".pdf", ".epub")):
                    messages.append(confirmation_ingestion(manger_livre(mem, brouteur, u, utilisateur=utilisateur)))
                elif site_refuse(u):
                    raise ErreurBroutage(f"je ne me nourris pas sur ce site ({site_refuse(u)})")
                else:
                    page = brouteur.page(u)
                    b = digerer(mem, None, None, u, page, utilisateur, nb_bouchees=4)
                    messages.append(f"Le site m'autorise : j'ai lu « {u} » et gardé {b['concepts']} concept(s).")
            except (ErreurBroutage, ValueError) as e:
                messages.append(f"« {u} » : {e}\n\n{recommander(texte)}")
            except Exception as e:
                messages.append(f"Je n'ai pas pu ouvrir « {u} » ({type(e).__name__}).")
        return "\n\n".join(messages), [], [], "lecteur", "hyper"
    if lectures or urls(texte):
        bilans = []
        sources = [brouter_fichier(f.name, f.getvalue()) for f in lectures]
        for u in urls(texte):
            try:
                sources.append(brouter_lien(u))
            except (ErreurBroutage, Exception) as e:
                bilans.append(f"Je n'ai pas pu brouter {u} : {e}")
        for source, contenu in sources:
            try:
                b = digerer(mem, r["config"], client, source, contenu, utilisateur, nb_bouchees=4)
            except ErreurBroutage as e:
                bilans.append(f"{source} : {e}")
                continue
            bilans.append(f"J'ai mangé « {source} » : {b['concepts']} concept(s), {b['exercices']} exercice(s) pour "
                          f"mon école, {len(b['lacunes_comblees'])} lacune(s) comblée(s).")
            for d in b["digestions"]:
                elements.append({"type": "liste", "titre": f"🧬 {d['famille']} — digestion {d['confiance']:.0%}",
                                 "lignes": [f"**{c['nom']}** : {c.get('explication', '')}" for c in d["concepts"]]
                                 + ([f"💡 Analogie avec le contrôle de gestion : {d['analogie']}"] if d["analogie"] else [])})
        return "\n\n".join(bilans), elements, journal, "lecteur", "hyper"

    voulu = intention(texte)
    if voulu == "livres_libres":
        from .livres_libres import recommander
        return recommander(texte), [], [], "lecteur", "normal"
    if voulu == "bulletin":
        return ("Voici où j'en suis : mes concepts par famille de sciences, ma vitesse d'apprentissage et mon bulletin "
                "de notes."), [{"type": "croissance"}, {"type": "bulletin", "titre": "📒 Mon bulletin"}], [], "savant", \
            "normal"
    if voulu == "bibliotheque":
        lignes = [f"{d['source']} — {d['famille']} ({len(json.loads(d['concepts']))} concept(s))"
                  for d in mem.digestions(200) if visible_par(d, utilisateur)][:30]
        return ("Voici ce que j'ai lu et digéré." if lignes else "Je n'ai encore rien lu : donne-moi un lien ou un livre !"), \
            [{"type": "liste", "titre": "📚 Ma bibliothèque", "lignes": lignes}], [], "lecteur", "normal"
    if voulu == "prononciation":
        langue = next((l for l in LANGUES if l.lower() in texte.lower()), "Darija")
        if langue == "Darija":          # phrases du quotidien professionnel, score suivi dans le temps
            phrase, sens = random.choice(PHRASES_PRO_DARIJA)
            return ("Écoute-moi, puis répète : je te note sur 100 et je suis tes progrès en darija.",
                    [{"type": "atelier", "langue": langue, "phrase": phrase, "sens": sens, "suivi": True}], [],
                    "savant", "normal")
        phrase = random.choice(LANGUES[langue]["phrases"])
        return (f"Écoute-moi, puis répète : je te note sur 100 ({langue}).",
                [{"type": "atelier", "langue": langue, "phrase": phrase}], [], "savant", "normal")

    if role == "inventeur" and client:
        historique, meilleure = evoluer(r["config"], client, texte, generations=2, taille=4,
                                        inspirations=chercher(mem, texte, n=4, utilisateur=utilisateur))
        finale, debat, meta = debattre(r["config"], client, texte, meilleure, 3)
        mem.garder_idee(utilisateur, texte, finale["titre"], finale.get("description", ""), meta["confiance"],
                        meta["faisabilite"], json.dumps({"debat": debat, "meta": meta}, ensure_ascii=False))
        texte_darija, sens = annonce_darija(finale, meta, nom=utilisateur)
        elements = [{"type": "metriques", "valeurs": [("Confiance", f"{meta['confiance']:.0%}"),
                                                      ("Faisabilité", f"{meta['faisabilite']:.0%}"),
                                                      ("Doutes restants", str(meta["doutes_restants"]))]},
                    {"type": "liste", "titre": "⚔️ Débat intérieur (Critique)",
                     "lignes": [f"Tour {t['tour']} : " + " ; ".join(t["objections"]) for t in debat
                                if t["agent"] == "Critique"]}]
        return (f"{texte_darija}\n\n### 🏆 {finale['titre']}\n{finale.get('description', '')}\n\n_Proverbe : {sens}_",
                elements, journal, "inventeur", "hyper")

    if client:
        return converser_avec_moteur(r, utilisateur, texte, role, journal), [], journal, role, \
            "hyper" if role == "inventeur" else "normal"
    from .pensee import correction_dans_la_conversation
    precedente = st.session_state.get("question_locale")
    merci = correction_dans_la_conversation(texte, mem, st.session_state.get("derniere_conclusion"), precedente,
                                            valider=r.get("admin", False), auteur=utilisateur)
    if merci:
        return merci, [], [], "compagnon", "normal"
    conclusion = {}
    reponse, etapes, confiance = reponse_locale(texte, mem, conclusion, precedente, utilisateur)
    st.session_state["conclusion_locale"] = conclusion
    st.session_state["derniere_conclusion"] = dict(conclusion) or st.session_state.get("derniere_conclusion")
    if not re.search(r"^\s*(ex\w*li\w*|détaill|pourquoi|non\b|oui\b|ok\b)", texte, re.I):
        st.session_state["question_locale"] = texte
    st.session_state["meta_locale"] = {"confiance": confiance, "details": f"{len(etapes)} étape(s) · mon propre cerveau"}
    return reponse, [{"type": "liste", "titre": "🧠 Mon raisonnement", "lignes": etapes}], [], role, "normal"


def apprendre_de_l_echange(r, utilisateur, question, texte):
    """Boucle d'auto-évolution : chaque échange nourrit ses lacunes, ses corrections et son étude autonome."""
    mem = memoire()
    if question:
        noter_si_lacune(mem, question)
        if apprendre_de_soi(mem, question, st.session_state.pop("conclusion_locale", None)):
            st.toast("🌱 J'ai appris de ma propre réponse : je reconnaîtrai mieux cette façon de dire.")
    if not st.session_state.get("conversation_id"):
        st.session_state["conversation_id"] = mem.nouvelle_conversation(utilisateur, question or "Fichier")
    mem.ajouter_message(utilisateur, st.session_state["conversation_id"], "user", question or "(fichier)")
    mem.ajouter_message(utilisateur, st.session_state["conversation_id"], "assistant", texte)
    if any(c["source"] != "auto-apprentissage" for c in mem.corrections_de(seulement_nouvelles=True)):
        reviser_tout(mem)               # les corrections d'une personne comptent tout de suite
    if r["cle_api"] and len(mem.lacunes_ouvertes(SEUIL_ETUDE)) >= SEUIL_ETUDE:
        try:
            etude = etudier_seule(mem, r["config"], client_moteur(r["moteur"], r["cle_api"]))
            st.toast(f"🧠 J'ai étudié seule {etude['etudiees']} question(s) : {etude['apprises']} nouvelle(s) "
                     "connaissance(s).")
        except Exception:
            pass          # l'étude autonome reprendra à la prochaine occasion


@st.fragment(run_every="60s")
def pouls_d_ia_aissa():
    """La croissance en direct : concepts maîtrisés et dernier repas du broutage autonome (rafraîchi chaque minute)."""
    etat = broutage_autonome()
    total = int(serie_croissance(memoire()).iloc[-1].sum())
    repas = etat.get("dernier_repas")
    if not etat.get("actif"):
        broutage = "broutage autonome arrêté par l'administrateur"
    elif repas:
        broutage = (f"dernier repas : « {repas['sujet']} » ({repas['source']}), {repas['concepts']} concept(s), "
                    f"{repas['injections']} analogie(s) injectée(s) dans l'atelier d'invention")
        if repas.get("quarantaine") is not None:
            broutage = (f"dernier repas : « {repas['sujet']} » mis en quarantaine (seulement "
                        f"{repas['quarantaine']:.0%} de mots de son programme)")
        pratique = repas.get("pratique") or {}
        if pratique.get("nom"):
            broutage += (f" · pratique seule en « {pratique['nom']} » : {pratique['avant']:.0%} → {pratique['apres']:.0%}"
                         + (" ✅ adoptée" if pratique["adoptee"] else " (gardée seulement si elle progresse)"))
    elif etat.get("erreurs"):
        broutage = f"broutage autonome actif, nouvel essai bientôt (dernier souci : {etat['erreurs'][-1]})"
    else:
        broutage = "broutage autonome actif, premier repas en cours"
    livre = etat.get("dernier_livre")
    if livre and livre.get("source"):
        broutage += f" · dernier livre lu seule : « {livre['source']} » ({livre['concepts']} concepts)"
    crises = etat.get("crises")
    if crises and crises["resolues"]:
        broutage += f" · crises synthétiques : {crises['justes']}/{crises['resolues']} bien pilotées"
    from .pensee import memoire_vive_mo
    ram = memoire_vive_mo()
    if ram is not None:
        broutage += f" · mémoire vive {ram:.0f} Mo"
    st.caption(f"🌱 {total} concepts maîtrisés · {broutage}")


# ==========================================
# L'espace unique
# ==========================================
def simulateur_de_paie():
    """Simulateur de paie simple pour les clients : brut ou net, et l'essentiel en un coup d'œil (barème 2026)."""
    from . import connaissances as K
    from .pensee import bulletin
    c1, c2 = st.columns([1.2, 1])
    sens = c1.radio("Je connais", ["le salaire brut", "le salaire net"], horizontal=True, key="paie_sens")
    montant = c2.number_input("Montant mensuel (DH)", min_value=0.0, value=8000.0, step=500.0, key="paie_montant")
    brut = K.brut_pour_net(montant) if sens == "le salaire net" else montant
    p = K.calculer_paie(brut)
    colonnes = st.columns(5)
    for col, (libelle, valeur) in zip(colonnes, [("Brut", brut), ("CNSS", p["cnss_salarie"]), ("AMO", p["amo_salarie"]),
                                                 ("IR", p["ir"]), ("Net", p["salaire_net"])]):
        col.metric(libelle, f"{valeur:,.0f} DH".replace(",", " "))
    st.caption(f"Coût pour l'employeur : {brut + p['charges_patronales']:,.0f} DH par mois".replace(",", " "))
    with st.popover("📄 Bulletin détaillé"):
        st.markdown(bulletin(brut))


def dh(v):
    return f"{v:,.0f} DH".replace(",", " ")


def panneau_simulations():
    """Toutes les simulations, au même endroit, pour les visiteurs."""
    from . import connaissances as K
    from . import simulations as S
    with st.expander("🧮 Simulations (paie, crédit, épargne, investissement, impôts, risque…)"):
        choix = st.selectbox("Simulation", [f"{i} {n} — {d}" for i, n, d in S.CATALOGUE], key="sim_choix",
                             label_visibility="collapsed")
        nom = choix.split(" ", 1)[1].split(" — ")[0]
        c = st.columns(3)
        if nom == "Paie":
            simulateur_de_paie()
        elif nom == "Crédit":
            capital = c[0].number_input("Capital (DH)", 0.0, value=200_000.0, step=10_000.0, key="sim_cap")
            taux = c[1].number_input("Taux annuel (%)", 0.0, 30.0, 5.0, 0.1, key="sim_taux") / 100
            ans = c[2].number_input("Durée (ans)", 1, 30, 10, key="sim_ans")
            e = S.echeancier_credit(capital, taux, ans * 12)
            m = st.columns(3)
            m[0].metric("Mensualité", dh(e["mensualite"]))
            m[1].metric("Coût des intérêts", dh(e["cout_total"]))
            m[2].metric("Total remboursé", dh(e["total_rembourse"]))
            st.line_chart(e["tableau"].set_index("Mois")[["Capital restant dû"]])
            st.dataframe(e["tableau"], hide_index=True, width="stretch", height=240)
        elif nom == "Épargne":
            versement = c[0].number_input("Versement mensuel (DH)", 0.0, value=500.0, step=100.0, key="sim_ver")
            taux = c[1].number_input("Rendement annuel (%)", 0.0, 20.0, 4.0, 0.1, key="sim_rend") / 100
            ans = c[2].number_input("Durée (ans)", 1, 50, 10, key="sim_ep_ans")
            e = S.epargne(versement, taux, ans)
            m = st.columns(3)
            m[0].metric("Capital final", dh(e["capital_final"]))
            m[1].metric("Total versé", dh(e["total_verse"]))
            m[2].metric("Intérêts gagnés", dh(e["interets"]))
            st.area_chart(e["tableau"].set_index("Année")[["Total versé", "Intérêts gagnés"]])
        elif nom == "Amortissement":
            valeur = c[0].number_input("Valeur d'acquisition HT (DH)", 0.0, value=100_000.0, step=5_000.0, key="sim_val")
            ans = c[1].number_input("Durée (ans)", 1, 40, 5, key="sim_am_ans")
            methode = c[2].radio("Méthode", ["lineaire", "degressif"], format_func=str.capitalize, key="sim_meth")
            a = S.amortissement(valeur, ans, methode)
            if methode == "degressif":
                st.caption(f"Coefficient {a['coefficient']} → taux {a['taux']:.1%} ; passage au linéaire quand il devient plus favorable.")
            st.dataframe(a["tableau"], hide_index=True, width="stretch")
        elif nom == "Investissement":
            investissement = c[0].number_input("Investissement (DH)", 0.0, value=100_000.0, step=10_000.0, key="sim_inv")
            taux = c[1].number_input("Taux d'actualisation (%)", 0.0, 50.0, 8.0, 0.5, key="sim_act") / 100
            flux = c[2].text_input("Flux annuels (DH, séparés par ;)", "30000; 40000; 50000; 20000", key="sim_flux")
            try:
                liste = [float(x.replace(" ", "").replace(",", ".")) for x in flux.split(";") if x.strip()]
                r = S.rentabilite_investissement(investissement, liste, taux)
                m = st.columns(3)
                m[0].metric("VAN", dh(r["van"]))
                m[1].metric("TRI", f"{r['tri']:.1%}" if r["tri"] is not None else "—")
                m[2].metric("Récupération", f"{r['delai_recuperation_ans']} an(s)" if r["delai_recuperation_ans"] else "jamais")
                st.caption(r["decision"])
            except ValueError:
                st.error("Écris les flux comme ceci : 30000; 40000; 50000")
        elif nom == "Seuil de rentabilité":
            prix = c[0].number_input("Prix de vente unitaire", 0.0, value=100.0, key="sim_px")
            cv = c[1].number_input("Coût variable unitaire", 0.0, value=60.0, key="sim_cv")
            cf = c[2].number_input("Charges fixes annuelles", 0.0, value=200_000.0, step=10_000.0, key="sim_cf")
            r = K.seuil_rentabilite(prix, cv, cf)
            if r.get("seuil_en_quantite") is None:
                st.error(r["remarque"])
            else:
                m = st.columns(2)
                m[0].metric("Seuil (unités)", f"{r['seuil_en_quantite']:,.0f}".replace(",", " "))
                m[1].metric("Seuil (chiffre d'affaires)", dh(r["seuil_en_chiffre_affaires"]))
        elif nom == "Prix de vente":
            cout = c[0].number_input("Coût de revient (DH)", 0.0, value=80.0, key="sim_cout")
            base = c[1].radio("Je fixe", ["un taux de marge (sur coût)", "un taux de marque (sur prix)"], key="sim_base")
            taux = c[2].number_input("Taux (%)", 0.0, 99.0, 25.0, key="sim_tm") / 100
            p = S.prix_de_vente(cout, taux_de_marque=taux) if "marque" in base else S.prix_de_vente(cout, taux_marge_sur_cout=taux)
            m = st.columns(3)
            m[0].metric("Prix HT", f"{p['prix_ht']:,.2f} DH".replace(",", " "))
            m[1].metric("Prix TTC (20 %)", f"{p['prix_ttc']:,.2f} DH".replace(",", " "))
            m[2].metric("Marge", f"{p['marge']:,.2f} DH".replace(",", " "))
            st.caption(f"Taux de marge {p['taux_de_marge']:.1%} · taux de marque {p['taux_de_marque']:.1%}")
        elif nom == "Trésorerie":
            solde = c[0].number_input("Solde de départ (DH)", value=50_000.0, step=5_000.0, key="sim_solde")
            enc = c[1].text_input("Encaissements des 12 mois (;)", "80000; 60000; 90000; 70000; 85000; 60000; "
                                                                    "95000; 70000; 80000; 90000; 75000; 100000", key="sim_enc")
            dec = c[2].text_input("Décaissements des 12 mois (;)", "90000; 85000; 80000; 75000; 80000; 85000; "
                                                                    "80000; 90000; 75000; 80000; 85000; 80000", key="sim_dec")
            try:
                lire = lambda t: [float(x.replace(" ", "").replace(",", ".")) for x in t.split(";") if x.strip()]
                r = S.tresorerie(solde, lire(enc), lire(dec))
                m = st.columns(3)
                m[0].metric("Solde final", dh(r["solde_final"]))
                m[1].metric("Solde le plus bas", dh(r["solde_minimum"]))
                m[2].metric("Premier mois à découvert", r["premier_mois_a_decouvert"] or "aucun")
                st.bar_chart(r["tableau"].set_index("Mois")[["Solde fin de mois"]])
            except ValueError:
                st.error("Écris les montants comme ceci : 80000; 60000; 90000")
        elif nom == "Risque (Monte-Carlo)":
            ca = st.slider("Chiffre d'affaires possible (DH)", 0, 5_000_000, (800_000, 1_200_000), 50_000, key="sim_ca")
            tcv = st.slider("Coûts variables (% du chiffre d'affaires)", 0, 100, (55, 70), key="sim_tcv")
            cf = st.number_input("Charges fixes (DH)", 0.0, value=350_000.0, step=10_000.0, key="sim_mc_cf")
            r = S.risque_monte_carlo(ca[0], ca[1], tcv[0] / 100, tcv[1] / 100, cf)
            m = st.columns(3)
            m[0].metric("Probabilité de perte", f"{r['probabilite_de_perte']:.0%}")
            m[1].metric("Résultat moyen", dh(r["resultat_moyen"]))
            m[2].metric("Fourchette 90 %", f"{dh(r['p5'])} à {dh(r['p95'])}")
            st.bar_chart(pd.Series(r["resultats"]).value_counts(bins=30, sort=False).rename("Simulations")
                         .set_axis([f"{i.mid:,.0f}".replace(",", " ") for i in
                                    pd.Series(r["resultats"]).value_counts(bins=30, sort=False).index]))
            st.caption(f"{r['simulations']:,} tirages au hasard dans les fourchettes (lois uniformes).".replace(",", " "))
        elif nom == "Impôts":
            impot = c[0].radio("Impôt", ["TVA", "IS", "IR"], key="sim_impot")
            if impot == "TVA":
                coll = c[1].number_input("TVA collectée", 0.0, value=50_000.0, key="sim_coll")
                ded = c[2].number_input("TVA déductible", 0.0, value=30_000.0, key="sim_ded")
                r = K.calculer_tva_due(coll, ded)
                st.metric("TVA due" if r["tva_due"] else "Crédit de TVA", dh(r["tva_due"] or r["credit_de_tva"]))
            elif impot == "IS":
                ben = c[1].number_input("Résultat fiscal (DH)", value=500_000.0, step=10_000.0, key="sim_ben")
                prod = c[2].number_input("Produits / CA (DH)", 0.0, value=3_000_000.0, step=100_000.0, key="sim_prod")
                r = K.calculer_is_du(ben, prod)
                m = st.columns(3)
                m[0].metric("IS proportionnel", dh(r["is"]))
                m[1].metric("Cotisation minimale", dh(r["cotisation_minimale"]))
                m[2].metric("IS dû", dh(r["is_du"]))
            else:
                rev = c[1].number_input("Revenu net imposable annuel", 0.0, value=120_000.0, step=5_000.0, key="sim_rev")
                r = K.calculer_ir(rev)
                m = st.columns(3)
                m[0].metric("IR annuel", dh(r["ir_annuel"]))
                m[1].metric("IR mensuel", dh(r["ir_mensuel"]))
                m[2].metric("Taux moyen", f"{r['taux_moyen']:.1%}")
        elif nom == "Auto-entrepreneur":
            ca = c[0].number_input("Chiffre d'affaires annuel (DH)", 0.0, value=150_000.0, step=10_000.0, key="sim_ae")
            act = c[1].radio("Activité", ["services", "commerce"], key="sim_act_ae")
            r = S.auto_entrepreneur(ca, act)
            c[2].metric("Impôt", dh(r["impot"]))
            if r["depasse_le_plafond"]:
                st.warning(f"Au-delà du plafond de {dh(r['plafond'])} : le régime ne s'applique plus.")
        elif nom == "Douane":
            caf = c[0].number_input("Valeur CAF (DH)", 0.0, value=100_000.0, step=5_000.0, key="sim_caf")
            di = c[1].number_input("Droit d'importation (%)", 0.0, 200.0, 17.5, key="sim_di") / 100
            r = K.calculer_droits_import(caf, di)
            c[2].metric("Coût dédouané", dh(r["cout_total_dedouane"]))
            st.caption(f"Droit {dh(r['droit_importation'])} · TVA à l'import {dh(r['tva_import'])}. {r['remarque']}")
        elif nom == "Stock":
            d = c[0].number_input("Demande annuelle (unités)", 0.0, value=12_000.0, key="sim_dem")
            cp = c[1].number_input("Coût d'une commande (DH)", 0.0, value=500.0, key="sim_cp")
            cs = c[2].number_input("Coût de stockage / unité / an", 0.01, value=2.0, key="sim_cs")
            r = K.quantite_wilson(d, cp, cs)
            st.write(" · ".join(f"**{k.replace('_', ' ')}** : {v}" for k, v in r.items()))


def ingestion_de_livres(utilisateur):
    """Dépôt de livres PDF : IA AISSA les lit seule (sans clé API), garde l'essentiel, et le fichier ne reste pas."""
    from .pensee import confirmation_ingestion, ingerer_pdf
    with st.expander("🌌 Cosmic Knowledge Ingestion (Upload PDF/Scanner Books)"):
        st.caption("Dépose des livres ou des cours (PDF, EPUB) : je les lis en entier, sans clé API, je garde l'essentiel "
                   "dans ma mémoire, puis je te dis quand tu peux supprimer le fichier pour gagner de la place. "
                   "Un livre scanné (images de pages) ? Passe-le d'abord à l'OCR d'IWELAH (iwelah.com), puis dépose le "
                   "résultat ici.")
        cle = f"livres_{st.session_state.get('livres_tour', 0)}"
        livres = st.file_uploader("Livres PDF, EPUB ou texte", type=["pdf", "epub", "txt"], accept_multiple_files=True, key=cle,
                                  label_visibility="collapsed")
        if livres:
            messages = []
            for livre in livres:
                with st.spinner(f"📖 Je mange « {livre.name} »…"):
                    try:
                        messages.append(confirmation_ingestion(ingerer_pdf(memoire(), livre.name, livre.getvalue(),
                                                                           utilisateur)))
                    except Exception as e:
                        messages.append(f"Je n'ai pas pu lire « {livre.name} » : {e}")
            del livres                                   # le livre quitte aussi la mémoire vive
            st.session_state["livres_tour"] = st.session_state.get("livres_tour", 0) + 1   # vide le dépôt
            texte = "\n\n".join(messages)
            st.session_state["affichage"].append({"role": "assistant", "texte": "📚 " + texte, "role_ia": "lecteur"})
            st.session_state["parole"] = {"texte": texte, "audio": None, "voix": "fr-FR", "nouveau": True,
                                          "etat": "hyper"}
            st.rerun()


def identite_visiteur():
    """Qui parle : un compte connecté (ou l'administrateur), sinon un visiteur anonyme reconnu par son appareil."""
    from . import admin
    import uuid
    mem = memoire()
    if (admin.valeur_app(mem, "ACCES_VISITEURS") or "ouvert") == "reserve":
        return verifier_acces(st)                       # espace réservé aux personnes autorisées
    if st.session_state.get("authentifie"):
        return st.session_state["authentifie"]
    retenu = admin.session(mem, coffre.lire("ia_aissa_session"))
    if retenu:
        st.session_state["utilisateur"] = st.session_state["authentifie"] = retenu
        return retenu
    ident = coffre.lire("ia_aissa_visiteur")
    if not ident:
        ident = st.session_state.setdefault("visiteur_nouveau", uuid.uuid4().hex[:8])
        coffre.ecrire("ia_aissa_visiteur", ident)
    nom = f"Visiteur {ident}"
    if st.session_state.get("utilisateur") != nom:      # appareil reconnu : on retrouve ses conversations
        st.session_state["utilisateur"] = nom
        st.session_state.pop("affichage", None)
    return nom


def application():
    """Deux espaces : les visiteurs parlent avec IA AISSA ; l'administrateur la nourrit, la commande et la suit."""
    global PAGE_ADMIN
    st.set_page_config(page_title="IA AISSA", page_icon="👽", layout="centered", initial_sidebar_state="collapsed")
    st.markdown(STYLE, unsafe_allow_html=True)
    coffre.ouvrir()                     # ce que cet appareil retient : identité, connexion, clé API
    broutage_autonome()                 # le travailleur autonome (démarré une seule fois par serveur)
    from .espace_admin import espace_admin
    visiteurs = st.Page(espace_visiteur, title="IA AISSA", icon="👽", default=True)
    PAGE_ADMIN = st.Page(espace_admin, title="Administration", icon="🛡️", url_path="admin")
    st.navigation([visiteurs, PAGE_ADMIN], position="hidden").run()


espace_unique = application             # ancien nom


def espace_visiteur():
    if "admin" in st.query_params and PAGE_ADMIN is not None:   # https://…/?admin : chemin de secours vers /admin
        st.switch_page(PAGE_ADMIN)
    utilisateur = identite_visiteur()
    mem = memoire()
    if "affichage" not in st.session_state:
        ouvrir_conversation(utilisateur, None)

    zone_alien = st.container()
    haut = st.columns([5, 1.4])
    with haut[1]:
        r = reglages(utilisateur) if est_admin() else reglages_visiteur(utilisateur)
    role_courant = st.session_state.get("role_ia", "compagnon")
    with haut[0]:
        st.markdown(f'<span class="role">{ROLES[role_courant][0]}</span>', unsafe_allow_html=True)
        st.caption("Je t'aide en droit, comptabilité, fiscalité, social et paie, finance, technique, études… "
                   "et je t'écoute quand ça ne va pas. Je réponds en darija, français, arabe, anglais, espagnol.")

    if "parole" not in st.session_state:          # première visite : l'alien salue, en darija et en français
        prenom = "" if utilisateur.startswith("Visiteur ") else utilisateur
        salut = SALUTATIONS["Darija"][moment_de_la_journee()].format(nom=prenom).replace(" آ ،", "،").replace(" ,", ",").replace("  ", " ")
        texte = (f"{salut} — {SALUTATIONS['Français'][moment_de_la_journee()].format(nom=prenom)} Je suis IA AISSA. "
                 "Pose-moi ta question : un problème juridique, comptable, social, financier, technique, un cours… "
                 "ou dis-moi simplement ce qui ne va pas.").replace(" ,", ",").replace("  ", " ")
        st.session_state["parole"] = {"texte": texte, "audio": _dire(salut, "Darija"), "voix": "ar-MA",
                                      "nouveau": True}

    panneau_simulations()
    if PAGE_ADMIN is not None:
        st.page_link(PAGE_ADMIN, label="🛡️ Administration (réservée)")

    if not st.session_state["affichage"]:
        st.markdown('<p class="astuce">🎙️ Appuie sur le micro bleu pour parler · ✅ pour envoyer ta voix · '
                    '📎 pour déposer un fichier · ou écris simplement</p>', unsafe_allow_html=True)
    for i, m in enumerate(st.session_state["affichage"]):
        afficher_message(m, i, r["voir_outils"])

    saisie = st.chat_input("Parle-moi, écris, ou dépose un fichier (chiffres, livre, image)…",
                           accept_file="multiple", accept_audio=True, submit_mode="disable",
                           file_type=["csv", "xlsx", "xlsm", "xls", "pdf", "epub", "txt", "md", "html"])
    if saisie:
        texte = saisie.text or ""
        fichiers = list(saisie.files or [])
        if getattr(saisie, "audio", None) is not None:
            st.toast("🎙️ Message vocal reçu, je l'écoute…")
            with st.spinner("👂 Je t'écoute…"):
                texte = f"{texte} {transcrire(oreille(), saisie.audio)[0]}".strip()
        affiche = (("🎙️ " if getattr(saisie, "audio", None) is not None else "") + texte
                   + "".join(f"\n\n📎 {f.name}" for f in fichiers)).strip()
        st.session_state["affichage"].append({"role": "user", "texte": affiche})
        afficher_message(st.session_state["affichage"][-1], len(st.session_state["affichage"]) - 1, False)
        debut = time.time()
        with st.spinner("🧠 IA AISSA réfléchit…"):
            reponse, elements, journal, role, etat = traiter(r, utilisateur, texte, fichiers)
        st.session_state["role_ia"] = role
        langue = repondre("langues", reponse[:300])[0]["reponse"]
        meta = st.session_state.pop("meta_locale", None) or meta_conscience(journal, time.time() - debut)
        message = {"role": "assistant", "texte": reponse, "elements": elements, "outils": journal, "langue": langue,
                   "meta": meta, "role_ia": role}
        st.session_state["affichage"].append(message)
        afficher_message(message, len(st.session_state["affichage"]) - 1, r["voir_outils"])
        apprendre_de_l_echange(r, utilisateur, texte, reponse)
        st.session_state["parole"] = {"texte": reponse, "audio": _dire(reponse, langue) if r["vocal"] else None,
                                      "voix": LANGUES[langue]["voix"], "nouveau": True, "etat": etat, "meta": meta}

    parole = st.session_state["parole"]
    image, type_image = mem.media("avatar")
    with zone_alien:
        st.iframe(avatar(parole["texte"][:400] + ("…" if len(parole["texte"]) > 400 else ""), parole.get("audio"),
                         parole.get("voix", "fr-FR"), image, type_image or "image/png",
                         lecture_auto=parole.get("nouveau", False) and r["vocal"], etat=parole.get("etat", "normal"),
                         indicateur=parole.get("meta"), en_haut=not st.session_state["affichage"]), height=590)
    parole["nouveau"] = False
