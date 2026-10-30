"""
L'appel à l'IA, sobre en jetons :
- préfixe fixe (prompt système identique à chaque requête, en premier) : le fournisseur le met en cache
  automatiquement (OpenAI : à partir de 1 024 jetons de préfixe identique ; d'autres fournisseurs ont leur propre
  mécanisme) et facture les jetons en cache moins cher ;
- fenêtre de mémoire plafonnée : seuls les N derniers messages sont envoyés, les plus anciens sont supprimés ;
- réponse plafonnée (max_tokens) : le coût maximal d'un message est connu à l'avance.
"""

from sqlalchemy import delete, insert, select

from . import base as T
from .garde import maintenant


def fenetre(conn, uid, n):
    lignes = conn.execute(select(T.messages.c.role, T.messages.c.contenu).where(T.messages.c.utilisateur_id == uid)
                          .order_by(T.messages.c.id.desc()).limit(n)).all()
    return [{"role": r.role, "content": r.contenu} for r in reversed(lignes)]


def memoriser(conn, uid, question, reponse, n):
    t = maintenant()
    conn.execute(insert(T.messages), [{"utilisateur_id": uid, "role": "user", "contenu": question, "cree_le": t},
                                      {"utilisateur_id": uid, "role": "assistant", "contenu": reponse, "cree_le": t}])
    garder = select(T.messages.c.id).where(T.messages.c.utilisateur_id == uid).order_by(T.messages.c.id.desc()).limit(n)
    conn.execute(delete(T.messages).where(T.messages.c.utilisateur_id == uid, T.messages.c.id.not_in(garder)))


def appeler(cfg, historique, question, client=None):
    """Renvoie (texte, jetons_entree, jetons_caches, jetons_sortie)."""
    if client is None:
        from openai import OpenAI
        client = OpenAI(base_url=cfg.llm_url, api_key=cfg.llm_cle, timeout=30)
    r = client.chat.completions.create(
        model=cfg.llm_modele, max_tokens=cfg.max_jetons_reponse,
        messages=[{"role": "system", "content": cfg.prompt_systeme}, *historique, {"role": "user", "content": question}])
    u = r.usage
    caches = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    return r.choices[0].message.content or "", u.prompt_tokens, caches, u.completion_tokens


def cout(cfg, entree, caches, sortie):
    return ((entree - caches) * cfg.prix_entree + caches * cfg.prix_entree_cache + sortie * cfg.prix_sortie) / 1e6
