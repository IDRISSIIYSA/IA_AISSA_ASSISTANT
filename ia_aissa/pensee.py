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
import json
import time
from datetime import timezone
from pathlib import Path
import math
import operator
import re

from . import connaissances as K
from .ecole import MATIERES, PAR_CLE, SEUIL_CONFIANCE, mots, repondre, repondre_automatiquement

HORS_ANALOGIE = {"langues", "matiere_scolaire", "orientation"}
VIDES = set("le la les de des du un une et au aux pour par en sur dans mon ma mes ton ta je tu il elle qui que "
            "quoi est ce cet cette dyal dial li ana nta wach chno chnou".split())
SEUIL_ANALOGIE = 0.45          # au-dessus : l'analogie est assez proche pour répondre
SEUIL_PISTE = 0.28             # en dessous de SEUIL_REPONSE : seulement citée comme piste, sans réponse
SEUIL_REPONSE = 0.5            # le cerveau d'école seul doit être sûr à 50 % pour répondre


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
        souvenirs = list(dict.fromkeys(souvenirs))       # souvenirs identiques fusionnés
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
    (re.compile(r"^\s*(non|nn|la|lla|no|pas du tout|faux|c'est faux)\s*[.!]*\s*$", re.I),
     "D'accord, je me suis trompée. Dis-moi la bonne réponse (ou reformule ta question avec un exemple) : "
     "j'en ferai une correction et je réviserai."),
    (re.compile(r"^\s*(oui|ok|okay|d'accord|wakha|iyeh|ah|parfait|super|top)\s*[.!]*\s*$", re.I),
     "Parfait ! Pose-moi la suite quand tu veux : un calcul, une question de cours, ou un fichier à analyser."),
    (re.compile(r"(tu dois apprendre|apprends|apprend plus|khassek t(t)?3allem)", re.I),
     "J'apprends en continu : je lis seule Wikipédia, je m'exerce dans mes matières, je résous 5 crises budgétaires "
     "par heure et je retiens chacune de tes corrections. Le plus efficace : quand je me trompe, dis-moi « non, "
     "c'est … » avec la bonne réponse."),
]
SUITE = re.compile(r"^\s*(ex\w*li\w*|e?xpli\w*|détaill\w*|detaill\w*|plus de détails|davantage|pourquoi|"
                   r"comment (ça|ca)|zid|chre7|chra7|فسر|وضح)\b.{0,25}$", re.I)


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


def bulletin(brut):
    """Le bulletin de paie détaillé, ligne par ligne, avec la règle de chaque ligne."""
    p = K.calculer_paie(brut)
    base_cnss = min(brut, K.PLAFOND_CNSS_MENSUEL)
    return ("| Ligne | Règle | Montant |\n|---|---|---|\n"
            f"| Salaire brut | | {montant(brut)} |\n"
            f"| CNSS salarié | {K.CNSS_SALARIE:.2%} × {montant(base_cnss)} (plafond 6 000 DH) | − {montant(p['cnss_salarie'])} |\n"
            f"| AMO salarié | {K.AMO_SALARIE:.2%} × brut | − {montant(p['amo_salarie'])} |\n"
            f"| Frais professionnels | abattement sur le brut, plafonné | ({montant(p['frais_professionnels'])}) |\n"
            f"| Net imposable | brut − CNSS − AMO − frais professionnels | {montant(p['net_imposable'])} |\n"
            f"| IR | barème annuel ÷ 12 | − {montant(p['ir'])} |\n"
            f"| **Salaire net** | brut − CNSS − AMO − IR | **{montant(p['salaire_net'])}** |\n"
            f"| Charges patronales | CNSS + AMO employeur | {montant(p['charges_patronales'])} |\n"
            f"| Coût employeur | brut + charges patronales | {montant(brut + p['charges_patronales'])} |\n\n"
            f"_{p['remarque']}_")


def evolution(texte):
    """Une question sur l'évolution d'un impôt dans le temps : la clé de la chronologie connue, sinon None."""
    t = texte.lower()
    if not re.search(r"([ée]vol\w*tion|[ée]volu|historique|r[ée]forme|changement|a chang|depuis quand|chronologie)", t):
        return None
    return next((k for k, motif in (("tva", r"\btva\b|taxe sur la valeur"), ("is", r"\bis\b|impôt sur les sociétés"),
                                    ("ir", r"\bir\b|impôt sur le revenu")) if re.search(motif, t)), None)


def valeur_apres(texte, motif, portee=40):
    """Le premier nombre qui suit un mot-clé (à moins de 40 caractères) : « bénéfice de 500 000 dh » -> 500000."""
    m = re.search(motif, texte, re.I)
    if not m:
        return None
    suite = nombres(texte[m.end():m.end() + portee])
    return suite[0] if suite else None


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
    annees = re.compile(r"(?<![\d.,])(19[5-9]\d|20[0-4]\d)(?![\d.,])")
    sans_annees = annees.sub(" ", t) if re.search(r"\b(de|à|a|en|depuis|entre|et|jusqu'à|année|annee|loi de finances)\s+"
                                                  r"(19|20)\d\d\b", t) else t
    valeurs = [v for v in nombres(sans_annees) if v > 0]
    if re.search(r"bulletin de (paie|salaire)|fiche de paie|fiche de salaire", t):
        brut = max(valeurs) if valeurs else 8000.0
        return (f"Bulletin de paie simulé (Maroc) pour un salaire brut mensuel de **{montant(brut)}**"
                + ("" if valeurs else " (exemple : donne-moi ton brut pour le tien)") + " :\n\n" + bulletin(brut),
                ["Bulletin de paie demandé.", "Barème marocain : CNSS (plafond 6 000 DH), AMO, frais professionnels, IR."])
    if not valeurs:
        return None
    if re.search(r"\bnet\b", t) and re.search(r"(salaire|salire|brut|paie|khlass)", t):
        net = max(valeurs)
        brut = K.brut_pour_net(net)
        reponse = f"Pour toucher **{montant(net)} net** par mois, il faut un salaire brut de **{montant(brut)}**.\n\n" + bulletin(brut)
        etapes = ["Chiffre trouvé : salaire net mensuel.",
                  "Je cherche le brut par dichotomie : j'essaie un brut, je calcule le net, j'ajuste."]
        if re.search(r"(optimi|moins ch|moins cher|économ|econom|réduire|charges)", t):
            o = K.optimiser_salaire(net)
            a, b = o["tout_salaire"], o["avec_indemnites"]
            reponse += (
                f"\n\n**Optimisation légale (même net de {montant(net)})** :\n\n"
                "| | Tout en salaire | Salaire + indemnités exonérées |\n|---|---|---|\n"
                f"| Salaire brut | {montant(a['brut'])} | {montant(b['brut'])} |\n"
                f"| Indemnité de transport (zone urbaine) | — | {montant(b['transport'])} |\n"
                f"| Prime de panier (30 DH × 22 jours) | — | {montant(b['panier'])} |\n"
                f"| CNSS + AMO salarié | {montant(a['cnss_amo'])} | {montant(b['cnss_amo'])} |\n"
                f"| IR | {montant(a['ir'])} | {montant(b['ir'])} |\n"
                f"| Charges patronales | {montant(a['charges_patronales'])} | {montant(b['charges_patronales'])} |\n"
                f"| **Coût employeur** | **{montant(a['cout_employeur'])}** | **{montant(b['cout_employeur'])}** |\n\n"
                f"Économie pour l'employeur : **{montant(o['economie_employeur'])} par mois**.\n\n"
                "⚠️ Sans perdre d'avantages ? Pas tout à fait : les indemnités exonérées ne cotisent pas, donc les droits "
                "CNSS (retraite, indemnités journalières) se calculent sur un brut plus bas. Elles doivent aussi "
                "correspondre à une réalité (trajets, repas pris au travail), le salaire de base rester au moins au SMIG, "
                "et les plafonds sont à confirmer dans l'article 57 du CGI.")
            etapes.append("Je compare deux façons de verser le même net : tout en salaire, ou salaire + indemnités exonérées.")
        return reponse, etapes
    if re.search(r"(salaire|brut|paie|salaire net|khlass|khalss|chhar)", t) and not re.search(r"\bir\b|impôt sur le revenu", t):
        v = max(valeurs)
        p = K.calculer_paie(v)
        return (f"Pour un salaire brut mensuel de **{montant(v)}** : CNSS {montant(p['cnss_salarie'])}, AMO "
                f"{montant(p['amo_salarie'])}, frais professionnels {montant(p['frais_professionnels'])}, IR "
                f"{montant(p['ir'])} → **salaire net {montant(p['salaire_net'])}** (charges patronales "
                f"{montant(p['charges_patronales'])}). _{p['remarque']}_\n\n" + bulletin(v),
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
    if re.search(r"(\bis\b|impôt sur les sociétés|bénéfice|benefice|rb7|déficit|deficit|perte|cotisation minimale)", t):
        resultat = valeur_apres(t, r"(bénéfice|benefice|résultat fiscal|resultat fiscal|rb7)")
        perte = valeur_apres(t, r"(déficit|deficit|perte|khsara)")
        produits = valeur_apres(t, r"(chiffre d['’ ]?\s*affaires|\bca\b|produits|ventes|recettes|rqm)")
        if produits is not None and (resultat is not None or perte is not None):
            benefice = -perte if perte is not None else resultat
            r = K.calculer_is_du(benefice, produits)
            return (f"Résultat fiscal **{montant(benefice)}**, produits {montant(produits)} : IS proportionnel "
                    f"{montant(r['is'])} ({r['taux']:.0%}), cotisation minimale {montant(r['cotisation_minimale'])} "
                    f"(0,25 % des produits, au moins 3 000 DH) → **IS dû {montant(r['is_du'])}** ({r['retenu']}).",
                    ["Chiffres trouvés : résultat fiscal et produits (chiffre d'affaires).",
                     "IS proportionnel (20 %, 35 % au-delà de 100 MDH) comparé à la cotisation minimale.",
                     "Le plus élevé des deux est dû (CGI, art. 144)."])
    if re.search(r"(\bis\b|impôt sur les sociétés|bénéfice|benefice|rb7)", t):
        v = max(valeurs)
        r = K.calculer_is(v)
        return (f"Bénéfice fiscal **{montant(v)}** → **IS {montant(r['is'])}** (taux {r['taux']:.0%}). _{r['remarque']}_",
                ["Chiffre trouvé : bénéfice fiscal.", "Taux d'IS marocain."])
    collectee = valeur_apres(t, r"collect[ée]e")
    deductible = valeur_apres(t, r"(d[ée]ductible|r[ée]cup[ée]rable)")
    if re.search(r"\btva\b", t) and collectee is not None and deductible is not None:
        r = K.calculer_tva_due(collectee, deductible)
        conclusion = (f"**TVA due {montant(r['tva_due'])}**" if r["tva_due"] else
                      f"**crédit de TVA {montant(r['credit_de_tva'])}**, reportable sur les déclarations suivantes")
        return (f"TVA collectée {montant(collectee)} − TVA déductible {montant(deductible)} → {conclusion}.",
                ["Chiffres trouvés : TVA collectée sur les ventes et TVA déductible sur les achats.",
                 "TVA due = collectée − déductible ; si négatif, crédit de TVA."])
    if re.search(r"\b(tva|ttc|ht)\b", t):
        v = max(valeurs)
        taux = next((x / 100 for x in valeurs if x in (7, 10, 14, 20) and x != v), None)
        if taux is None:
            regime = repondre("tva", texte, top=1)[0]
            if regime["confiance"] < 0.5:                 # produit inconnu : taux normal
                taux = 0.2
            else:
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
def penser(texte, memoire=None, conclusion=None, precedente=None, utilisateur=None):
    """Réponse d'IA AISSA avec ses propres cerveaux. Renvoie (réponse en markdown, étapes du raisonnement, confiance).
    conclusion (dict facultatif) reçoit la matière, la réponse retenue et l'accord analogie × école.
    precedente : la question d'avant, pour comprendre « explique plus », « pourquoi »…"""
    if precedente and SUITE.search(texte) and not SUITE.search(precedente):
        reponse, etapes, confiance = penser(precedente, memoire, utilisateur=utilisateur)
        return (f"Je reprends ta question précédente (« {precedente} ») plus en détail :\n\n{reponse}\n\n"
                "**Comment j'ai raisonné** :\n" + "\n".join(f"{i}. {e}" for i, e in enumerate(etapes, 1)),
                ["Tu demandes plus de détails : je reprends ta question précédente."] + etapes, confiance)
    for motif, reponse in CONVERSATION:
        if motif.search(texte) and len(texte.split()) <= 6:
            return reponse, ["Petite conversation reconnue."], 0.95

    sujet_evolution = evolution(texte)
    calcul = None if sujet_evolution else calculer(texte)
    if calcul:
        reponse, etapes = calcul
        return reponse, ["Je repère des chiffres et un calcul que je sais faire."] + etapes, 0.9

    from .lecture import repondre_par_lecture
    lu = repondre_par_lecture(texte, memoire, utilisateur)
    if lu:                                             # ce qu'elle a lu passe avant ce qu'on lui a écrit
        return ("D'après mes lectures :\n\n" + lu["reponse"],
                [f"Je cherche dans ma mémoire de lecture : {len(lu['sources'])} document(s) répondent "
                 f"({', '.join(lu['sources'][:4])}).", "Je cite les phrases exactes, avec leur source."], lu["confiance"])
    if sujet_evolution:
        return (K.EVOLUTIONS[sujet_evolution] + "\n\n_Connaissance intégrée : je ne l'ai pas encore trouvée dans mes "
                "lectures (dépose-moi les textes officiels pour que je la vérifie)._",
                ["Question sur une évolution dans le temps.", "Rien de proche dans mes lectures : chronologie intégrée."],
                0.7)

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
    vrais_mots = [x for x in mots(texte) if x not in VIDES and len(x) > 2]
    if len(vrais_mots) < 2 and not (a and a["score"] >= 0.8):      # « non », « explique plus » : trop court pour classer
        d_accord, a, c = False, None, {**c, "confiance": 0.0}
        etapes.append("Message trop court pour que je devine sa matière.")
    if d_accord:
        choix, confiance = a, min(0.99, max(a["score"], c["confiance"]) + 0.15)
        etapes.append("Les deux sont d'accord : je suis sûre de moi.")
    elif a and a["score"] >= SEUIL_ANALOGIE:
        choix, confiance = a, a["score"]
        etapes.append("Je fais confiance à l'analogie : elle est très proche de ce que je connais.")
    elif c["confiance"] >= max(SEUIL_REPONSE, a["score"] if a else 0):
        choix, confiance = {"cle": c["cle"], "reponse": c["reponse"]}, c["confiance"]
        etapes.append("Je fais confiance à mon cerveau d'école.")
    else:
        choix, confiance = None, max(a["score"] if a else 0, c["confiance"])
        etapes.append("Rien d'assez proche dans ce que je connais : je préfère l'avouer.")

    if conclusion is not None and choix is not None:
        conclusion.update(cle=choix["cle"], reponse=choix["reponse"], confiance=confiance, accord=bool(d_accord))
    lectures = []
    if memoire is not None:
        from .bibliotheque import chercher
        cles = {x for x in mots(texte) if x not in VIDES and len(x) > 3}
        lectures = [l for l in chercher(memoire, texte, n=2, utilisateur=utilisateur) if l["pertinence"] >= 0.4      # proche ET un vrai mot commun
                    and cles & {x for x in mots(f"{l['concept']} {l['explication']}") if len(x) > 3}]
        if lectures:
            etapes.append(f"Ma bibliothèque : {len(lectures)} concept(s) proche(s) dans mes lectures.")

    if choix is None:
        reponse = (f"Je ne suis pas sûre de comprendre « {texte.strip()[:80]} ». Peux-tu préciser (un chiffre, un exemple, "
                   "la matière) ? Je l'ai noté et je l'étudierai.")
        if max(c["confiance"], a["score"] if a else 0) >= SEUIL_PISTE:
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
    if memoire is not None:
        for l in lectures:                       # une lecture utile est gardée (l'élagage oublie les autres)
            memoire.definir_reglage(f"lecture_utilisee:{l['id']}", str(int(time.time())))
    for l in lectures:
        reponse += f"\n\n📚 {l['concept']} : {l['explication']} _(lu dans {l['source']})_"
    return reponse, etapes, round(confiance, 3)


# ==========================================
# Hygiène de la mémoire : compresser quand elle devient dense
# ==========================================
SEUIL_DENSITE = 1500            # concepts lus au-delà desquels la bibliothèque est élaguée
OUBLI_JOURS = 7                 # un fait lu seule sur le web et jamais utilisé depuis 7 jours est oublié


def cle_concept(nom):
    return " ".join(sorted(set(mots(nom))))


def elaguer(memoire, seuil=SEUIL_DENSITE, jours=OUBLI_JOURS, maintenant=None, forcer=False):
    """Si la bibliothèque est dense : fusionne les concepts redondants (même nom, à l'accent et à l'ordre des mots
    près ; on garde le plus ancien) et oublie les faits lus seule sur le web, jamais utilisés pour répondre,
    et plus vieux que 7 jours. Les livres et pages donnés par une personne ne sont jamais oubliés.
    Renvoie le bilan."""
    digestions = memoire.digestions(100_000)
    total = sum(len(json.loads(d["concepts"])) for d in digestions)
    bilan = {"concepts_avant": total, "fusionnes": 0, "oublies": 0, "dense": total > seuil}
    if not (bilan["dense"] or forcer):
        bilan["concepts_apres"] = total
        return bilan
    utilisees = {int(k.split(":", 1)[1]) for k in memoire.reglages("lecture_utilisee:")}
    limite = (maintenant or time.time()) - jours * 86_400
    vus = set()
    for d in sorted(digestions, key=lambda d: d["id"]):              # du plus ancien au plus récent
        date = d["cree_le"]
        quand = (date if date.tzinfo else date.replace(tzinfo=timezone.utc)).timestamp()
        if d["utilisateur"] == "IA AISSA" and d["id"] not in utilisees and quand < limite:
            bilan["oublies"] += len(json.loads(d["concepts"]))
            memoire.supprimer_digestion(d["id"])
            continue
        concepts = json.loads(d["concepts"])
        gardes = []
        for c in concepts:
            cle = cle_concept(c.get("nom", ""))
            if cle and cle in vus:
                bilan["fusionnes"] += 1
            else:
                vus.add(cle)
                gardes.append(c)
        if len(gardes) != len(concepts):
            if gardes:
                memoire.modifier_concepts(d["id"], json.dumps(gardes, ensure_ascii=False))
            else:
                memoire.supprimer_digestion(d["id"])
    bilan["concepts_apres"] = total - bilan["fusionnes"] - bilan["oublies"]
    return bilan


# ==========================================
# Mémoire vive : rester loin de la limite de Streamlit Cloud
# ==========================================
PLAFOND_RAM_MO = 400            # au-delà, elle s'allège (la limite gratuite de Streamlit Cloud est d'environ 1 Go)


def memoire_vive_mo():
    """Mémoire vive occupée par le serveur (Mo), lue dans /proc (Linux, comme Streamlit Cloud) ; None ailleurs."""
    try:
        with open("/proc/self/status") as f:
            ligne = next(l for l in f if l.startswith("VmRSS:"))
        return round(int(ligne.split()[1]) / 1024, 1)
    except (OSError, StopIteration, ValueError):
        return None


def alleger(plafond=PLAFOND_RAM_MO):
    """Au-dessus du plafond : vide les caches qui se reconstruisent seuls (cerveaux chargés, mémoire associative,
    vocabulaire). Le savoir lui-même ne vit pas en mémoire vive : il est dans la base (SQLite ou PostgreSQL)."""
    import gc
    avant = memoire_vive_mo()
    if avant is None or avant < plafond:
        return {"avant": avant, "apres": avant, "allege": False}
    from . import autodidacte, ecole
    ecole._CACHE.clear()
    _CACHE.clear()
    autodidacte._VOCABULAIRE.clear()
    gc.collect()
    return {"avant": avant, "apres": memoire_vive_mo(), "allege": True}


# ==========================================
# « Non, c'est … » : se corriger pendant la conversation
# ==========================================
CORRECTION = re.compile(r"^\s*(non|nn|la|faux)\s*[,.!:]?\s*(c'est|c est|c’est|plutôt|plutot|la bonne réponse est|rah|hiya|howa)"
                        r"\s+(.{2,120})$", re.I)


def correction_dans_la_conversation(texte, memoire, conclusion_precedente, question_precedente, valider=True,
                                    auteur="Aissa"):
    """« non, c'est 2340 » juste après une réponse : la bonne réponse devient une correction, révisée aussitôt.
    valider=False (visiteur) : la correction attend la validation de l'administrateur (pas d'empoisonnement)."""
    m = CORRECTION.search(texte or "")
    if not (m and conclusion_precedente and question_precedente and memoire is not None):
        return None
    if not valider:
        from .corrections import valider_reponse
        officielle = valider_reponse(conclusion_precedente["cle"], m.group(3).strip(" .!"))
        if officielle is None:
            return "Je n'ai pas trouvé cette réponse dans ma matière : reformule avec un exemple, s'il te plaît."
        proposer_correction(memoire, auteur, conclusion_precedente["cle"], question_precedente, officielle)
        return (f"Merci ! J'ai noté ta correction (« {question_precedente} » → **{officielle}**). "
                "Mon administrateur la vérifiera avant que je l'apprenne.")
    from .corrections import corriger, reviser
    try:
        r = corriger(memoire, "Aissa", conclusion_precedente["cle"], question_precedente, m.group(3).strip(" .!"),
                     source="utilisateur")
    except ValueError as e:
        return f"Je n'ai pas trouvé cette réponse dans ma matière : {e}"
    bilan = reviser(memoire, conclusion_precedente["cle"])
    adoptee = bilan and bilan.get("adoptee")
    return (f"Merci ! J'ai retenu : « {question_precedente} » → **{r['bonne_reponse']}** ({r['matiere']}). "
            + ("J'ai révisé mon cerveau : je ne referai pas cette erreur." if adoptee else
               "Je l'ai gardé en mémoire ; ma révision n'a pas encore été adoptée (elle ne doit rien me faire oublier), "
               "mais ma mémoire associative s'en sert déjà."))


# ==========================================
# Ingestion de livres PDF : lire le livre entier, distiller, garder
# ==========================================
FICHIER_MEMOIRE = Path(__file__).resolve().parents[1] / "data" / "aissa_memoire.json"
MAX_PASSAGES = 60               # au-delà, 60 passages répartis du début à la fin du livre


MAX_PAGES_LUES = 150            # très gros PDF : 150 pages réparties du début à la fin (mémoire vive ménagée)


def lire_livre(chemin, nom, max_pages=MAX_PAGES_LUES):
    """Texte d'un PDF ou d'un EPUB lu sur le disque ; un très gros PDF est lu page par page, sur un échantillon
    régulier de pages, sans charger tout le fichier en mémoire. Renvoie (titre, texte, pages lues, pages totales)."""
    from .bibliotheque import texte_epub
    if nom.lower().endswith(".epub"):
        with open(chemin, "rb") as f:
            titre, texte = texte_epub(f.read())
        return titre, texte, 1, 1
    from pypdf import PdfReader
    lecteur = PdfReader(chemin)
    total = len(lecteur.pages)
    choisies = sorted({round(i * (total - 1) / max(1, max_pages - 1)) for i in range(min(total, max_pages))})
    titre = lecteur.metadata.title if lecteur.metadata and lecteur.metadata.title else ""
    return titre, "\n".join((lecteur.pages[i].extract_text() or "") for i in choisies), len(choisies), total


def ingerer_fichier(memoire, chemin, nom, utilisateur="Aissa", fichier_json=None, source=None, max_pages=MAX_PAGES_LUES):
    """Lit un livre déjà sur le disque, le rumine avec sa pensée propre (sans clé API), range les concepts dans sa
    mémoire durable et une copie distillée dans data/aissa_memoire.json, puis SUPPRIME le fichier (os.remove).
    Renvoie le bilan ; lève ValueError si le livre n'a pas de texte (scan sans OCR)."""
    import os
    from datetime import datetime
    from .bibliotheque import TAILLE_MORCEAU, digerer
    try:
        titre, texte, pages_lues, pages_total = lire_livre(chemin, nom, max_pages)
    finally:
        if os.path.exists(chemin):
            os.remove(chemin)                         # le fichier source ne reste jamais sur le disque du serveur
    texte = " ".join(texte.split())
    if len(texte) < 200:
        raise ValueError("ce livre n'a presque pas de texte : c'est sans doute un livre scanné (des images de pages). "
                         "Il faudrait d'abord le passer à la reconnaissance de caractères (OCR).")
    source = source or titre or nom
    from .lecture import decouper
    morceaux_lus = decouper(texte)
    memoire.garder_passages(utilisateur, source, morceaux_lus)     # le texte lui-même : elle pourra le retrouver
    passages = -(-len(texte) // TAILLE_MORCEAU)
    bilan = digerer(memoire, None, None, source, texte, utilisateur, nb_bouchees=min(passages, MAX_PASSAGES))
    concepts = [c for d in bilan["digestions"] for c in d["concepts"]]
    fichier_json = Path(fichier_json or FICHIER_MEMOIRE)
    fichier_json.parent.mkdir(parents=True, exist_ok=True)
    try:
        archive = json.loads(fichier_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        archive = []
    archive.append({"source": source, "utilisateur": utilisateur, "date": datetime.now(timezone.utc).isoformat(),
                    "caracteres": len(texte), "passages_lus": bilan["bouchees"], "passages_total": passages,
                    "pages_lues": pages_lues, "pages_total": pages_total,
                    "familles": sorted({d["famille"] for d in bilan["digestions"]}), "concepts": concepts})
    fichier_json.write_text(json.dumps(archive, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"source": source, "caracteres": len(texte), "passages_lus": bilan["bouchees"],
            "passages_total": passages, "concepts": len(concepts), "passages_gardes": len(morceaux_lus),
            "entier": pages_lues >= pages_total,
            "pages_lues": pages_lues, "pages_total": pages_total, "lacunes_comblees": len(bilan["lacunes_comblees"])}


def ingerer_pdf(memoire, nom, contenu, utilisateur="Aissa", fichier_json=None, max_pages=3000):
    """Un livre reçu en mémoire (dépôt) : écrit dans un fichier temporaire, lu, puis supprimé aussitôt."""
    import tempfile
    temporaire = tempfile.NamedTemporaryFile(suffix=Path(nom).suffix or ".pdf", delete=False)
    temporaire.write(contenu)
    temporaire.close()
    return ingerer_fichier(memoire, temporaire.name, nom, utilisateur, fichier_json, max_pages=max_pages)


def confirmation_ingestion(bilan):
    """Le message de l'alien après un livre, en darija et en français, fidèle à ce qui a vraiment été lu."""
    if bilan["entier"]:
        lu = (f"Klit lktab kamel w wssa3t l3alam dyali ! J'ai lu tout le livre « {bilan['source']} » : "
              f"{bilan.get('passages_gardes', bilan['passages_lus'])} passages gardés mot pour mot dans ma mémoire de "
              f"lecture et {bilan['concepts']} concepts digérés.")
    else:
        pages = (f"{bilan['pages_lues']} pages sur {bilan['pages_total']}, " if bilan.get("pages_total", 1) > 1
                 and bilan.get("pages_lues", 1) < bilan["pages_total"] else "")
        lu = (f"Klit l'essentiel dyal lktab ! J'ai lu « {bilan['source']} » ({pages}réparties du début à la fin) et digéré "
              f"{bilan['passages_lus']} passages (sur {bilan['passages_total']}), soit {bilan['concepts']} concepts : "
              "mon univers s'est agrandi.")
    return lu + " Tout est gardé dans ma mémoire : tu peux supprimer le fichier source !"


def proposer_correction(memoire, auteur, cle, question, reponse):
    memoire.definir_reglage(f"proposition:{int(time.time() * 1000)}", json.dumps(
        {"auteur": auteur, "matiere": cle, "question": question, "reponse": reponse}, ensure_ascii=False))


def propositions(memoire):
    """Corrections proposées par des visiteurs, en attente de validation : [(clé, proposition)]."""
    return [(k, json.loads(v)) for k, v in sorted(memoire.reglages("proposition:").items())]
