"""
Vérification des récompenses envoyées par la régie publicitaire, côté serveur uniquement.

1. AdMob (application mobile) : vérification côté serveur (SSV) — la régie appelle notre URL avec les paramètres de
   la récompense, signés en ECDSA ; la signature est vérifiée avec les clés publiques publiées par Google.
2. Toute régie qui envoie un webhook signé en HMAC-SHA256 avec un secret partagé (en-tête X-Signature).

Le navigateur n'est jamais cru : un clic, un événement JavaScript « vidéo terminée » ou un appel direct à l'API ne
créditent rien.
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.request
from urllib.parse import unquote

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from .garde import Refus

_cles = {"lues_le": 0.0, "cles": {}}


def cles_admob(url, duree_cache=24 * 3600, lire=None):
    """Clés publiques de vérification d'AdMob, gardées en cache 24 h."""
    if time.time() - _cles["lues_le"] > duree_cache or not _cles["cles"]:
        brut = lire(url) if lire else urllib.request.urlopen(url, timeout=10).read()
        donnees = json.loads(brut)
        _cles["cles"] = {str(k["keyId"]): load_pem_public_key(k["pem"].encode()) for k in donnees["keys"]}
        _cles["lues_le"] = time.time()
    return _cles["cles"]


def _b64url(texte):
    return base64.urlsafe_b64decode(texte + "=" * (-len(texte) % 4))


def verifier_admob(cfg, query_string, cles=None):
    """query_string : la chaîne brute reçue (« ad_network=…&…&signature=…&key_id=… »).
    Le message signé est tout ce qui précède « &signature= ». Renvoie (transaction_id, user_id)."""
    if "&signature=" not in query_string:
        raise Refus(400, "Signature absente.")
    message, suite = query_string.split("&signature=", 1)
    params = {k: unquote(v) for k, v in (p.split("=", 1) for p in query_string.split("&") if "=" in p)}
    signature, key_id = params.get("signature", ""), params.get("key_id", "")
    cles = cles if cles is not None else cles_admob(cfg.admob_cles_url)
    cle = cles.get(key_id)
    if cle is None:
        raise Refus(400, "Clé de vérification inconnue.")
    try:
        cle.verify(_b64url(signature), message.encode(), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError):
        raise Refus(403, "Signature de la régie invalide.")
    horodatage = int(params.get("timestamp", "0")) / 1000
    if abs(time.time() - horodatage) > cfg.fraicheur_callback:
        raise Refus(403, "Récompense périmée.")
    if not params.get("transaction_id") or not params.get("user_id"):
        raise Refus(400, "Récompense incomplète.")
    return params["transaction_id"], params["user_id"]


def verifier_webhook(cfg, corps, signature_hex):
    """Webhook générique : corps JSON {transaction_id, user_id, duree_vue, horodatage}, signé en HMAC-SHA256."""
    if not cfg.secret_webhook:
        raise Refus(503, "Webhook de régie non configuré.")
    attendu = hmac.new(cfg.secret_webhook.encode(), corps, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(attendu, signature_hex or ""):
        raise Refus(403, "Signature de la régie invalide.")
    d = json.loads(corps)
    if float(d.get("duree_vue", 0)) < cfg.duree_min_video:
        raise Refus(403, f"Vidéo regardée moins de {cfg.duree_min_video} secondes.")
    if abs(time.time() - float(d.get("horodatage", 0))) > cfg.fraicheur_callback:
        raise Refus(403, "Récompense périmée.")
    return str(d["transaction_id"]), str(d["user_id"])
