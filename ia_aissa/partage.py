"""Ressources partagées entre les pages : secrets et mémoire durable (avec les cerveaux révisés)."""

import os

import streamlit as st

from .corrections import brancher
from .memoire import Memoire

AIDE_MEMOIRE = (
    "**Pour qu'IA AISSA se souvienne pour toujours** (5 minutes, gratuit) :\n"
    "1. Créez un compte sur [neon.tech](https://neon.tech), puis un projet (région Europe).\n"
    "2. Cliquez sur **Connect** et copiez l'adresse de connexion (elle commence par `postgresql://`).\n"
    "3. Sur [share.streamlit.io](https://share.streamlit.io) : votre application → **Settings → Secrets**, "
    "ajoutez la ligne `MEMOIRE_URL = \"postgresql://…\"` (l'adresse copiée), puis **Save**."
)


def secret(nom):
    """Secrets de Streamlit Cloud, puis variables d'environnement, puis réglages enregistrés par l'administrateur."""
    try:
        valeur = st.secrets.get(nom) or os.environ.get(nom)
    except Exception:
        valeur = os.environ.get(nom)
    if valeur or nom == "MEMOIRE_URL":
        return valeur
    from .admin import valeur_app
    try:
        return valeur_app(memoire(), nom)
    except Exception:
        return None


@st.cache_resource(show_spinner="IA AISSA se connecte à sa mémoire…")
def memoire():
    url = secret("MEMOIRE_URL")
    try:
        m = Memoire(url)
        m.erreur = None
    except Exception as e:                      # adresse erronée ou base injoignable : on ne bloque pas l'application
        m = Memoire(None)
        m.erreur = f"{type(e).__name__} : {str(e).splitlines()[0][:200]}"
    brancher(m)
    return m


def etat_memoire(st_):
    """Affiche l'état de la mémoire : durable, en erreur (avec la cause) ou temporaire (avec la marche à suivre)."""
    m = memoire()
    if m.persistante:
        st_.caption("🟢 Mémoire durable connectée : IA AISSA se souvient de tout, même après un redémarrage.")
    elif m.erreur:
        st_.error(f"🔴 La mémoire durable `MEMOIRE_URL` est configurée mais IA AISSA n'arrive pas à s'y connecter "
                  f"({m.erreur}). Vérifiez l'adresse copiée (mot de passe compris). En attendant, sa mémoire est "
                  f"temporaire.\n\n{AIDE_MEMOIRE}")
    else:
        st_.warning("⚠️ La mémoire d'IA AISSA est temporaire : visages, conversations et apprentissages sont effacés "
                    f"à chaque redémarrage de l'application.\n\n{AIDE_MEMOIRE}")


def broutage_autonome():
    """Démarre le broutage autonome d'IA AISSA (un travailleur par serveur), avec le grand moteur si une clé API de
    l'application existe, sinon seule (rumination locale) ; appelé régulièrement, il ne démarre qu'une fois.
    Secrets facultatifs : BROUTAGE_AUTONOME = "non" pour l'arrêter, BROUTAGE_PAR_JOUR = 6 (repas par jour)."""
    from .assistant import MOTEURS, client_moteur
    from .broutage import ETAT, demarrer
    if str(secret("BROUTAGE_AUTONOME") or "oui").lower() in ("non", "false", "0") or os.environ.get("IA_AISSA_TESTS"):
        return ETAT
    moteur = next((m for m, c in MOTEURS.items() if secret(c["secret"])), None)
    par_jour = int(secret("BROUTAGE_PAR_JOUR") or 6)
    if moteur is None:                  # sans clé : elle broute, rumine et s'exerce seule (aucun coût d'appel)
        return demarrer(memoire(), None, lambda: None, int(secret("BROUTAGE_PAR_JOUR") or 24))
    cle = secret(MOTEURS[moteur]["secret"])
    return demarrer(memoire(), MOTEURS[moteur], lambda: client_moteur(moteur, cle), par_jour)
