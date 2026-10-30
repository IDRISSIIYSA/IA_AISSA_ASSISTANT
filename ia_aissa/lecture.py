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
    """BM25 sur les passages : [(id, utilisateur, source, numero, texte)]."""

    def __init__(self, lignes, k1=1.4, b=0.75):
        self.lignes, self.k1, self.b = lignes, k1, b
        self.docs = [collections.Counter(jetons(l["texte"])) for l in lignes]
        self.longueurs = [sum(d.values()) for d in self.docs]
        self.moyenne = sum(self.longueurs) / max(1, len(self.docs))
        frequences = collections.Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + .5) / (f + .5)) for t, f in frequences.items()}
        self.index = collections.defaultdict(list)
        for i, d in enumerate(self.docs):
            for t in d:
                self.index[t].append(i)

    def chercher(self, question, n=5):
        q = [t for t in set(jetons(question)) if t in self.idf]
        scores = collections.defaultdict(float)
        for t in q:
            for i in self.index[t]:
                f = self.docs[i][t]
                scores[i] += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.longueurs[i] / self.moyenne))
        maximum = sum(self.idf[t] for t in q) * (self.k1 + 1) or 1
        meilleurs = sorted(scores.items(), key=lambda e: -e[1])[:n]
        return [{**self.lignes[i], "score": round(s, 3), "couverture": round(s / maximum, 3),
                 "mots_trouves": sum(1 for t in q if t in self.docs[i]) / max(1, len(q))} for i, s in meilleurs]


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
    notees = sorted(phrases, key=lambda p: -len(q & set(jetons(p))))
    gardees = [p for p in notees[:n] if q & set(jetons(p))]
    return [p for p in phrases if p in gardees] or phrases[:1]


SEUIL_LECTURE = 0.45            # part des mots de la question retrouvés dans le meilleur passage


def repondre_par_lecture(question, memoire, utilisateur=None, n=6):
    """Réponse tirée de ses lectures : un extrait par document (comparaison entre éditions), avec la source.
    Renvoie None si rien d'assez proche n'a été lu."""
    if memoire is None:
        return None
    resultats = index(memoire, utilisateur).chercher(question, n=n * 6)
    resultats = [r for r in resultats if r["mots_trouves"] >= SEUIL_LECTURE]
    if not resultats:
        return None
    par_source = {}
    for r in resultats:                                   # le meilleur passage de chaque document
        par_source.setdefault(r["source"], r)
    annees = set(re.findall(r"\b(?:19|20)\d\d\b", question))
    datees = {src: r for src, r in par_source.items() if annees & set(re.findall(r"(?:19|20)\d\d", src))}
    if datees:                                             # « en 2026 », « de 2021 à 2026 » : les éditions de ces années
        par_source = datees
    choisis = sorted(par_source.values(), key=lambda r: r["source"])[:n] if len(par_source) > 1 else [resultats[0]]
    lignes = [f"**{r['source']}** (passage {r['numero'] + 1}) : « {' '.join(phrases_utiles(r['texte'], question))} »"
              for r in choisis]
    confiance = round(min(0.95, max(r["mots_trouves"] for r in choisis)), 3)
    return {"reponse": "\n\n".join(lignes), "sources": [r["source"] for r in choisis], "confiance": confiance}


# ==========================================
# Examen de lecture : ce qu'elle a vraiment retenu
# ==========================================
def examen_lecture(memoire, n=20, rng=None):
    """Tire n phrases de ses lectures, cache un mot-clé (de préférence un nombre ou un mot rare), lui pose la phrase
    à trous, et vérifie qu'elle retrouve le passage d'origine et le mot caché. Le résultat est gardé."""
    rng = rng or random.Random()
    lignes = memoire.passages()
    if not lignes:
        return {"questions": 0, "passage_retrouve": 0, "mot_retrouve": 0, "score": 0.0, "exemples": []}
    idx = index(memoire)
    retrouves = mots_ok = 0
    exemples = []
    for ligne in rng.sample(lignes, min(n, len(lignes))):
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
