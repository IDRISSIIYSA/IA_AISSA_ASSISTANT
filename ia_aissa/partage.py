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


def _secrets_a_plat():
    """Tous les secrets de Streamlit, y compris ceux rangés par erreur dans une section ([general], [secrets]…)."""
    a_plat = {}
    try:
        for cle, valeur in st.secrets.items():
            if hasattr(valeur, "items"):
                for sous_cle, sous_valeur in valeur.items():
                    a_plat.setdefault(str(sous_cle), sous_valeur)
            else:
                a_plat[str(cle)] = valeur
    except Exception:
        pass
    return a_plat


def noms_des_secrets():
    """Les noms (jamais les valeurs) des secrets que l'application voit : pour le diagnostic de l'administrateur."""
    return sorted(_secrets_a_plat())


def secret(nom):
    """Secrets de Streamlit Cloud (même rangés dans une section, majuscules ou non), puis variables d'environnement,
    puis réglages enregistrés par l'administrateur."""
    secrets = _secrets_a_plat()
    trouve = next((v for k, v in secrets.items() if k.strip().upper() == nom.upper()), None)
    valeur = (str(trouve).strip() if trouve not in (None, "") else None) or os.environ.get(nom) or fichier_env().get(nom)
    if valeur or nom in ADRESSES_BASE:
        return valeur
    from .admin import valeur_app
    try:
        return valeur_app(memoire(), nom)
    except Exception:
        return None


ADRESSES_BASE = ("MEMOIRE_URL", "DATABASE_URL")     # DATABASE_URL : le nom donné par Neon (neon deploy, intégrations)
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fichier_env():
    """Variables de .env.local ou .env à la racine du projet (écrits par « neon deploy »), pour un lancement local.
    Ces fichiers ne sont jamais envoyés sur GitHub (.gitignore)."""
    valeurs = {}
    if os.environ.get("IA_AISSA_TESTS"):               # les tests ne touchent jamais la vraie base
        return valeurs
    for nom in (".env", ".env.local"):                  # .env.local l'emporte
        try:
            with open(os.path.join(RACINE, nom), encoding="utf-8") as f:
                for ligne in f:
                    ligne = ligne.strip()
                    if ligne and not ligne.startswith("#") and "=" in ligne:
                        k, v = ligne.removeprefix("export ").split("=", 1)
                        valeurs[k.strip()] = v.strip().strip('"').strip("'")
        except OSError:
            pass
    return valeurs


def adresse_memoire():
    return next((u for u in (secret(n) for n in ADRESSES_BASE) if u), None)


@st.cache_resource(show_spinner="IA AISSA se connecte à sa mémoire…")
def memoire():
    url = adresse_memoire()
    try:
        m = Memoire(url)
        m.erreur = None
    except Exception as e:                      # adresse erronée ou base injoignable : on ne bloque pas l'application
        m = Memoire(None)
        m.erreur = f"{type(e).__name__} : {str(e).splitlines()[0][:200]}"
    brancher(m)
    try:                                          # taux mis à jour par l'administrateur : appliqués à tous les calculs
        from .parametres import appliquer
        appliquer(m)
    except Exception:
        pass
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
    moteur = next((m for m, c in MOTEURS.items() if secret(c["secret"]) and not c.get("local")), None)
    par_jour = int(secret("BROUTAGE_PAR_JOUR") or 6)
    if moteur is None:                  # sans clé : elle broute, rumine et s'exerce seule (aucun coût d'appel)
        return demarrer(memoire(), None, lambda: None, int(secret("BROUTAGE_PAR_JOUR") or 24))
    cle = secret(MOTEURS[moteur]["secret"])
    return demarrer(memoire(), MOTEURS[moteur], lambda: client_moteur(moteur, cle), par_jour)


def repas_du_jour():
    """À chaque visite : si IA AISSA n'a pas encore mangé aujourd'hui, elle lit en arrière-plan l'article de Wikipédia
    qui répond à une de ses lacunes (au plus un appel au grand moteur par jour). Secret facultatif :
    REPAS_DU_JOUR = "non" pour l'arrêter."""
    if os.environ.get("IA_AISSA_TESTS") or str(secret("REPAS_DU_JOUR") or "oui").lower() in ("non", "false", "0"):
        return False
    from .assistant import MOTEURS, client_moteur
    from .nourrir import nourrir_en_arriere_plan
    moteur = next((m for m, c in MOTEURS.items() if secret(c["secret"]) and not c.get("local")), None)
    if moteur is None:
        return nourrir_en_arriere_plan(memoire())
    cle = secret(MOTEURS[moteur]["secret"])
    return nourrir_en_arriere_plan(memoire(), MOTEURS[moteur], lambda: client_moteur(moteur, cle))
