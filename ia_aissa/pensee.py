"""
La pensée propre d'IA AISSA : répondre avec son propre cerveau, sans moteur externe ni clé API.

Elle raisonne en plusieurs étapes, et montre son raisonnement :
1. Comprendre : de quoi parle-t-on (salutation, calcul, question de cours) et dans quelle langue.
2. Calculer : si la question contient des chiffres (paie, IR, IS, TVA, crédit, opération), elle calcule elle-même
   avec ses barèmes marocains.
3. Se souvenir par analogie (mémoire associative) : elle compare la question à tout ce qu'elle connaît (les
   formulations de toutes ses matières et les corrections qu'on lui a apprises) et retient la plus proche.
4. Consulter ses cerveaux d'école : l'aiguilleur choisit la matière, le cerveau de la matière répond.
5. Confronter (Dalio) : si analogie et cerveaux sont d'accord, elle est sûre ; sinon elle le dit et donne
   l'autre hypothèse. Sous le seuil, elle avoue ne pas savoir (et note la lacune pour l'étudier).
6. Lire : elle ajoute ce que sa bibliothèque (livres et pages digérés) dit de proche.
"""

import ast
import collections
import math
import operator
import re

from . import connaissances as K
from .ecole import MATIERES, PAR_CLE, SEUIL_CONFIANCE, mots, repondre, repondre_automatiquement

HORS_ANALOGIE = {"langues", "matiere_scolaire", "orientation"}
VIDES = set("le la les de des du un une et au aux pour par en sur dans mon ma mes ton ta je tu il elle qui que "
            "quoi est ce cet cette dyal dial li ana nta wach chno chnou".split())
SEUIL_ANALOGIE = 0.45          # au-dessus : l'analogie est assez proche pour répondre
SEUIL_PISTE = 0.28             # entre les deux : une piste, donnée avec prudence


# ==========================================
# Mémoire associative (TF-IDF sur mots, paires de mots et morceaux de mots)
# ==========================================
def jetons(texte):
    m = [x for x in mots(texte) if x not in VIDES]
    j = m + [a + "_" + b for a, b in zip(m, m[1:])]
    for x in m:                       # morceaux de 4 lettres : « lkoutoubia » ressemble à « koutoubia »
        x = f"<{x}>"
        j += [x[i:i + 4] for i in range(len(x) - 3)]
    return j


class MemoireAssociative:
    def __init__(self, souvenirs):
        """souvenirs : liste de (texte, clé de matière, réponse)."""
        self.souvenirs = souvenirs
        docs = [jetons(t) for t, _, _ in souvenirs]
        n = len(docs)
        frequences = collections.Counter(x for d in docs for x in set(d))
        self.idf = {k: math.log((n + 1) / (v + 1)) + 1 for k, v in frequences.items()}
        self.vecteurs = [self._vecteur(d) for d in docs]
        self.index = collections.defaultdict(list)          # jeton -> documents qui le contiennent
        for i, v in enumerate(self.vecteurs):
            for k in v:
                self.index[k].append(i)

    def _vecteur(self, js):
        c = collections.Counter(js)
        v = {k: n * self.idf[k] for k, n in c.items() if k in self.idf}
        norme = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {k: x / norme for k, x in v.items()}

    def chercher(self, question, n=3):
        """Les souvenirs les plus proches, une seule fois par réponse : [{cle, reponse, score, exemple}]."""
        q = self._vecteur(jetons(question))
        scores = collections.defaultdict(float)
        for k, x in q.items():
            for i in self.index.get(k, ()):
                scores[i] += x * self.vecteurs[i][k]
        resultats, vus = [], set()
        for i, s in sorted(scores.items(), key=lambda e: -e[1]):
            texte, cle, reponse = self.souvenirs[i]
            if (cle, reponse) in vus:
                continue
            vus.add((cle, reponse))
            resultats.append({"cle": cle, "reponse": reponse, "score": round(s, 3), "exemple": texte})
            if len(resultats) == n:
                break
        return resultats


_CACHE = {}


def memoire_associative(memoire=None):
    """Tout ce qu'IA AISSA connaît : formulations de ses matières + corrections apprises (refaite quand elles changent)."""
    corrections = memoire.corrections_de() if memoire is not None else []
    cle_cache = (id(memoire), len(corrections))
    if _CACHE.get("cle") != cle_cache:
        souvenirs = [(f, m.cle, a) for m in MATIERES if m.exemples and m.cle not in HORS_ANALOGIE
                     for a, formes in zip(m.actions, m.exemples) for f in formes]
        souvenirs += [(c["question"], c["matiere"], c["bonne_reponse"]) for c in corrections
                      if c["matiere"] in PAR_CLE and c["matiere"] not in HORS_ANALOGIE
                      and c["bonne_reponse"] in PAR_CLE[c["matiere"]].actions]
        _CACHE.update(cle=cle_cache, memoire=MemoireAssociative(souvenirs))
    return _CACHE["memoire"]


# ==========================================
# Petites conversations
# ==========================================
CONVERSATION = [
    (re.compile(r"^\s*(salut|bonjour|bonsoir|salam|slm|cc|coucou|hello|hi|السلام|سلام|ahlan|marhba)\b", re.I),
     "Salam ! Labas 3lik ? Je suis là. Pose-moi une question de gestion, de fiscalité, d'école… ou donne-moi des chiffres."),
    (re.compile(r"\b(merci|chokran|shukran|شكرا|thanks)\b", re.I), "Bla jmil ! Avec plaisir, je suis là quand tu veux."),
    (re.compile(r"(qui es[- ]tu|t'es qui|chkoun nta|شكون نتا|ton nom|smitek)", re.I),
     "Je suis IA AISSA, un petit alien marocain né vide et qui apprend seul : 74 matières à l'école, des livres que je "
     "digère, et tout ce que tu m'apprends. Je pense avec mes propres cerveaux, et avec un grand moteur si tu me "
     "donnes une clé API."),
    (re.compile(r"(comment (ça|ca) va|labas|kidayr|kidayra|cava|ça va)", re.I),
     "Hamdoullah, labas ! Mes cerveaux tournent bien. Et toi ?"),
]


# ==========================================
# Calculs à partir des chiffres de la question
# ==========================================
NOMBRE = r"(\d[\d\s.,]*\d|\d)(\s*(k|mille|alf|ألف))?"
OPERATEURS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
              ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


def nombres(texte):
    """« 8 000 dh », « 8000,50 », « 8k », « 8 mille » -> [8000.0, …]."""
    valeurs = []
    for m in re.finditer(NOMBRE, texte, re.I):
        brut = re.sub(r"\s", "", m.group(1))
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", brut):
            brut = brut.replace(".", "")
        brut = brut.replace(",", ".")
        try:
            v = float(brut)
        except ValueError:
            continue
        valeurs.append(v * 1000 if m.group(3) else v)
    return valeurs


def _evaluer(noeud):
    if isinstance(noeud, ast.Expression):
        return _evaluer(noeud.body)
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)):
        return noeud.value
    if isinstance(noeud, ast.BinOp) and type(noeud.op) in OPERATEURS:
        gauche, droite = _evaluer(noeud.left), _evaluer(noeud.right)
        if isinstance(noeud.op, ast.Pow) and abs(droite) > 100:
            raise ValueError("puissance trop grande")
        return OPERATEURS[type(noeud.op)](gauche, droite)
    if isinstance(noeud, ast.UnaryOp) and type(noeud.op) in OPERATEURS:
        return OPERATEURS[type(noeud.op)](_evaluer(noeud.operand))
    raise ValueError("expression non autorisée")


def montant(v):
    return f"{v:,.2f}".replace(",", " ").replace(".00", "") + " DH"


def calculer(texte):
    """Renvoie (réponse, étapes) si la question est un calcul qu'IA AISSA sait faire, sinon None."""
    t = texte.lower()
    expression = re.sub(r"[x×]", "*", re.sub(r"÷", "/", t)).replace("^", "**")
    expression = re.sub(r"(combien (fait|font)|calcule[rz]?|=|\?|ch7al|chhal)", "", expression).strip()
    if re.fullmatch(r"[\d\s.,+\-*/()]+", expression) and re.search(r"\d\s*[+\-*/]", expression):
        try:
            valeur = _evaluer(ast.parse(expression.replace(",", "."), mode="eval"))
            return f"**{expression.strip()} = {valeur:,.6g}**".replace(",", " "), ["Opération reconnue, calculée pas à pas."]
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError):
            pass
    valeurs = [v for v in nombres(t) if v > 0]
    if not valeurs:
        return None
    if re.search(r"(salaire|brut|paie|salaire net|khlass|khalss|chhar)", t) and not re.search(r"\bir\b|impôt sur le revenu", t):
        v = max(valeurs)
        p = K.calculer_paie(v)
        return (f"Pour un salaire brut mensuel de **{montant(v)}** : CNSS {montant(p['cnss_salarie'])}, AMO "
                f"{montant(p['amo_salarie'])}, frais professionnels {montant(p['frais_professionnels'])}, IR "
                f"{montant(p['ir'])} → **salaire net {montant(p['salaire_net'])}** (charges patronales "
                f"{montant(p['charges_patronales'])}). _{p['remarque']}_",
                ["Chiffre trouvé : salaire brut mensuel.", "Barème de paie marocain : CNSS, AMO, frais professionnels, IR."])
    if re.search(r"(\bir\b|impôt sur le revenu|dariba 3la (salaire|dakhl))", t):
        v = max(valeurs)
        annuel = v * 12 if re.search(r"(mois|mensuel|chhar)", t) else v
        r = K.calculer_ir(annuel)
        return (f"Revenu net imposable annuel **{montant(annuel)}** : taux marginal {r['taux_marginal']:.0%}, somme à "
                f"déduire {montant(r['somme_a_deduire'])} → **IR annuel {montant(r['ir_annuel'])}** "
                f"({montant(r['ir_mensuel'])} par mois, taux moyen {r['taux_moyen']:.1%}).",
                ["Chiffre trouvé : revenu" + (" mensuel, multiplié par 12." if annuel != v else " annuel."),
                 "Barème IR marocain (tranche, taux marginal, somme à déduire)."])
    if re.search(r"(\bis\b|impôt sur les sociétés|bénéfice|benefice|rb7)", t):
        v = max(valeurs)
        r = K.calculer_is(v)
        return (f"Bénéfice fiscal **{montant(v)}** → **IS {montant(r['is'])}** (taux {r['taux']:.0%}). _{r['remarque']}_",
                ["Chiffre trouvé : bénéfice fiscal.", "Taux d'IS marocain."])
    if re.search(r"\b(tva|ttc|ht)\b", t):
        v = max(valeurs)
        taux = next((x / 100 for x in valeurs if x in (7, 10, 14, 20) and x != v), None)
        if taux is None:
            regime = repondre("tva", texte, top=1)[0]
            taux = {"20 %": 0.2, "10 %": 0.1}.get(regime["reponse"], 0.0 if "xon" in regime["reponse"] else 0.2)
        r = K.calculer_tva(v, taux, "ttc" in t)
        return (f"Montant **{montant(v)}** {'TTC' if 'ttc' in t else 'HT'} au taux de {taux:.0%} : HT {montant(r['ht'])}, "
                f"TVA {montant(r['tva'])}, **TTC {montant(r['ttc'])}**.",
                ["Chiffre trouvé : montant.", f"Taux retenu : {taux:.0%} (donné, ou trouvé par mon cerveau TVA)."])
    if re.search(r"(crédit|credit|prêt|pret|kredi|emprunt)", t) and len(valeurs) >= 3:
        capital = max(valeurs)
        taux = next((x for x in valeurs if x < 30 and "%" in t), None)
        duree = next((x for x in valeurs if x != capital and x != taux), None)
        if taux and duree:
            mois = duree * 12 if re.search(r"(an|ans|année|years|3am|عام)", t) else duree
            r = K.mensualite_credit(capital, taux / 100, int(mois))
            return (f"Crédit de **{montant(capital)}** à {taux:g} % sur {int(mois)} mois → **mensualité "
                    f"{montant(r['mensualite'])}**, coût total du crédit {montant(r['cout_total_credit'])}.",
                    ["Chiffres trouvés : capital, taux, durée.", "Formule de l'annuité constante."])
    return None


# ==========================================
# Penser
# ==========================================
def penser(texte, memoire=None):
    """Réponse d'IA AISSA avec ses propres cerveaux. Renvoie (réponse en markdown, étapes du raisonnement, confiance)."""
    for motif, reponse in CONVERSATION:
        if motif.search(texte) and len(texte.split()) <= 6:
            return reponse, ["Petite conversation reconnue."], 0.95

    calcul = calculer(texte)
    if calcul:
        reponse, etapes = calcul
        return reponse, ["Je repère des chiffres et un calcul que je sais faire."] + etapes, 0.9

    analogies = memoire_associative(memoire).chercher(texte, n=3)
    cerveaux = repondre_automatiquement(texte)
    etapes = []
    a = analogies[0] if analogies else None
    c = cerveaux[0]
    if a:
        etapes.append(f"Mémoire associative : cela ressemble à « {a['exemple']} » ({a['score']:.0%} de proximité) "
                      f"→ {PAR_CLE[a['cle']].nom} : {a['reponse']}.")
    etapes.append(f"Mes cerveaux d'école : aiguillage vers « {c['matiere']} », réponse {c['reponse']} "
                  f"(confiance {c['confiance']:.0%}).")
    d_accord = a and a["cle"] == c["cle"] and a["reponse"] == c["reponse"]
    if d_accord:
        choix, confiance = a, min(0.99, max(a["score"], c["confiance"]) + 0.15)
        etapes.append("Les deux sont d'accord : je suis sûre de moi.")
    elif a and a["score"] >= SEUIL_ANALOGIE:
        choix, confiance = a, a["score"]
        etapes.append("Je fais confiance à l'analogie : elle est très proche de ce que je connais.")
    elif c["confiance"] >= max(SEUIL_CONFIANCE, a["score"] if a else 0):
        choix, confiance = {"cle": c["cle"], "reponse": c["reponse"]}, c["confiance"]
        etapes.append("Je fais confiance à mon cerveau d'école.")
    elif a and a["score"] >= SEUIL_PISTE:
        choix, confiance = a, a["score"]
        etapes.append("Ce n'est qu'une piste : je reste prudente.")
    else:
        choix, confiance = None, max(a["score"] if a else 0, c["confiance"])
        etapes.append("Rien d'assez proche dans ce que je connais : je préfère l'avouer.")

    lectures = []
    if memoire is not None:
        from .bibliotheque import chercher
        cles = {x for x in mots(texte) if x not in VIDES and len(x) > 3}
        lectures = [l for l in chercher(memoire, texte, n=2) if l["pertinence"] >= 0.4      # proche ET un vrai mot commun
                    and cles & {x for x in mots(f"{l['concept']} {l['explication']}") if len(x) > 3}]
        if lectures:
            etapes.append(f"Ma bibliothèque : {len(lectures)} concept(s) proche(s) dans mes lectures.")

    if choix is None:
        reponse = "Je ne sais pas encore répondre à ça avec mes propres cerveaux : je l'ai noté et je l'étudierai."
        if c["confiance"] > 0.05 or a:
            pistes = ([f"{PAR_CLE[a['cle']].nom} → {a['reponse']}"] if a else []) + [f"{c['matiere']} → {c['reponse']}"]
            reponse += " Mes pistes, sans certitude : " + " ; ".join(dict.fromkeys(pistes)) + "."
    else:
        m = PAR_CLE[choix["cle"]]
        prudence = "" if confiance >= SEUIL_ANALOGIE else "Je pense que "
        reponse = f"{prudence}**{choix['reponse']}** — {m.domaine}, {m.nom} (confiance {confiance:.0%})."
        if m.note:
            reponse += f"\n\n_{m.note}_"
        if choix.get("exemple") and choix["exemple"].lower().strip() != texte.lower().strip():
            reponse += f"\n\nJe le rapproche de ce que je connais : « {choix['exemple']} »."
        autre = next((x for x in [*analogies[1:], *([{"cle": c["cle"], "reponse": c["reponse"]}] if not d_accord else [])]
                      if (x["cle"], x["reponse"]) != (choix["cle"], choix["reponse"])
                      and x.get("score", 1) >= SEUIL_PISTE), None)
        if autre and confiance < 0.8:
            reponse += f"\n\nAutre hypothèse : {PAR_CLE[autre['cle']].nom} → {autre['reponse']}."
    for l in lectures:
        reponse += f"\n\n📚 {l['concept']} : {l['explication']} _(lu dans {l['source']})_"
    return reponse, etapes, round(confiance, 3)
