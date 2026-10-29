"""
Le coffre d'IA AISSA : ce que l'appareil doit retenir (clé API, jeton administrateur), gardé dans le stockage local
du navigateur et renvoyé à l'application à chaque chargement, par un composant bidirectionnel (st.components.v2).

Pourquoi pas des cookies ? Sur Streamlit Cloud, le serveur ne reçoit pas les cookies posés par l'application :
la clé était écrite mais jamais relue. Le stockage local, lu par le composant et renvoyé à Python, fonctionne
partout. Seules les entrées dont le nom commence par « ia_aissa_ » sont lues ou écrites.
"""

import streamlit as st

JS = """
export default function(component) {
  const { setStateValue, data } = component;
  for (const [nom, valeur] of ((data && data.ecrire) || [])) {
    try { valeur === null ? localStorage.removeItem(nom) : localStorage.setItem(nom, valeur); } catch (e) {}
  }
  const valeurs = {};
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const nom = localStorage.key(i);
      if (nom && nom.startsWith('ia_aissa_')) valeurs[nom] = localStorage.getItem(nom);
    }
  } catch (e) {}
  const empreinte = JSON.stringify(valeurs);
  if (window.__iaAissaCoffre !== empreinte) {            // n'envoie que les changements (pas de boucle)
    window.__iaAissaCoffre = empreinte;
    setStateValue('valeurs', valeurs);
  }
}
"""

_composant = None


def _monter():
    global _composant
    if _composant is None:
        _composant = st.components.v2.component("ia_aissa_coffre", js=JS)
    return _composant


def ouvrir():
    """À appeler une fois par affichage, en haut de la page : applique les écritures en attente et relit le coffre."""
    ecritures = st.session_state.pop("coffre_ecritures", [])
    resultat = _monter()(key="ia_aissa_coffre", data={"ecrire": ecritures}, on_valeurs_change=lambda: None)
    try:
        valeurs = dict(resultat["valeurs"] or {})
    except (KeyError, TypeError):
        valeurs = dict(getattr(resultat, "valeurs", None) or {})
    for nom, valeur in ecritures:                         # cohérence immédiate, avant le retour du navigateur
        if valeur is None:
            valeurs.pop(nom, None)
        else:
            valeurs[nom] = valeur
    st.session_state["coffre_valeurs"] = valeurs
    return valeurs


def lire(nom):
    return st.session_state.get("coffre_valeurs", {}).get(nom)


def ecrire(nom, valeur):
    """Met en file une écriture (ou un effacement si valeur est None), appliquée au prochain affichage."""
    st.session_state.setdefault("coffre_ecritures", []).append((nom, valeur))
    valeurs = st.session_state.setdefault("coffre_valeurs", {})
    if valeur is None:
        valeurs.pop(nom, None)
    else:
        valeurs[nom] = valeur
