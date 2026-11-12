"""
La mémoire de lecture d'IA AISSA : ce qu'elle lit, elle le garde mot pour mot, et elle sait le retrouver.

- Découper : chaque livre ou document lu est rangé en passages d'environ 900 caractères (coupés entre deux phrases),
  dans la base de données (durable avec MEMOIRE_URL).
- Retrouver : pour une question, un index BM25 (le classement des moteurs de recherche) sur les mots et les
  morceaux de mots désigne les passages les plus proches ; elle en extrait les phrases qui répondent, et cite le
  document. Plusieurs documents (ex. CGI 2021 et CGI 2026) : un passage par document, pour comparer.
- S'examiner : un examen de lecture tire des phrases de ses lectures, en cache un mot-clé, et vérifie qu'elle
  retrouve le bon passage et le mot caché. Le score est gardé : on suit ce qu'elle a vraiment retenu.
"""

import collections
from array import array
import json
import math
import random
import re
import time

from .ecole import mots

TAILLE_PASSAGE = 900
VIDES = set("""le la les de des du un une et en au aux pour par sur dans avec sans sont est été être ce cette ces son sa
ses leur leurs qui que quoi dont plus moins ainsi comme mais il ils elle elles nous vous on se ne pas ou où entre tout
tous toute toutes peut doit être été article articles alinéa the of and to in is are for with quel quelle quels quelles
comment combien pourquoi quand evolution historique entre depuis jusqu dis moi explique""".split())
SYNONYMES = {"tva": "taxe valeur ajoutee", "is": "impot societes", "ir": "impot revenu", "cnss": "securite sociale",
             "cgi": "code general impots", "sarl": "societe responsabilite limitee"}
COMMUN = ("IA AISSA", "Bibliothèque")      # savoir commun : lu seule sur le web, ou déposé par l'administrateur


def decouper(texte, taille=TAILLE_PASSAGE):
    """Passages d'environ `taille` caractères, coupés entre deux phrases (ou deux articles de loi)."""
    texte = " ".join(texte.split())
    phrases = re.split(r"(?<=[.;:!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9«(])|(?=\bArticle\s+\d)", texte)
    passages, courant = [], ""
    for p in phrases:
        if courant and len(courant) + len(p) > taille:
            passages.append(courant.strip())
            courant = ""
        courant += " " + p
    if courant.strip():
        passages.append(courant.strip())
    return [p for p in passages if len(p) > 40]


def jetons(texte):
    m = []
    for x in mots(texte):
        m += mots(SYNONYMES[x]) if x in SYNONYMES else [x]
    m = [x for x in m if x not in VIDES and (len(x) > 2 or x.isdigit())]
    return m + [f"<{x[:5]}" for x in m if len(x) > 6]          # racines : « exonérée » ~ « exonération »


class Index:
    """BM25 sur les passages : [(id, utilisateur, source, numero, texte)].
    Index inversé compact (mot → tableaux de numéros de passage et de fréquences) : environ 10 fois moins de mémoire
    qu'un compteur de mots par passage, ce qui compte quand sa bibliothèque grandit chaque jour (le serveur en ligne
    a peu de mémoire). Les scores sont calculés d'un bloc avec numpy ; les mots retrouvés ne sont recomptés que pour
    les meilleurs passages."""

    def __init__(self, lignes, k1=1.4, b=0.75):
        import numpy as np
        self.k1, self.b = k1, b
        self.champs = ("id", "utilisateur", "source", "numero")
        self.meta = [tuple(l[c] for c in self.champs) for l in lignes]
        self.textes = [l["texte"] for l in lignes]
        postings = collections.defaultdict(lambda: (array("I"), array("H")))
        longueurs = array("I")
        for i, texte in enumerate(self.textes):
            compte = collections.Counter(jetons(texte))
            longueurs.append(sum(compte.values()))
            for t, f in compte.items():
                ids, tfs = postings[t]
                ids.append(i)
                tfs.append(min(f, 65535))
        n = len(self.textes)
        self.longueurs = np.frombuffer(longueurs, dtype=np.uint32).astype(np.float32) if n else np.zeros(0, np.float32)
        self.moyenne = float(self.longueurs.mean()) if n else 0.0
        self.postings = {t: (np.frombuffer(ids, dtype=np.uint32), np.frombuffer(tfs, dtype=np.uint16))
                         for t, (ids, tfs) in postings.items()}
        self.idf = {t: math.log(1 + (n - len(ids) + .5) / (len(ids) + .5)) for t, (ids, _) in self.postings.items()}

    def __len__(self):
        return len(self.textes)

    def chercher(self, question, n=5):
        import numpy as np
        q = [t for t in set(jetons(question)) if t in self.idf]
        if not q or not self.textes:
            return []
        scores = np.zeros(len(self.textes), dtype=np.float32)
        normes = self.k1 * (1 - self.b + self.b * self.longueurs / max(self.moyenne, 1e-9))
        for t in q:
            ids, tfs = self.postings[t]
            f = tfs.astype(np.float32)
            scores[ids] += self.idf[t] * f * (self.k1 + 1) / (f + normes[ids])
        touches = np.flatnonzero(scores)
        meilleurs = touches[np.argsort(-scores[touches], kind="stable")[:n]]
        maximum = sum(self.idf[t] for t in q) * (self.k1 + 1) or 1
        entiers = [t for t in q if not t.startswith("<")]
        resultats = []
        for i in meilleurs:
            presents = set(jetons(self.textes[i]))
            s = float(scores[i])
            resultats.append({**dict(zip(self.champs, self.meta[i])), "texte": self.textes[i], "score": round(s, 3),
                              "couverture": round(s / maximum, 3),
                              "mots_trouves": sum(1 for t in q if t in presents) / max(1, len(q)),
                              "mots_entiers": sum(1 for t in entiers if t in presents),
                              "part_entiers": sum(1 for t in entiers if t in presents) / max(1, len(entiers))})
        return resultats


_INDEX = {}


def index(memoire, utilisateur=None):
    """L'index des passages visibles par la personne (ses documents + le savoir commun), refait quand ils changent."""
    visibles = None if utilisateur is None else {utilisateur, *COMMUN}
    comptes = memoire.compter_passages()
    signature = (id(memoire), tuple(sorted(visibles or [])), sum(c["passages"] for c in comptes), len(comptes))
    if _INDEX.get("signature") != signature:
        _INDEX.update(signature=signature, index=Index(memoire.passages(visibles)))
    return _INDEX["index"]


def phrases_utiles(passage, question, n=3):
    """Les phrases du passage qui portent le plus de mots de la question (sans répétition)."""
    q = set(jetons(question))
    phrases, vues = [], set()
    for p in re.split(r"(?<=[.;!?])\s+", passage):
        cle = "".join(p.split()).lower()                  # même phrase, espaces près (extraction PDF)
        if len(p.strip()) > 25 and cle not in vues:
            vues.add(cle)
            phrases.append(p.strip())
    # Un mot de la question présent dans toutes les phrases (le sujet : « Japon ») compte peu ; un mot rare dans le
    # passage (« capitale ») désigne la phrase qui répond
    jetons_phrases = [set(jetons(p)) for p in phrases]
    frequence = collections.Counter(j for js in jetons_phrases for j in js & q)
    poids = {j: math.log(1 + len(phrases) / f) for j, f in frequence.items()}
    notes = {p: sum(poids[j] for j in js & q) for p, js in zip(phrases, jetons_phrases)}
    notees = sorted(phrases, key=lambda p: -notes[p])
    return [p for p in notees[:n] if notes[p] > 0] or phrases[:1]      # la phrase qui répond en premier


ENSEMBLES = {"national", "ensemble", "total", "maroc", "tous", "toutes", "global", "total général", "royaume"}


def agregation(texte):
    """Part des étiquettes d'une ligne de tableau (« … — National, Total : … ») qui désignent un ensemble plutôt
    qu'une région ou une catégorie : « Ensemble, Total » → 1 ; « National, Casablanca » → 0,5 ; autre texte → 0."""
    etiquettes = re.findall(r" — ([^—:]+) : ", texte)
    if not etiquettes:
        return 0.0
    mots = [e.strip().lower() for e in etiquettes[-1].split(",") if e.strip() not in ("", "-")]
    return sum(m in ENSEMBLES for m in mots) / len(mots) if mots else 0.0


def avertissement_partiel(texte, question):
    """Une ligne de tableau sur une seule région ou catégorie que la question ne nomme pas : le dire, pour qu'un
    chiffre de Taza ne passe pas pour le chiffre national."""
    etiquettes = re.findall(r" — ([^—:]+) : ", texte)
    if not etiquettes or agregation(texte) == 1:
        return ""
    precises = [e.strip() for e in etiquettes[-1].split(",") if e.strip() not in ("", "-")
                and e.strip().lower() not in ENSEMBLES]
    q = set(jetons(question))
    absentes = [e for e in precises if not (set(jetons(e)) & q)]
    if not absentes:
        return ""
    return (f" _(attention : ce chiffre ne concerne que « {', '.join(absentes)} » ; ce tableau ne donne pas de total "
            "national dans ce que j'ai lu)_")


SEUIL_LECTURE = 0.45            # part des mots de la question retrouvés dans le meilleur passage


def repondre_par_lecture(question, memoire, utilisateur=None, n=6, strict=False):
    """Réponse tirée de ses lectures : un extrait par document (comparaison entre éditions), avec la source.
    Renvoie None si rien d'assez proche n'a été lu."""
    if memoire is None:
        return None
    resultats = index(memoire, utilisateur).chercher(question, n=n * 30)   # assez de lignes d'un même tableau
    seuil = 0.6 if strict else SEUIL_LECTURE
    resultats = [r for r in resultats if r["mots_trouves"] >= seuil and r["part_entiers"] >= seuil
                 and r["mots_entiers"] >= 2]          # au moins deux vrais mots de la question, pas une racine seule
    if not resultats:
        return None
    par_source = {}
    for r in resultats:                                   # le meilleur passage de chaque document
        meilleur = par_source.setdefault(r["source"], r)
        if r["mots_trouves"] >= meilleur["mots_trouves"] and agregation(r["texte"]) > agregation(meilleur["texte"]):
            par_source[r["source"]] = r                   # question qui ne nomme ni région ni catégorie : l'ensemble
    annees = set(re.findall(r"\b(?:19|20)\d\d\b", question))
    datees = {src: r for src, r in par_source.items() if annees & set(re.findall(r"(?:19|20)\d\d", src))}
    if datees:                                             # « en 2026 », « de 2021 à 2026 » : les éditions de ces années
        par_source = datees
    choisis = sorted(par_source.values(), key=lambda r: r["source"])[:n] if len(par_source) > 1 else list(par_source.values())
    lignes = [f"**{r['source']}** (passage {r['numero'] + 1}) : « {' '.join(phrases_utiles(r['texte'], question))} »"
              + avertissement_partiel(r["texte"], question) for r in choisis]
    confiance = round(min(0.95, max(r["mots_trouves"] for r in choisis)), 3)
    return {"reponse": "\n\n".join(lignes), "sources": [r["source"] for r in choisis], "confiance": confiance}


# ==========================================
# Examen de lecture : ce qu'elle a vraiment retenu
# ==========================================
def examen_lecture(memoire, n=20, rng=None):
    """Tire n phrases de ses lectures, cache un mot-clé (de préférence un nombre ou un mot rare), lui pose la phrase
    à trous, et vérifie qu'elle retrouve le passage d'origine et le mot caché. Le résultat est gardé."""
    rng = rng or random.Random()
    idx = index(memoire)                    # les passages sont pris dans l'index : la bibliothèque n'est lue qu'une fois
    if not len(idx):
        return {"questions": 0, "passage_retrouve": 0, "mot_retrouve": 0, "score": 0.0, "exemples": []}
    retrouves = mots_ok = 0
    exemples = []
    for i in rng.sample(range(len(idx)), min(n, len(idx))):
        ligne = {**dict(zip(idx.champs, idx.meta[i])), "texte": idx.textes[i]}
        phrases = [p for p in re.split(r"(?<=[.;!?])\s+", ligne["texte"]) if len(p.split()) >= 8]
        if not phrases:
            continue
        phrase = rng.choice(phrases)
        candidats = [m for m in re.findall(r"\b\w[\w%,.-]*\b", phrase) if len(m) > 6 or re.search(r"\d", m)]
        if not candidats:
            continue
        cache = max(candidats, key=lambda m: (bool(re.search(r"\d", m)), len(m)))
        question = phrase.replace(cache, "____", 1)
        trouve = idx.chercher(question, n=1)
        bon_passage = bool(trouve) and trouve[0]["id"] == ligne["id"]
        bon_mot = bool(trouve) and cache in trouve[0]["texte"]
        retrouves += bon_passage
        mots_ok += bon_mot
        exemples.append({"question": question[:200], "attendu": cache, "source": ligne["source"],
                         "passage_retrouve": bon_passage, "mot_retrouve": bon_mot})
    total = len(exemples)
    bilan = {"questions": total, "passage_retrouve": retrouves, "mot_retrouve": mots_ok,
             "score": round(mots_ok / total, 3) if total else 0.0, "exemples": exemples}
    memoire.definir_reglage(f"examen_lecture:{int(time.time() * 1000)}", json.dumps(
        {k: v for k, v in bilan.items() if k != "exemples"}))
    return bilan


def historique_examens(memoire):
    return [{"quand": int(k.split(":", 1)[1]) / 1000, **json.loads(v)}
            for k, v in sorted(memoire.reglages("examen_lecture:").items())]
