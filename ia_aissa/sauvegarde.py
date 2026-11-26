"""
Sauvegarde de la mémoire d'IA AISSA et santé du serveur.

Sauvegarde : toutes les tables de la base (Neon en ligne, SQLite en local) exportées en JSON compressé (gzip), par
SQLAlchemy — sans pg_dump, absent de Streamlit Cloud. L'administrateur la télécharge (stockage à part : son
ordinateur) ; sur un serveur dédié, deploy/sauvegarde.sh fait chaque nuit un pg_dump avec rotation sur 30 jours.
⚠️ Une sauvegarde contient les conversations et les réglages : à garder en lieu sûr.

Restauration : `restaurer(memoire, octets)` remplit une base VIDE (refus sinon), table par table, dans l'ordre des
clés étrangères. En ligne de commande :
    python -m ia_aissa.sauvegarde exporter sauvegarde.json.gz       (base : MEMOIRE_URL)
    python -m ia_aissa.sauvegarde restaurer sauvegarde.json.gz      (dans une base vide)

Santé : mémoire du serveur et du processus, disque, modules lourds chargés, cerveaux en cache, index de lecture.
"""

import base64
import gzip
import json
import os
import shutil
import sys
import threading
from datetime import date, datetime, timezone

from sqlalchemy import func, insert, select

from .memoire import meta

FORMAT = 1
ALERTE_JOURS = 7                 # au-delà, l'administration rappelle de télécharger une sauvegarde
SEUIL_PASSAGES = 60_000          # au-delà, l'index de lecture menace la mémoire du serveur en ligne (≈ 1 Go)


def _vers_json(v):
    if isinstance(v, (datetime, date)):
        return {"__date__": v.isoformat()}
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"__octets__": base64.b64encode(bytes(v)).decode("ascii")}
    return v


def _depuis_json(v):
    if isinstance(v, dict) and "__date__" in v:
        return datetime.fromisoformat(v["__date__"])
    if isinstance(v, dict) and "__octets__" in v:
        return base64.b64decode(v["__octets__"])
    return v


def exporter(memoire):
    """Toute la base en JSON compressé. Renvoie (octets, bilan {table: lignes})."""
    tables, bilan = {}, {}
    with memoire.moteur.connect() as c:
        for table in meta.sorted_tables:
            lignes = [{k: _vers_json(v) for k, v in l._mapping.items()} for l in c.execute(select(table))]
            tables[table.name] = lignes
            bilan[table.name] = len(lignes)
    document = {"format": FORMAT, "date": datetime.now(timezone.utc).isoformat(), "tables": tables}
    octets = gzip.compress(json.dumps(document, ensure_ascii=False).encode("utf-8"))
    memoire.definir_reglage("sauvegarde:derniere", json.dumps(
        {"date": document["date"][:10], "lignes": sum(bilan.values()), "octets": len(octets)}))
    return octets, bilan


def restaurer(memoire, octets):
    """Remplit une base vide avec une sauvegarde. Renvoie {table: lignes restaurées}."""
    document = json.loads(gzip.decompress(octets).decode("utf-8"))
    if document.get("format") != FORMAT:
        raise ValueError(f"Format de sauvegarde inconnu : {document.get('format')}.")
    with memoire.moteur.connect() as c:
        pleines = [t.name for t in meta.sorted_tables if t.name != "reglages"
                   and c.execute(select(func.count()).select_from(t)).scalar()]
    if pleines:
        raise ValueError(f"La base n'est pas vide ({', '.join(pleines)}) : restauration refusée pour ne rien écraser.")
    bilan = {}
    with memoire.moteur.begin() as c:
        for table in meta.sorted_tables:                       # ordre des clés étrangères
            lignes = [{k: _depuis_json(v) for k, v in l.items()} for l in document["tables"].get(table.name, [])]
            if table.name == "reglages":                       # réglages : ceux de la sauvegarde remplacent
                c.execute(table.delete())
            if lignes:
                c.execute(insert(table), lignes)
            bilan[table.name] = len(lignes)
    memoire._cache_reglages = {}
    return bilan


def derniere_sauvegarde(memoire):
    brut = memoire.reglage("sauvegarde:derniere")
    return json.loads(brut) if brut else None


def alerte_sauvegarde(memoire, aujourdhui=None):
    """Message si aucune sauvegarde n'a été téléchargée depuis ALERTE_JOURS jours (base persistante seulement)."""
    if not getattr(memoire, "persistante", False):
        return None
    aujourdhui = aujourdhui or date.today()
    d = derniere_sauvegarde(memoire)
    if d is None:
        return "💾 Aucune sauvegarde de la mémoire n'a encore été téléchargée : faites-en une (onglet 🕹️ Commandes)."
    jours = (aujourdhui - date.fromisoformat(d["date"])).days
    if jours > ALERTE_JOURS:
        return f"💾 Dernière sauvegarde de la mémoire il y a {jours} jours : téléchargez-en une nouvelle."
    return None


def etat_bibliotheque(memoire):
    """Passages gardés dans la base : total, lus seule sur le web (« IA AISSA ») et donnés par des personnes."""
    comptes = memoire.compter_passages()
    total = sum(c["passages"] for c in comptes)
    web = sum(c["passages"] for c in comptes if c["utilisateur"] == "IA AISSA")
    return {"total": total, "web": web, "autres": total - web, "sources": len(comptes)}


def alerte_passages(etat, seuil=SEUIL_PASSAGES):
    """Message au-delà de `seuil` passages. Rien n'est oublié sans la décision de l'administrateur."""
    if etat["total"] <= seuil:
        return None
    return (f"📚 {etat['total']:,} passages en mémoire (seuil {seuil:,}), dont {etat['web']:,} lus seule sur le web : "
            "l'index de lecture risque de saturer la mémoire du serveur. À décider : oublier les lectures web jamais "
            "utilisées pour répondre (les livres et documents donnés ne sont jamais oubliés).").replace(",", " ")


# ==========================================
# Sauvegarde automatique hebdomadaire vers un stockage objet compatible S3 (AWS S3, Neon Object Storage, R2…)
# ==========================================
# Secrets (Streamlit Cloud, jamais dans le dépôt) : SAUVEGARDE_S3_ENDPOINT (ex. https://s3.eu-west-3.amazonaws.com),
# SAUVEGARDE_S3_BUCKET, SAUVEGARDE_S3_CLE (identifiant de clé), SAUVEGARDE_S3_SECRET, SAUVEGARDE_S3_REGION (facultatif).
# Signature AWS Signature Version 4 écrite ici (une trentaine de lignes) plutôt que boto3 (lourd pour le petit serveur).
SECRETS_S3 = ("SAUVEGARDE_S3_ENDPOINT", "SAUVEGARDE_S3_BUCKET", "SAUVEGARDE_S3_CLE", "SAUVEGARDE_S3_SECRET")
CLE_AUTO = "sauvegarde:auto"
PERIODE_AUTO_JOURS = 7


def config_s3(secret):
    """La configuration lue dans les secrets (secret(nom) → valeur), ou None s'il en manque une."""
    valeurs = {n: secret(n) for n in SECRETS_S3}
    if not all(valeurs.values()):
        return None
    return {"endpoint": valeurs["SAUVEGARDE_S3_ENDPOINT"].rstrip("/"), "bucket": valeurs["SAUVEGARDE_S3_BUCKET"],
            "cle": valeurs["SAUVEGARDE_S3_CLE"], "secret": valeurs["SAUVEGARDE_S3_SECRET"],
            "region": secret("SAUVEGARDE_S3_REGION") or "us-east-1"}


def signer_v4(methode, url, en_tetes, corps_sha256, cle, secret_cle, region, service="s3", quand=None):
    """En-têtes signés (AWS Signature Version 4) : Authorization, x-amz-date, x-amz-content-sha256, host."""
    import hashlib
    import hmac
    from urllib.parse import quote, urlsplit
    quand = quand or datetime.now(timezone.utc)
    amz_date, jour = quand.strftime("%Y%m%dT%H%M%SZ"), quand.strftime("%Y%m%d")
    u = urlsplit(url)
    en_tetes = {k.lower(): str(v).strip() for k, v in en_tetes.items()}
    en_tetes.update({"host": u.netloc, "x-amz-date": amz_date})
    if service == "s3":
        en_tetes["x-amz-content-sha256"] = corps_sha256
    noms = sorted(en_tetes)
    requete = "\n".join([methode, quote(u.path or "/", safe="/~"), u.query,
                         "".join(f"{n}:{en_tetes[n]}\n" for n in noms), ";".join(noms), corps_sha256])
    portee = f"{jour}/{region}/{service}/aws4_request"
    a_signer = "\n".join(["AWS4-HMAC-SHA256", amz_date, portee, hashlib.sha256(requete.encode()).hexdigest()])
    k = ("AWS4" + secret_cle).encode()
    for morceau in (jour, region, service, "aws4_request"):
        k = hmac.new(k, morceau.encode(), hashlib.sha256).digest()
    signature = hmac.new(k, a_signer.encode(), hashlib.sha256).hexdigest()
    en_tetes["authorization"] = (f"AWS4-HMAC-SHA256 Credential={cle}/{portee}, SignedHeaders={';'.join(noms)}, "
                                 f"Signature={signature}")
    return en_tetes


def envoyer_s3(octets, nom, config, envoyer=None):
    """Dépose `octets` sous `nom` dans le bucket (adresse « chemin » : endpoint/bucket/nom). Renvoie le code HTTP."""
    import hashlib
    url = f"{config['endpoint']}/{config['bucket']}/{nom}"
    en_tetes = signer_v4("PUT", url, {"content-type": "application/gzip"}, hashlib.sha256(octets).hexdigest(),
                         config["cle"], config["secret"], config["region"])
    if envoyer is None:
        import requests
        envoyer = lambda u, h, d: requests.put(u, headers=h, data=d, timeout=120).status_code
    return envoyer(url, en_tetes, octets)


def verifier_restauration(octets, bilan):
    """Restaure la sauvegarde dans une base de test temporaire (fichier SQLite sur disque : pas de mémoire en plus) et
    compare le nombre de lignes de chaque table. Renvoie (vrai si identique, {table: lignes restaurées})."""
    import tempfile
    from .memoire import Memoire
    with tempfile.TemporaryDirectory() as dossier:
        test = Memoire(f"sqlite:///{dossier}/verification.db")
        restaure = restaurer(test, octets)
        test.moteur.dispose()
    return all(restaure.get(t, 0) == n for t, n in bilan.items()), restaure


def derniere_auto(memoire):
    brut = memoire.reglage(CLE_AUTO)
    return json.loads(brut) if brut else None


def sauvegarde_hebdomadaire(memoire, config, maintenant=None, envoyer=None):
    """Une fois tous les PERIODE_AUTO_JOURS jours : exporte, vérifie la restauration sur une base de test, puis envoie
    vers le stockage objet (seulement si la vérification réussit). Renvoie le compte rendu, ou None si pas encore dû."""
    maintenant = maintenant or datetime.now(timezone.utc)
    d = derniere_auto(memoire)
    if d and d.get("statut") == "envoyée" and (maintenant - datetime.fromisoformat(d["date"])).days < PERIODE_AUTO_JOURS:
        return None
    octets, bilan = exporter(memoire)
    ok, _ = verifier_restauration(octets, bilan)
    nom = f"ia_aissa/ia_aissa_{maintenant:%Y-%m-%d}.json.gz"
    compte = {"date": maintenant.isoformat(), "fichier": nom, "octets": len(octets), "lignes": sum(bilan.values()),
              "restauration_verifiee": ok}
    if not ok:
        compte["statut"] = "non envoyée : la restauration de test ne retrouve pas toutes les lignes"
    else:
        try:
            code = envoyer_s3(octets, nom, config, envoyer)
            compte["statut"] = "envoyée" if 200 <= code < 300 else f"refusée par le stockage (HTTP {code})"
        except Exception as e:                           # réseau, adresse… : jamais la clé dans le message
            compte["statut"] = f"échec de l'envoi ({type(e).__name__})"
    memoire.definir_reglage(CLE_AUTO, json.dumps(compte, ensure_ascii=False))
    return compte


# ==========================================
# Santé du serveur
# ==========================================
def _meminfo():
    infos = {}
    try:
        with open("/proc/meminfo") as f:
            for ligne in f:
                cle, valeur = ligne.split(":", 1)
                infos[cle] = int(valeur.split()[0]) / 1024           # kio → Mio
    except (OSError, ValueError):
        pass
    return infos


def _processus():
    infos = {}
    try:
        with open("/proc/self/status") as f:
            for ligne in f:
                if ligne.startswith(("VmRSS:", "VmHWM:")):
                    infos[ligne.split(":")[0]] = int(ligne.split()[1]) / 1024
    except (OSError, ValueError):
        pass
    return infos


def sante():
    """État du serveur : mémoire, disque, modules lourds, cerveaux en cache, index de lecture."""
    from . import chrono
    mem, proc = _meminfo(), _processus()
    disque = shutil.disk_usage(os.path.abspath(os.sep))
    lourds = {nom: nom in sys.modules for nom in ("torch", "faster_whisper", "cv2", "openpyxl", "openai", "anthropic")}
    cerveaux, passages, index_mo = [], None, None
    if "ia_aissa.ecole" in sys.modules:
        cerveaux = sorted(sys.modules["ia_aissa.ecole"]._CACHE)
    if "ia_aissa.lecture" in sys.modules:
        index = sys.modules["ia_aissa.lecture"]._INDEX.get("index")
        if index is not None:
            passages, index_mo = len(index), round(index.memoire_mo(), 1)
    return {
        "memoire_totale_mo": round(mem.get("MemTotal", 0)), "memoire_disponible_mo": round(mem.get("MemAvailable", 0)),
        "processus_mo": round(proc.get("VmRSS", 0)), "processus_pic_mo": round(proc.get("VmHWM", 0)),
        "disque_libre_go": round(disque.free / 1e9, 1), "disque_total_go": round(disque.total / 1e9, 1),
        "age_s": chrono.age_du_processus(), "fils": threading.active_count(), "modules_lourds": lourds,
        "cerveaux_en_cache": cerveaux, "passages_indexes": passages,
        "index_mo": index_mo,
        "python": sys.version.split()[0],
    }


# Courbe de la mémoire : un point par heure (à la première visite de l'heure), 14 jours gardés en base
CLE_COURBE = "sante:memoire"
INTERVALLE_S = 3600
GARDER_POINTS = 14 * 24
SEUIL_SATURATION = 0.85          # part de la mémoire totale du serveur au-delà de laquelle le 502 menace
_DERNIER_POINT = {"t": 0.0}


def courbe_memoire(memoire):
    brut = memoire.reglage(CLE_COURBE) if memoire is not None else None
    return json.loads(brut) if brut else []


def noter_memoire(memoire, maintenant=None, mesure=None):
    """Ajoute un point (mémoire du processus, pic, mémoire libre, âge du serveur) si le dernier a plus d'une heure.
    Le contrôle se fait d'abord en mémoire : la base n'est lue qu'une fois par heure. Renvoie le point, ou None."""
    import time
    maintenant = maintenant or time.time()
    if maintenant - _DERNIER_POINT["t"] < INTERVALLE_S:
        return None
    points = courbe_memoire(memoire)
    if points and maintenant - points[-1]["t"] < INTERVALLE_S:          # un autre processus vient de noter
        _DERNIER_POINT["t"] = points[-1]["t"]
        return None
    s = mesure or sante()
    point = {"t": round(maintenant), "processus_mo": s["processus_mo"], "pic_mo": s["processus_pic_mo"],
             "libre_mo": s["memoire_disponible_mo"], "total_mo": s["memoire_totale_mo"],
             "age_h": round(s["age_s"] / 3600, 1) if s.get("age_s") else None}
    points = (points + [point])[-GARDER_POINTS:]
    memoire.definir_reglage(CLE_COURBE, json.dumps(points))
    _DERNIER_POINT["t"] = maintenant
    return point


def depuis_le_redemarrage(points):
    """Les points du processus actuel : on remonte tant que l'âge du serveur décroît d'un point à l'autre."""
    suite = []
    for p in reversed(points):
        if suite and (p.get("age_h") is None or suite[-1].get("age_h") is None or p["age_h"] >= suite[-1]["age_h"]):
            break
        suite.append(p)
    return suite[::-1]


def alerte_memoire(points, horizon_h=48):
    """Message si, depuis le redémarrage, la mémoire du processus monte au point d'atteindre SEUIL_SATURATION de la
    mémoire totale dans moins de `horizon_h` heures (pente par moindres carrés, au moins 6 points)."""
    import statistics
    suite = depuis_le_redemarrage(points)
    if len(suite) < 6 or not suite[-1].get("total_mo"):
        return None
    pente, _ = statistics.linear_regression([p["t"] / 3600 for p in suite], [p["processus_mo"] for p in suite])
    limite = SEUIL_SATURATION * suite[-1]["total_mo"]
    reste = limite - suite[-1]["processus_mo"]
    if pente <= 0.5 or reste <= 0:                      # moins de 0,5 Mo/h : stable
        return None if reste > 0 else (f"⚠️ La mémoire du processus ({suite[-1]['processus_mo']} Mo) dépasse "
                                       f"{SEUIL_SATURATION:.0%} de la mémoire du serveur : redémarrage conseillé.")
    heures = reste / pente
    if heures > horizon_h:
        return None
    return (f"📈 La mémoire du processus monte de {pente:.0f} Mo par heure depuis le redémarrage "
            f"({suite[-1]['processus_mo']} Mo) : {SEUIL_SATURATION:.0%} de la mémoire du serveur serait atteint dans "
            f"environ {heures:.0f} h (risque d'erreur 502). Pistes : index de lecture, cerveaux en cache, redémarrage.")


def lignes_sante(s):
    """La santé en phrases courtes, pour l'administration."""
    age = s["age_s"]
    lignes = [f"Mémoire du processus : **{s['processus_mo']} Mo** (pic {s['processus_pic_mo']} Mo) ; mémoire libre du "
              f"serveur : {s['memoire_disponible_mo']} Mo sur {s['memoire_totale_mo']} Mo.",
              f"Disque libre : {s['disque_libre_go']} Go sur {s['disque_total_go']} Go.",
              (f"Serveur démarré il y a {age / 3600:.1f} h" if age else "Âge du serveur inconnu")
              + f" ; {s['fils']} fil(s) d'exécution ; Python {s['python']}.",
              "Modules lourds chargés : " + (", ".join(n for n, ok in s["modules_lourds"].items() if ok) or "aucun")
              + ".",
              f"Cerveaux d'école en mémoire : {len(s['cerveaux_en_cache'])}"
              + (f" ({', '.join(s['cerveaux_en_cache'][:8])}{'…' if len(s['cerveaux_en_cache']) > 8 else ''})"
                 if s["cerveaux_en_cache"] else "") + ".",
              "Index de lecture : " + (f"{s['passages_indexes']} passages, environ {s.get('index_mo')} Mo." if s["passages_indexes"] is not None
                                       else "pas encore construit.")]
    if s["memoire_totale_mo"] and s["memoire_disponible_mo"] < 0.15 * s["memoire_totale_mo"]:
        lignes.insert(0, "⚠️ Moins de 15 % de mémoire libre : risque d'arrêt du serveur (erreur 502).")
    return lignes


if __name__ == "__main__":
    from .memoire import Memoire
    from .partage import adresse_memoire
    action, chemin = sys.argv[1], sys.argv[2]
    m = Memoire(adresse_memoire())
    if action == "exporter":
        octets, bilan = exporter(m)
        with open(chemin, "wb") as f:
            f.write(octets)
        print(f"{sum(bilan.values())} lignes, {len(octets) / 1e6:.1f} Mo → {chemin}")
    elif action == "restaurer":
        with open(chemin, "rb") as f:
            print(restaurer(m, f.read()))
