"""
Administration d'IA AISSA, depuis l'application elle-même (sans passer par Streamlit Cloud).

- Le premier mot de passe administrateur créé devient celui de l'application (empreinte PBKDF2, jamais en clair).
- L'administrateur enregistre les clés API de l'application : valables sur tous les appareils et pour le
  broutage autonome. Elles sont gardées dans la base de mémoire d'IA AISSA (la vôtre, si MEMOIRE_URL est
  défini) et ne sont affichées que masquées.
- Il gère les personnes autorisées à parler à IA AISSA, et le broutage autonome.
- Les secrets de Streamlit Cloud restent prioritaires sur ces réglages.
"""

import hashlib
import hmac
import os
import secrets as aleatoire

CLES_APP = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "MINIMAX_API_KEY", "BROUTAGE_AUTONOME", "BROUTAGE_PAR_JOUR",
            "ACCES_VISITEURS", "VISITEURS_MOTEUR", "QUOTA_VISITEUR")
ITERATIONS = 200_000


def empreinte(mot_de_passe, sel=None):
    sel = sel or aleatoire.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), ITERATIONS).hex()
    return f"pbkdf2${ITERATIONS}${sel}${h}"


def verifier(mot_de_passe, empreinte_gardee):
    try:
        _, iterations, sel, h = empreinte_gardee.split("$")
        calcul = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), int(iterations)).hex()
        return hmac.compare_digest(calcul, h)
    except (ValueError, AttributeError):
        return False


# ---------- Administrateur ----------
def admin_existe(memoire):
    return memoire.reglage("admin:empreinte") is not None


def creer_admin(memoire, mot_de_passe, prenom="Aissa"):
    """Crée le compte administrateur : c'est aussi le compte de connexion de son propriétaire (même prénom,
    même mot de passe). Dès lors, l'accès à IA AISSA est réservé aux personnes autorisées."""
    if admin_existe(memoire):
        raise PermissionError("Un administrateur existe déjà.")
    if len(mot_de_passe) < 8:
        raise ValueError("Le mot de passe doit faire au moins 8 caractères.")
    prenom = (prenom or "Aissa").strip()
    memoire.definir_reglage("admin:empreinte", empreinte(mot_de_passe))
    memoire.definir_reglage("admin:utilisateur", prenom)
    ajouter_utilisateur(memoire, prenom, mot_de_passe)
    return nouveau_jeton(memoire)


def lier_proprietaire(memoire, prenom, mot_de_passe):
    """Pour un administrateur créé avant que le compte admin soit aussi un compte de connexion."""
    prenom = (prenom or "Aissa").strip()
    memoire.definir_reglage("admin:utilisateur", prenom)
    if prenom not in utilisateurs(memoire):
        ajouter_utilisateur(memoire, prenom, mot_de_passe)


def proprietaire(memoire):
    """Le prénom du compte administrateur (None s'il n'y a pas encore d'administrateur)."""
    return memoire.reglage("admin:utilisateur")


# ---------- Connexion retenue sur l'appareil ----------
def ouvrir_session(memoire, prenom):
    """Jeton de connexion pour cet appareil (gardé dans son coffre) ; seule son empreinte est stockée."""
    jeton = aleatoire.token_urlsafe(32)
    memoire.definir_reglage(f"session:{hashlib.sha256(jeton.encode()).hexdigest()}", prenom)
    return jeton


def session(memoire, jeton):
    return memoire.reglage(f"session:{hashlib.sha256(jeton.encode()).hexdigest()}") if jeton else None


def fermer_session(memoire, jeton):
    if jeton:
        memoire.supprimer_reglage(f"session:{hashlib.sha256(jeton.encode()).hexdigest()}")


def connexion_admin(memoire, mot_de_passe):
    """Renvoie un jeton de session (à garder dans un cookie) si le mot de passe est bon, sinon None."""
    if verifier(mot_de_passe, memoire.reglage("admin:empreinte")):
        return nouveau_jeton(memoire)
    return None


def nouveau_jeton(memoire):
    jeton = aleatoire.token_urlsafe(32)
    memoire.definir_reglage("admin:jeton", empreinte(jeton, sel=os.urandom(16).hex()))
    return jeton


def jeton_valide(memoire, jeton):
    return bool(jeton) and verifier(jeton, memoire.reglage("admin:jeton"))


def deconnexion(memoire):
    memoire.supprimer_reglage("admin:jeton")


def changer_mot_de_passe(memoire, ancien, nouveau):
    if not verifier(ancien, memoire.reglage("admin:empreinte")):
        raise PermissionError("Ancien mot de passe incorrect.")
    if len(nouveau) < 8:
        raise ValueError("Le mot de passe doit faire au moins 8 caractères.")
    memoire.definir_reglage("admin:empreinte", empreinte(nouveau))


# ---------- Réglages de l'application ----------
def valeur_app(memoire, nom):
    return memoire.reglage(f"app:{nom}") if nom in CLES_APP else None


def definir_valeur_app(memoire, nom, valeur):
    if nom not in CLES_APP:
        raise KeyError(nom)
    if valeur:
        memoire.definir_reglage(f"app:{nom}", str(valeur).strip())
    else:
        memoire.supprimer_reglage(f"app:{nom}")


def masquer(cle):
    return f"{cle[:7]}…{cle[-4:]}" if cle and len(cle) > 14 else "••••"


# ---------- Personnes autorisées ----------
def utilisateurs(memoire):
    return {k.split(":", 1)[1]: v for k, v in memoire.reglages("utilisateur:").items()}


def ajouter_utilisateur(memoire, prenom, mot_de_passe):
    prenom = prenom.strip()
    if not prenom or len(mot_de_passe) < 6:
        raise ValueError("Prénom requis et mot de passe d'au moins 6 caractères.")
    memoire.definir_reglage(f"utilisateur:{prenom}", empreinte(mot_de_passe))


def retirer_utilisateur(memoire, prenom):
    memoire.supprimer_reglage(f"utilisateur:{prenom}")


def verifier_utilisateur(memoire, prenom, mot_de_passe):
    comptes = utilisateurs(memoire)
    nom = next((n for n in comptes if n.lower() == prenom.strip().lower()), None)
    return nom if nom and verifier(mot_de_passe, comptes[nom]) else None
