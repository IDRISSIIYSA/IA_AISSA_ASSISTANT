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
    cerveaux, passages = [], None
    if "ia_aissa.ecole" in sys.modules:
        cerveaux = sorted(sys.modules["ia_aissa.ecole"]._CACHE)
    if "ia_aissa.lecture" in sys.modules:
        index = sys.modules["ia_aissa.lecture"]._INDEX.get("index")
        passages = len(index) if index is not None else None
    return {
        "memoire_totale_mo": round(mem.get("MemTotal", 0)), "memoire_disponible_mo": round(mem.get("MemAvailable", 0)),
        "processus_mo": round(proc.get("VmRSS", 0)), "processus_pic_mo": round(proc.get("VmHWM", 0)),
        "disque_libre_go": round(disque.free / 1e9, 1), "disque_total_go": round(disque.total / 1e9, 1),
        "age_s": chrono.age_du_processus(), "fils": threading.active_count(), "modules_lourds": lourds,
        "cerveaux_en_cache": cerveaux, "passages_indexes": passages,
        "python": sys.version.split()[0],
    }


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
              "Index de lecture : " + (f"{s['passages_indexes']} passages." if s["passages_indexes"] is not None
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
