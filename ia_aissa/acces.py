"""
Accès réservé : IA AISSA ne parle qu'aux personnes autorisées par son propriétaire.

Dans les secrets Streamlit (Settings → Secrets sur Streamlit Cloud, ou .streamlit/secrets.toml en local) :

    [utilisateurs]
    Aissa = "mot-de-passe-d-aissa"
    Karim = "mot-de-passe-de-karim"

Un simple MOT_DE_PASSE = "..." fonctionne aussi (utilisateur unique : Aissa). Sans secret, l'accès est libre.
"""

import hmac
import os

PROPRIETAIRE = "Aissa"


def utilisateurs_autorises(st):
    try:
        secrets = st.secrets
        comptes = dict(secrets.get("utilisateurs", {}))
        mot_de_passe = secrets.get("MOT_DE_PASSE")
    except Exception:
        comptes, mot_de_passe = {}, None
    mot_de_passe = mot_de_passe or os.environ.get("IA_AISSA_MOT_DE_PASSE")
    if mot_de_passe:
        comptes.setdefault(PROPRIETAIRE, mot_de_passe)
    return comptes


def verifier_acces(st):
    """Bloque la page tant que la personne n'est pas identifiée ; renvoie son prénom."""
    comptes = utilisateurs_autorises(st)
    from .admin import utilisateurs as utilisateurs_admin, verifier_utilisateur
    from .partage import memoire
    comptes_admin = utilisateurs_admin(memoire())
    if not comptes and not comptes_admin:
        return st.session_state.get("utilisateur", PROPRIETAIRE)
    if st.session_state.get("utilisateur") in comptes or st.session_state.get("utilisateur") in comptes_admin:
        return st.session_state["utilisateur"]
    from . import coffre
    from .admin import ouvrir_session, session
    retenu = session(memoire(), coffre.lire("ia_aissa_session"))     # connexion retenue sur cet appareil
    if retenu and (retenu in comptes or retenu in comptes_admin):
        st.session_state["utilisateur"] = st.session_state["authentifie"] = retenu
        return retenu
    st.title("🔒 IA AISSA")
    st.write("IA AISSA ne parle qu'aux personnes autorisées par son propriétaire.")
    with st.form("connexion"):
        nom = st.text_input("Prénom")
        saisi = st.text_input("Mot de passe", type="password")
        valide = st.form_submit_button("Entrer")
    if valide:
        compte = next((n for n in comptes if n.lower() == nom.strip().lower()), None)
        if not (compte and hmac.compare_digest(saisi, str(comptes[compte]))):
            compte = verifier_utilisateur(memoire(), nom, saisi)
        if compte:
            st.session_state["utilisateur"] = st.session_state["authentifie"] = compte
            coffre.ecrire("ia_aissa_session", ouvrir_session(memoire(), compte))   # retenu sur cet appareil
            st.rerun()
        st.error("Prénom ou mot de passe incorrect.")
    st.stop()
