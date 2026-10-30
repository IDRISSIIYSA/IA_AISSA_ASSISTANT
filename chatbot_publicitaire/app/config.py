"""Réglages, lus dans les variables d'environnement (jamais dans le code ni dans le dépôt)."""

import os
from dataclasses import dataclass, field


def _f(nom, defaut):
    return float(os.environ.get(nom, defaut))


def _i(nom, defaut):
    return int(os.environ.get(nom, defaut))


@dataclass
class Config:
    base: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:///chat.db"))
    secret: str = field(default_factory=lambda: os.environ.get("SECRET_SERVEUR", ""))
    secret_webhook: str = field(default_factory=lambda: os.environ.get("SECRET_WEBHOOK_REGIE", ""))
    jeton_admin: str = field(default_factory=lambda: os.environ.get("JETON_ADMIN", ""))
    faire_confiance_au_proxy: bool = field(default_factory=lambda: os.environ.get("DERRIERE_PROXY", "0") == "1")
    # IA (toute API compatible OpenAI : GPT-4o-mini, MiniMax, etc.)
    llm_url: str = field(default_factory=lambda: os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_cle: str = field(default_factory=lambda: os.environ.get("LLM_API_KEY", ""))
    llm_modele: str = field(default_factory=lambda: os.environ.get("LLM_MODELE", "gpt-4o-mini"))
    prix_entree: float = field(default_factory=lambda: _f("PRIX_ENTREE_USD_PAR_MILLION", 0.15))
    prix_entree_cache: float = field(default_factory=lambda: _f("PRIX_ENTREE_CACHE_USD_PAR_MILLION", 0.075))
    prix_sortie: float = field(default_factory=lambda: _f("PRIX_SORTIE_USD_PAR_MILLION", 0.60))
    max_jetons_reponse: int = field(default_factory=lambda: _i("MAX_JETONS_REPONSE", 400))
    max_caracteres_message: int = field(default_factory=lambda: _i("MAX_CARACTERES_MESSAGE", 1000))
    historique: int = field(default_factory=lambda: _i("HISTORIQUE_MESSAGES", 4))
    # Portefeuille et anti-fraude
    recompense: int = field(default_factory=lambda: _i("MESSAGES_PAR_VIDEO", 5))
    plafond: int = field(default_factory=lambda: _i("PLAFOND_PORTEFEUILLE", 20))
    videos_jour_ip: int = field(default_factory=lambda: _i("VIDEOS_PAR_JOUR_ET_IP", 20))
    messages_jour_ip: int = field(default_factory=lambda: _i("MESSAGES_PAR_JOUR_ET_IP", 100))
    sessions_jour_ip: int = field(default_factory=lambda: _i("SESSIONS_PAR_JOUR_ET_IP", 5))
    secondes_entre_videos: int = field(default_factory=lambda: _i("SECONDES_MIN_ENTRE_VIDEOS", 30))
    duree_min_video: int = field(default_factory=lambda: _i("DUREE_MIN_VIDEO_SECONDES", 30))
    fraicheur_callback: int = field(default_factory=lambda: _i("FRAICHEUR_CALLBACK_SECONDES", 3600))
    # Disjoncteur financier
    revenu_par_video: float = field(default_factory=lambda: _f("REVENU_ESTIME_USD_PAR_VIDEO", 0.005))
    marge: float = field(default_factory=lambda: _f("MARGE_DE_SECURITE", 1.5))
    budget_jour: float = field(default_factory=lambda: _f("BUDGET_IA_USD_PAR_JOUR", 5.0))
    admob_cles_url: str = field(default_factory=lambda: os.environ.get(
        "ADMOB_CLES_URL", "https://www.gstatic.com/admob/reward/verifier-keys.json"))
    prompt_systeme: str = field(default_factory=lambda: os.environ.get("PROMPT_SYSTEME", PROMPT_SYSTEME))

    def cout_max_message(self):
        """Coût maximal d'un message : prompt système + historique + message au plus long, réponse au plus long."""
        jetons_entree = len(self.prompt_systeme) // 3 + (self.historique + 1) * (self.max_caracteres_message // 3 + 10)
        return (jetons_entree * self.prix_entree + self.max_jetons_reponse * self.prix_sortie) / 1e6

    def verifier(self):
        """Refuse une configuration qui perdrait de l'argent par construction, ou sans secrets."""
        erreurs = []
        if len(self.secret) < 32:
            erreurs.append("SECRET_SERVEUR manquant ou trop court (32 caractères au moins).")
        cout_recompense = self.recompense * self.cout_max_message()
        if cout_recompense * self.marge > self.revenu_par_video:
            erreurs.append(f"Configuration déficitaire : {self.recompense} messages coûtent jusqu'à "
                           f"{cout_recompense:.5f} USD, × marge {self.marge} > revenu estimé d'une vidéo "
                           f"{self.revenu_par_video:.5f} USD. Baissez MAX_JETONS_REPONSE, MESSAGES_PAR_VIDEO ou "
                           "HISTORIQUE_MESSAGES, ou choisissez un modèle moins cher.")
        return erreurs


# Préfixe fixe, toujours en tête de la requête : c'est ce qui permet la mise en cache du prompt par le fournisseur.
PROMPT_SYSTEME = ("Tu es un assistant utile, précis et bref. Réponds dans la langue de l'utilisateur, en 150 mots au "
                  "plus sauf demande contraire. Refuse poliment les demandes illégales ou dangereuses.")
