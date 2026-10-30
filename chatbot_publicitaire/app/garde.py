"""
Le portefeuille scellé, les compteurs anti-fraude et le disjoncteur financier.

Toutes les écritures passent par des mises à jour atomiques en base : deux requêtes simultanées ne peuvent pas
dépenser deux fois le même message (verrou optimiste sur la version), et le solde ne sort jamais de [0 ; plafond].
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, insert, select, update

from . import base as T


class Refus(Exception):
    """Requête refusée : code HTTP et message pour l'utilisateur."""

    def __init__(self, code, message, bloquer=None):
        super().__init__(message)
        self.code, self.message, self.bloquer = code, message, bloquer     # bloquer : compte à bloquer après rollback


def maintenant():
    return datetime.now(timezone.utc)


def jour():
    return maintenant().strftime("%Y-%m-%d")


# ------------------------------------------------------------------ Sessions signées
def jeton_pour(cfg, utilisateur_id):
    sig = hmac.new(cfg.secret.encode(), f"session:{utilisateur_id}".encode(), hashlib.sha256).hexdigest()
    return f"{utilisateur_id}.{sig}"


def utilisateur_du_jeton(cfg, jeton):
    try:
        uid, sig = jeton.rsplit(".", 1)
    except (AttributeError, ValueError):
        raise Refus(401, "Session invalide.")
    attendu = hmac.new(cfg.secret.encode(), f"session:{uid}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, attendu):
        raise Refus(401, "Session invalide.")
    return uid


# ------------------------------------------------------------------ Portefeuille scellé
def sceau(cfg, uid, solde, version):
    return hmac.new(cfg.secret.encode(), f"wallet:{uid}:{solde}:{version}".encode(), hashlib.sha256).hexdigest()


def creer_utilisateur(cfg, conn, ip):
    compter(conn, f"ip:{ip}", "sessions", cfg.sessions_jour_ip, "Trop de sessions créées depuis cette adresse aujourd'hui.")
    uid = secrets.token_urlsafe(24)
    t = maintenant()
    conn.execute(insert(T.utilisateurs).values(id=uid, ip_creation=ip, cree_le=t, bloque=0))
    conn.execute(insert(T.portefeuilles).values(utilisateur_id=uid, solde=0, version=0, sceau=sceau(cfg, uid, 0, 0),
                                                maj_le=t))
    return uid


def lire_portefeuille(cfg, conn, uid):
    u = conn.execute(select(T.utilisateurs.c.bloque).where(T.utilisateurs.c.id == uid)).first()
    if u is None:
        raise Refus(401, "Session inconnue.")
    if u.bloque:
        raise Refus(403, "Compte bloqué.")
    p = conn.execute(select(T.portefeuilles).where(T.portefeuilles.c.utilisateur_id == uid)).first()
    if not hmac.compare_digest(p.sceau, sceau(cfg, uid, p.solde, p.version)):
        raise Refus(403, "Portefeuille altéré : compte bloqué.", bloquer=uid)
    return p


def modifier_solde(cfg, conn, uid, delta):
    """Ajoute delta (négatif pour dépenser), borné à [0 ; plafond]. Renvoie (ancien, nouveau). Atomique."""
    for _ in range(5):
        p = lire_portefeuille(cfg, conn, uid)
        nouveau = max(0, min(cfg.plafond, p.solde + delta))
        if delta < 0 and p.solde + delta < 0:
            raise Refus(402, "Solde épuisé : regardez une vidéo pour obtenir des messages.")
        r = conn.execute(update(T.portefeuilles)
                         .where(T.portefeuilles.c.utilisateur_id == uid, T.portefeuilles.c.version == p.version)
                         .values(solde=nouveau, version=p.version + 1, sceau=sceau(cfg, uid, nouveau, p.version + 1),
                                 maj_le=maintenant()))
        if r.rowcount == 1:
            return p.solde, nouveau
    raise Refus(409, "Requêtes simultanées : réessayez.")


# ------------------------------------------------------------------ Compteurs journaliers
def compter(conn, cle, colonne, limite, message):
    """Incrémente le compteur du jour ; refuse au-delà de la limite (l'incrément n'est pas fait)."""
    j = jour()
    ligne = conn.execute(select(T.compteurs).where(T.compteurs.c.jour == j, T.compteurs.c.cle == cle)).first()
    if ligne is None:
        conn.execute(insert(T.compteurs).values(jour=j, cle=cle, videos=0, messages=0, sessions=0))
        valeur = 0
    else:
        valeur = getattr(ligne, colonne)
    if valeur >= limite:
        raise Refus(429, message)
    conn.execute(update(T.compteurs).where(T.compteurs.c.jour == j, T.compteurs.c.cle == cle,
                                           getattr(T.compteurs.c, colonne) == valeur)
                 .values({colonne: valeur + 1}))


# ------------------------------------------------------------------ Disjoncteur financier
def bilan_du_jour(cfg, conn):
    debut = maintenant().replace(hour=0, minute=0, second=0, microsecond=0)
    depense = conn.execute(select(func.coalesce(func.sum(T.consommation.c.cout_usd), 0.0))
                           .where(T.consommation.c.cree_le >= debut)).scalar_one()
    estime = conn.execute(select(func.coalesce(func.sum(T.recompenses.c.revenu_estime), 0.0))
                          .where(T.recompenses.c.recue_le >= debut)).scalar_one()
    reel = conn.execute(select(T.revenus_reels.c.revenu_usd).where(T.revenus_reels.c.jour == jour())).scalar()
    revenu = float(reel) if reel is not None else float(estime)
    return {"depense": float(depense), "revenu": revenu, "revenu_reel_connu": reel is not None,
            "plafond": min(cfg.budget_jour, revenu / cfg.marge)}


def disjoncteur(cfg, conn):
    """Bloque tout appel à l'IA si la dépense du jour, plus le pire coût d'un message, dépasserait le revenu du jour
    divisé par la marge de sécurité, ou le budget journalier absolu."""
    b = bilan_du_jour(cfg, conn)
    if b["depense"] + cfg.cout_max_message() > b["plafond"]:
        raise Refus(503, "Service en pause : le budget du jour est atteint. Revenez demain.")
    return b


# ------------------------------------------------------------------ Récompenses
def crediter(cfg, conn, reseau, transaction_id, uid, ip):
    """Crédite +recompense messages après une vidéo vérifiée par la régie. Idempotent sur transaction_id."""
    if conn.execute(select(T.recompenses.c.transaction_id)
                    .where(T.recompenses.c.transaction_id == transaction_id)).first():
        return {"deja_traite": True}
    lire_portefeuille(cfg, conn, uid)
    derniere = conn.execute(select(func.max(T.recompenses.c.recue_le))
                            .where(T.recompenses.c.utilisateur_id == uid)).scalar()
    if derniere is not None:
        derniere = derniere if derniere.tzinfo else derniere.replace(tzinfo=timezone.utc)
        if maintenant() - derniere < timedelta(seconds=cfg.secondes_entre_videos):
            raise Refus(429, "Vidéos trop rapprochées.")
    compter(conn, f"ip:{ip}", "videos", cfg.videos_jour_ip, "Limite de vidéos atteinte pour aujourd'hui.")
    compter(conn, f"user:{uid}", "videos", cfg.videos_jour_ip, "Limite de vidéos atteinte pour aujourd'hui.")
    ancien, nouveau = modifier_solde(cfg, conn, uid, cfg.recompense)
    conn.execute(insert(T.recompenses).values(transaction_id=transaction_id, utilisateur_id=uid, reseau=reseau, ip=ip,
                                              messages=nouveau - ancien, revenu_estime=cfg.revenu_par_video,
                                              recue_le=maintenant()))
    return {"deja_traite": False, "credites": nouveau - ancien, "solde": nouveau}


def bloquer(moteur, uid):
    with moteur.begin() as conn:
        conn.execute(update(T.utilisateurs).where(T.utilisateurs.c.id == uid).values(bloque=1))
