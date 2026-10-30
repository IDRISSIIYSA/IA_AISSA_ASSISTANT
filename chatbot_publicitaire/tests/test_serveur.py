import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import update

from app import base as T
from app.config import Config
from app.main import creer_app

SECRET_WEBHOOK = "w" * 40


class FausseIA:
    def __init__(self, echoue=False):
        self.appels, self.echoue = [], echoue
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.appels.append(kw)
        if self.echoue:
            raise RuntimeError("panne")
        usage = SimpleNamespace(prompt_tokens=300, completion_tokens=80,
                                prompt_tokens_details=SimpleNamespace(cached_tokens=200))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Réponse."))], usage=usage)


@pytest.fixture
def env(tmp_path):
    cle = ec.generate_private_key(ec.SECP256R1())
    cfg = Config(base=f"sqlite:///{tmp_path / 't.db'}", secret="s" * 40, secret_webhook=SECRET_WEBHOOK,
                 jeton_admin="admin-test", secondes_entre_videos=0)
    ia = FausseIA()
    app = creer_app(cfg, ia, cles_admob={"7": cle.public_key()})
    return SimpleNamespace(client=TestClient(app), app=app, cfg=cfg, ia=ia, cle=cle)


def session(c):
    s = c.post("/api/session").json()
    return s, {"Authorization": f"Bearer {s['jeton']}"}


def webhook(env, uid, tx, duree=31):
    corps = json.dumps({"transaction_id": tx, "user_id": uid, "duree_vue": duree, "horodatage": time.time()}).encode()
    sig = hmac.new(SECRET_WEBHOOK.encode(), corps, hashlib.sha256).hexdigest()
    return env.client.post("/api/recompense/webhook", content=corps, headers={"X-Signature": sig})


def admob(env, uid, tx, cle=None):
    msg = (f"ad_network=5450213213286189855&ad_unit=1234&reward_amount=5&reward_item=messages"
           f"&timestamp={int(time.time() * 1000)}&transaction_id={tx}&user_id={uid}")
    sig = (cle or env.cle).sign(msg.encode(), ec.ECDSA(hashes.SHA256()))
    return env.client.get(f"/api/recompense/admob?{msg}&signature={base64.urlsafe_b64encode(sig).decode().rstrip('=')}&key_id=7")


def test_solde_initial_nul_et_chat_bloque(env):
    s, h = session(env.client)
    assert s["solde"] == 0
    r = env.client.post("/api/chat", json={"message": "Bonjour"}, headers=h)
    assert r.status_code == 402 and not env.ia.appels            # aucun appel payant sans solde


def test_recompense_signee_credite_5_puis_chat(env):
    s, h = session(env.client)
    assert webhook(env, s["utilisateur_id"], "tx1").json()["credites"] == 5
    assert webhook(env, s["utilisateur_id"], "tx1").json()["deja_traite"]     # rejeu sans effet
    r = env.client.post("/api/chat", json={"message": "Bonjour"}, headers=h).json()
    assert r == {"reponse": "Réponse.", "solde": 4}
    assert env.ia.appels[0]["max_tokens"] == env.cfg.max_jetons_reponse
    assert env.ia.appels[0]["messages"][0]["role"] == "system"                # préfixe fixe en tête (cache)


def test_signatures_fausses_ou_video_trop_courte_refusees(env):
    s, _ = session(env.client)
    corps = json.dumps({"transaction_id": "x", "user_id": s["utilisateur_id"], "duree_vue": 31,
                        "horodatage": time.time()}).encode()
    assert env.client.post("/api/recompense/webhook", content=corps, headers={"X-Signature": "00"}).status_code == 403
    assert webhook(env, s["utilisateur_id"], "court", duree=12).status_code == 403
    assert admob(env, s["utilisateur_id"], "a1", cle=ec.generate_private_key(ec.SECP256R1())).status_code == 403
    assert admob(env, s["utilisateur_id"], "a2").json()["credites"] == 5      # vraie signature AdMob (ECDSA)


def test_plafond_de_20_et_limite_de_videos_par_jour(env):
    s, h = session(env.client)
    for i in range(5):
        webhook(env, s["utilisateur_id"], f"p{i}")
    assert env.client.get("/api/solde", headers=h).json()["solde"] == 20
    env.cfg.videos_jour_ip = 5
    assert webhook(env, s["utilisateur_id"], "p6").status_code == 429


def test_fenetre_de_memoire_et_remboursement_si_panne(env):
    s, h = session(env.client)
    webhook(env, s["utilisateur_id"], "m1")
    for i in range(4):
        env.client.post("/api/chat", json={"message": f"question {i}"}, headers=h)
    envoyes = env.ia.appels[-1]["messages"]
    assert len(envoyes) == 1 + env.cfg.historique + 1                         # système + 4 derniers + question
    env.ia.echoue = True
    r = env.client.post("/api/chat", json={"message": "encore"}, headers=h)
    assert r.status_code == 502 and env.client.get("/api/solde", headers=h).json()["solde"] == 1


def test_portefeuille_altere_bloque_le_compte(env):
    s, h = session(env.client)
    with env.app.state.moteur.begin() as conn:
        conn.execute(update(T.portefeuilles).values(solde=20))                # modification directe en base
    assert env.client.get("/api/solde", headers=h).status_code == 403
    webhook(env, s["utilisateur_id"], "z1")
    assert env.client.get("/api/solde", headers=h).status_code == 403        # reste bloqué


def test_disjoncteur_financier(env):
    s, h = session(env.client)
    webhook(env, s["utilisateur_id"], "d1")
    env.cfg.budget_jour = 0.0                                                 # budget épuisé
    assert env.client.post("/api/chat", json={"message": "x"}, headers=h).status_code == 503
    assert env.client.get("/api/solde", headers=h).json()["solde"] == 5       # rien débité


def test_configuration_deficitaire_refusee(tmp_path):
    with pytest.raises(RuntimeError, match="déficitaire"):
        creer_app(Config(base=f"sqlite:///{tmp_path / 'x.db'}", secret="s" * 40, revenu_par_video=0.0001))
    with pytest.raises(RuntimeError, match="SECRET_SERVEUR"):
        creer_app(Config(base=f"sqlite:///{tmp_path / 'y.db'}", secret=""))


def test_jeton_falsifie_et_trop_de_sessions(env):
    s, _ = session(env.client)
    faux = {"Authorization": f"Bearer {s['utilisateur_id']}.0000"}
    assert env.client.get("/api/solde", headers=faux).status_code == 401
    for _ in range(env.cfg.sessions_jour_ip):
        env.client.post("/api/session")
    assert env.client.post("/api/session").status_code == 429


def test_bilan_admin(env):
    assert env.client.get("/api/admin/bilan").status_code == 401
    b = env.client.get("/api/admin/bilan", headers={"Authorization": "Bearer admin-test"}).json()
    assert b["cout_max_par_video"] * env.cfg.marge <= b["revenu_estime_par_video"]
