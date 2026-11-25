"""
Le temps d'ouverture de chaque page, mesuré à chaque affichage (objectif : moins de 3 secondes).

Deux mesures distinctes :
- l'affichage d'une page : du début à la fin du script Streamlit pour cette page (ce que vit chaque visiteur) ;
- le démarrage à froid du serveur : de la naissance du processus à la fin du premier affichage (imports de PyTorch,
  pandas…, payé une seule fois quand Streamlit Cloud réveille l'application).

Les affichages qui préparent une réponse au visiteur (message envoyé) sont comptés à part (« — réponse ») : leur durée
est celle de la réflexion d'IA AISSA, pas celle de l'ouverture de la page.

Alerte : quand le 95e centile des ouvertures d'une page dépasse 3 s sur les dernières 24 heures (au moins 5 mesures).
Les mesures restent en mémoire du serveur (horodatées, au plus 2 000 par page) : rien n'est écrit en base à chaque
affichage.
"""

import importlib.abc
import importlib.machinery
import os
import statistics
import sys
import threading
import time
from collections import deque

OBJECTIF_S = 3.0
GARDER = 2_000                  # par page : de quoi couvrir une journée chargée
FENETRE_ALERTE_S = 86_400       # une journée
MIN_MESURES_ALERTE = 5          # pas d'alerte sur une seule ouverture lente
SUFFIXE_REPONSE = " — réponse"
_MESURES = {}
_DEMARRAGE = {}
_COURANT = threading.local()    # le chronomètre de l'affichage en cours (un fil par session Streamlit)


def age_du_processus():
    """Secondes depuis la naissance du processus, lues dans /proc (Linux) ; None ailleurs."""
    try:
        with open("/proc/self/stat") as f:
            debut_ticks = int(f.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/uptime") as f:
            uptime = float(f.read().split()[0])
        return max(0.0, uptime - debut_ticks / os.sysconf("SC_CLK_TCK"))
    except (OSError, ValueError, IndexError):
        return None


def enregistrer(page, duree, quand=None):
    _MESURES.setdefault(page, deque(maxlen=GARDER)).append((quand or time.time(), float(duree)))
    if "secondes" not in _DEMARRAGE:                 # premier affichage depuis le démarrage du serveur
        age = age_du_processus()
        _DEMARRAGE.update(secondes=age, page=page)


class Chrono:
    """with Chrono("IA AISSA"): … — mesure l'affichage de la page, même si elle s'interrompt (rerun, switch_page)."""

    def __init__(self, page):
        self.page = page

    def __enter__(self):
        self.debut = time.perf_counter()
        self.reponse = False
        _COURANT.chrono = self
        return self

    def __exit__(self, *exc):
        _COURANT.chrono = None
        enregistrer(self.page + (SUFFIXE_REPONSE if self.reponse else ""), time.perf_counter() - self.debut)
        return False


def marquer_reponse():
    """Cet affichage prépare une réponse à un message : il est compté à part (pas dans l'ouverture de la page)."""
    chrono = getattr(_COURANT, "chrono", None)
    if chrono is not None:
        chrono.reponse = True


def centile_95(valeurs):
    v = sorted(valeurs)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def demarrage_a_froid():
    return _DEMARRAGE.get("secondes")


def tableau():
    """Par page : nombre d'affichages, médiane, 95e centile, maximum, et respect de l'objectif."""
    lignes = []
    for page, d in sorted(_MESURES.items()):
        v = sorted(duree for _, duree in d)
        p95 = centile_95(v)
        lignes.append({"Page": page, "Affichages mesurés": len(v), "Médiane (s)": round(statistics.median(v), 2),
                       "95e centile (s)": round(p95, 2), "Maximum (s)": round(v[-1], 2),
                       "Objectif < 3 s": "—" if page.endswith(SUFFIXE_REPONSE) else "✅" if p95 < OBJECTIF_S else "⚠️"})
    import pandas as pd                               # au premier tableau seulement : pas au démarrage
    return pd.DataFrame(lignes)


# ==========================================
# Temps d'import des gros modules (mesuré au premier import, dans le processus du serveur)
# ==========================================
SURVEILLES = ("pandas", "numpy", "pyarrow", "sqlalchemy", "streamlit", "plotly", "openpyxl", "faster_whisper", "torch",
              "cv2", "openai", "anthropic", "pypdf", "fpdf", "reportlab", "edge_tts", "gtts")
SEUIL_IMPORT_S = 0.3            # au-delà, le module doit être importé à la demande (paresseux)
_IMPORTS = {}                   # module → (secondes, horodatage)
_local = threading.local()


class _Chronometre(importlib.abc.MetaPathFinder):
    """Chronomètre l'exécution des modules surveillés (sous-modules compris : temps cumulé)."""

    def find_spec(self, nom, chemin, cible=None):
        if nom not in SURVEILLES or nom in _IMPORTS or getattr(_local, "actif", False):
            return None
        _local.actif = True
        try:
            spec = importlib.machinery.PathFinder.find_spec(nom, chemin, cible)
        finally:
            _local.actif = False
        if spec is None or spec.loader is None or not hasattr(spec.loader, "exec_module"):
            return None
        executer = spec.loader.exec_module

        def exec_module(module):
            debut = time.perf_counter()
            try:
                executer(module)
            finally:
                _IMPORTS[nom] = (time.perf_counter() - debut, time.time())
        spec.loader.exec_module = exec_module
        return spec


def surveiller_imports():
    """Installe le chronomètre (une seule fois) ; à appeler avant les imports à mesurer."""
    if not any(isinstance(f, _Chronometre) for f in sys.meta_path):
        sys.meta_path.insert(0, _Chronometre())


def temps_imports():
    """[{module, état, secondes}] : mesuré au premier import, « déjà chargé » s'il l'était avant le chronomètre,
    « pas encore chargé » s'il attend son premier usage (paresseux)."""
    lignes = []
    for nom in SURVEILLES:
        if nom in _IMPORTS:
            s = _IMPORTS[nom][0]
            lignes.append({"Module": nom, "Import (s)": round(s, 2),
                           "État": "⚠️ lent (> 0,3 s)" if s > SEUIL_IMPORT_S else "✅ rapide"})
        elif nom in sys.modules:
            lignes.append({"Module": nom, "Import (s)": None, "État": "chargé avant la mesure (Streamlit)"})
        else:
            lignes.append({"Module": nom, "Import (s)": None, "État": "💤 pas encore chargé (à la demande)"})
    return sorted(lignes, key=lambda l: -(l["Import (s)"] or 0))


# ==========================================
# Résumé du soir, gardé en base : la tendance d'un redémarrage du serveur à l'autre
# ==========================================
CLE_RESUMES = "chrono:resumes"
HEURE_DU_SOIR = 20               # heure du Maroc à partir de laquelle la journée est résumée
GARDER_JOURS = 90


# Heure légale du Maroc : GMT+1 (décret 2.18.855 de 2018, retour à GMT pendant le Ramadan) jusqu'au 20/09/2026 à 2 h,
# puis GMT (décret 2.26.530, Bulletin officiel du 29/06/2026 ; vérifié le 25/11/2026 dans Médias24, Hespress, Le Brief).
# La base des fuseaux du serveur peut ignorer ce changement (versions antérieures à 2026e) : elle est alors corrigée.
RETOUR_GMT = 1_789_866_000       # 20/09/2026 à 2 h du matin (GMT+1), soit 01:00 UTC


def heure_du_maroc(maintenant=None):
    import datetime
    instant = maintenant or time.time()
    try:
        from zoneinfo import ZoneInfo
        local = datetime.datetime.fromtimestamp(instant, ZoneInfo("Africa/Casablanca"))
    except Exception:                                   # sans base des fuseaux
        local = None
    if instant >= RETOUR_GMT:
        if local is None or local.utcoffset() != datetime.timedelta(0):   # base trop ancienne : GMT, sans exception
            local = datetime.datetime.fromtimestamp(instant, datetime.timezone.utc)
    elif local is None:
        local = datetime.datetime.fromtimestamp(instant, datetime.timezone(datetime.timedelta(hours=1)))
    return local


def resume(maintenant=None, fenetre_s=FENETRE_ALERTE_S):
    """Par page (réponses comprises, à part) : nombre d'affichages, médiane, 95e centile et maximum sur la fenêtre."""
    maintenant = maintenant or time.time()
    pages = {}
    for page, d in sorted(_MESURES.items()):
        v = sorted(duree for quand, duree in d if maintenant - quand <= fenetre_s)
        if v:
            pages[page] = {"n": len(v), "mediane": round(statistics.median(v), 2), "p95": round(centile_95(v), 2),
                           "max": round(v[-1], 2)}
    return pages


def resumes(memoire):
    import json
    brut = memoire.reglage(CLE_RESUMES) if memoire is not None else None
    return json.loads(brut) if brut else {}


def garder_resume_du_soir(memoire, maintenant=None):
    """À chaque visite : après HEURE_DU_SOIR (heure du Maroc), garde une fois par jour le résumé des dernières 24 h,
    avec l'âge du serveur et son démarrage à froid. Renvoie la date gardée, ou None (déjà fait, trop tôt, rien mesuré)."""
    import json
    local = heure_du_maroc(maintenant)
    if local.hour < HEURE_DU_SOIR:
        return None
    jour = local.date().isoformat()
    tous = resumes(memoire)
    if jour in tous:
        return None
    pages = resume(maintenant)
    if not pages:
        return None
    age = age_du_processus()
    tous[jour] = {"pages": pages, "serveur_age_h": round(age / 3600, 1) if age else None,
                  "demarrage_a_froid_s": round(_DEMARRAGE["secondes"], 1) if _DEMARRAGE.get("secondes") else None}
    for vieux in sorted(tous)[:-GARDER_JOURS]:
        del tous[vieux]
    memoire.definir_reglage(CLE_RESUMES, json.dumps(tous, ensure_ascii=False))
    return jour


def tendance(memoire, jours=14):
    """Les résumés gardés, une ligne par jour et par page (les plus récents d'abord), pour l'administration."""
    lignes = []
    for jour, r in sorted(resumes(memoire).items(), reverse=True)[:jours]:
        for page, m in r["pages"].items():
            lignes.append({"Jour": jour, "Page": page, "Affichages": m["n"], "Médiane (s)": m["mediane"],
                           "95e centile (s)": m["p95"], "Maximum (s)": m["max"],
                           "Serveur démarré depuis (h)": r.get("serveur_age_h"),
                           "Démarrage à froid (s)": r.get("demarrage_a_froid_s")})
    return lignes


def alertes(maintenant=None):
    """Pages dont le 95e centile d'ouverture dépasse l'objectif sur les dernières 24 heures (réponses exclues)."""
    maintenant = maintenant or time.time()
    messages = []
    for page, d in sorted(_MESURES.items()):
        if page.endswith(SUFFIXE_REPONSE):
            continue
        jour = [duree for quand, duree in d if maintenant - quand <= FENETRE_ALERTE_S]
        if len(jour) >= MIN_MESURES_ALERTE and (p95 := centile_95(jour)) > OBJECTIF_S:
            messages.append(f"🐢 « {page} » : 95e centile d'ouverture de {p95:.1f} s sur les dernières 24 heures "
                            f"({len(jour)} ouvertures, objectif < {OBJECTIF_S:.0f} s). Pistes : serveur réveillé "
                            "récemment, tâches de fond (broutage, révisions), mémoire du serveur.")
    return messages


def reinitialiser():
    _MESURES.clear()
    _DEMARRAGE.clear()
