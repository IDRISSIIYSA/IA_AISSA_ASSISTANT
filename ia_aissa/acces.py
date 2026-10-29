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
    if not comptes:
        return st.session_state.get("utilisateur", PROPRIETAIRE)
    if st.session_state.get("utilisateur") in comptes:
        return st.session_state["utilisateur"]
    st.title("🔒 IA AISSA")
    st.write("IA AISSA ne parle qu'aux personnes autorisées par son propriétaire.")
    with st.form("connexion"):
        nom = st.text_input("Prénom")
        saisi = st.text_input("Mot de passe", type="password")
        valide = st.form_submit_button("Entrer")
    if valide:
        compte = next((n for n in comptes if n.lower() == nom.strip().lower()), None)
        if compte and hmac.compare_digest(saisi, str(comptes[compte])):
            st.session_state["utilisateur"] = compte
            st.rerun()
        st.error("Prénom ou mot de passe incorrect.")
    st.stop()
