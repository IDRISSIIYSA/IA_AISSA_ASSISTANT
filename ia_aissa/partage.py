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
    try:
        return st.secrets.get(nom) or os.environ.get(nom)
    except Exception:
        return os.environ.get(nom)


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
