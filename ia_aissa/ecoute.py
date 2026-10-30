"""
L'écoute bienveillante d'IA AISSA (rôle « psy »), avec ou sans grand moteur.

IA AISSA écoute, reformule et encourage ; elle n'est ni psychologue ni médecin et le dit. Quand une personne parle
de se faire du mal ou de mourir, elle répond d'abord par la sécurité : numéros d'urgence au Maroc, ne pas rester
seul(e), parler à quelqu'un maintenant. Ce message passe avant toute autre réponse, même avec le grand moteur.
"""

import re

DETRESSE = re.compile(
    r"(suicid\w*|me tuer|me suicider|en finir|mettre fin à (mes jours|ma vie)|plus envie de vivre|"
    r"veux mourir|envie de mourir|me faire du mal|me blesser|kill myself|want to die|"
    r"bghit nmout|nebghi nmout|nmout|ntiri rasi|nqtel rasi|بغيت نموت|انتحار|نقتل راسي|نموت)", re.I)

SECURITE = (
    "💚 Ce que tu ressens compte, et tu n'as pas à le porter seul(e). **Si tu es en danger maintenant, appelle tout de "
    "suite le 141 (urgences médicales, SAMU), le 15 (protection civile) ou le 19 (police)**, ou va aux urgences de "
    "l'hôpital le plus proche. Ne reste pas seul(e) : appelle maintenant un proche en qui tu as confiance, et "
    "parle-lui de ce que tu vis. Un médecin ou un psychologue peut vraiment t'aider ; ce n'est pas une faiblesse "
    "de demander de l'aide.\n\nJe suis là pour t'écouter aussi : qu'est-ce qui se passe pour toi en ce moment ?")

PISTES = [
    "Prends une minute pour respirer lentement : inspire 4 secondes, bloque 4, expire 6, cinq fois de suite.",
    "Écris ce qui te pèse sur une feuille : le sortir de ta tête aide souvent à y voir plus clair.",
    "Parle-en à une personne de confiance aujourd'hui, même un court message.",
    "Le sommeil, un peu de marche et des repas réguliers changent beaucoup l'humeur en quelques jours.",
]


def en_detresse(texte):
    return bool(DETRESSE.search(texte or ""))


def ecoute_locale(texte):
    """Réponse d'écoute sans grand moteur : sécurité d'abord si besoin, sinon reformulation et pistes simples."""
    if en_detresse(texte):
        return SECURITE
    return ("Je t'écoute, et merci de me le confier. Ce que tu vis a l'air lourd, et c'est normal de se sentir comme ça "
            "dans une période difficile.\n\n" + "\n".join(f"- {p}" for p in PISTES)
            + "\n\nSi ce mal-être dure plus de deux semaines, ou t'empêche de dormir, de manger ou de travailler, parles-en "
              "à un médecin ou à un psychologue : ça se soigne. Tu veux me raconter ce qui se passe ?"
            + "\n\n_Je suis une IA d'écoute, pas un psychologue._")
