"""
Le serveur : sessions, solde, récompenses vérifiées par la régie, et la passerelle qui protège l'API de l'IA.

Lancement : uvicorn app.main:app --host 0.0.0.0 --port 8000   (variables d'environnement : voir README.md)
"""

import hmac
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import insert

from . import base as T
from . import garde as G
from . import ia
from . import regie
from .config import Config

STATIQUE = Path(__file__).resolve().parent.parent / "statique"


class Question(BaseModel):
    message: str


def creer_app(cfg=None, client_ia=None, cles_admob=None):
    cfg = cfg or Config()
    erreurs = cfg.verifier()
    if erreurs:
        raise RuntimeError("Démarrage refusé :\n- " + "\n- ".join(erreurs))
    moteur = T.moteur(cfg.base)
    app = FastAPI(title="Chat gratuit financé par la publicité", docs_url=None, redoc_url=None)

    def ip_de(request):
        if cfg.faire_confiance_au_proxy and request.headers.get("x-forwarded-for"):
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        return request.client.host if request.client else "inconnue"

    def uid_de(autorisation):
        return G.utilisateur_du_jeton(cfg, (autorisation or "").removeprefix("Bearer ").strip())

    @app.exception_handler(G.Refus)
    async def refus(_, e):
        if e.bloquer:
            G.bloquer(moteur, e.bloquer)
        return JSONResponse({"erreur": e.message}, status_code=e.code)

    @app.get("/")
    def page():
        return FileResponse(STATIQUE / "index.html")

    @app.post("/api/session")
    def session(request: Request):
        with moteur.begin() as conn:
            uid = G.creer_utilisateur(cfg, conn, ip_de(request))
        return {"jeton": G.jeton_pour(cfg, uid), "utilisateur_id": uid, "solde": 0, "plafond": cfg.plafond,
                "messages_par_video": cfg.recompense}

    @app.get("/api/solde")
    def solde(authorization: str = Header(default="")):
        uid = uid_de(authorization)
        with moteur.begin() as conn:
            p = G.lire_portefeuille(cfg, conn, uid)
        return {"solde": p.solde, "plafond": cfg.plafond}

    @app.post("/api/chat")
    def chat(q: Question, request: Request, authorization: str = Header(default="")):
        uid, ip = uid_de(authorization), ip_de(request)
        texte = q.message.strip()
        if not texte:
            raise G.Refus(400, "Message vide.")
        if len(texte) > cfg.max_caracteres_message:
            raise G.Refus(413, f"Message trop long ({cfg.max_caracteres_message} caractères au plus).")
        # 1. Passerelle : disjoncteur, limites du jour, puis débit atomique — avant tout appel payant
        with moteur.begin() as conn:
            _, reste = G.modifier_solde(cfg, conn, uid, -1)      # tout est annulé si un contrôle suivant refuse
            G.compter(conn, f"ip:{ip}", "messages", cfg.messages_jour_ip, "Limite de messages atteinte pour aujourd'hui.")
            G.disjoncteur(cfg, conn)
            historique = ia.fenetre(conn, uid, cfg.historique)
        # 2. Appel à l'IA hors transaction ; remboursement du message en cas d'échec
        try:
            reponse, entree, caches, sortie = ia.appeler(cfg, historique, texte, client_ia)
        except Exception:
            with moteur.begin() as conn:
                _, reste = G.modifier_solde(cfg, conn, uid, +1)
            raise G.Refus(502, "L'IA n'a pas répondu : votre message a été remboursé.")
        # 3. Coût réel et fenêtre de mémoire
        with moteur.begin() as conn:
            conn.execute(insert(T.consommation).values(utilisateur_id=uid, jetons_entree=entree, jetons_caches=caches,
                                                       jetons_sortie=sortie, cout_usd=ia.cout(cfg, entree, caches, sortie),
                                                       cree_le=G.maintenant()))
            ia.memoriser(conn, uid, texte, reponse, cfg.historique)
        return {"reponse": reponse, "solde": reste}

    @app.get("/api/recompense/admob")
    def recompense_admob(request: Request):
        """URL de rappel SSV à déclarer dans AdMob (bloc d'annonces avec récompense → vérification côté serveur)."""
        transaction, uid = regie.verifier_admob(cfg, request.url.query, cles_admob)
        with moteur.begin() as conn:
            r = G.crediter(cfg, conn, "admob", transaction, uid, ip_de(request))
        return r

    @app.post("/api/recompense/webhook")
    async def recompense_webhook(request: Request, x_signature: str = Header(default="")):
        transaction, uid = regie.verifier_webhook(cfg, await request.body(), x_signature)
        with moteur.begin() as conn:
            r = G.crediter(cfg, conn, "webhook", transaction, uid, ip_de(request))
        return r

    @app.get("/api/admin/bilan")
    def bilan(authorization: str = Header(default="")):
        verifier_admin(authorization)
        with moteur.begin() as conn:
            b = G.bilan_du_jour(cfg, conn)
        return {**b, "cout_max_message": cfg.cout_max_message(),
                "cout_max_par_video": cfg.cout_max_message() * cfg.recompense, "revenu_estime_par_video": cfg.revenu_par_video}

    @app.post("/api/admin/revenu")
    def revenu(jour: str, revenu_usd: float, authorization: str = Header(default="")):
        """Le revenu réel du jour, lu dans le rapport de la régie : il remplace l'estimation dans le disjoncteur."""
        verifier_admin(authorization)
        with moteur.begin() as conn:
            conn.execute(T.revenus_reels.delete().where(T.revenus_reels.c.jour == jour))
            conn.execute(insert(T.revenus_reels).values(jour=jour, revenu_usd=revenu_usd))
        return {"ok": True}

    def verifier_admin(autorisation):
        jeton = (autorisation or "").removeprefix("Bearer ").strip()
        if not cfg.jeton_admin or not hmac.compare_digest(jeton, cfg.jeton_admin):
            raise G.Refus(401, "Accès réservé.")

    app.state.moteur, app.state.cfg = moteur, cfg
    return app


app = None
if __name__ != "__main__":
    try:
        app = creer_app()
    except RuntimeError as e:          # import par les tests sans secrets : l'application est créée par le test
        import os
        if os.environ.get("CHAT_PUB_TESTS") != "1":
            raise
