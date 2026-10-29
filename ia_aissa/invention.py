"""
Laboratoire d'invention : évolution génétique des idées par auto-simulation.

IA AISSA se dédouble dans son univers :
- l'Inventeur croise des domaines éloignés (analogies) et applique les opérateurs SCAMPER / TRIZ ;
- le Contrôleur, strict (règle de Dalio), note chaque idée et nomme son défaut principal.
À chaque génération, seules les meilleures idées survivent ; elles sont croisées deux à deux et mutées
pour corriger leurs défauts. Coût maîtrisé : environ deux appels au moteur par génération.
"""

import json
import random

from .autonomie import demander, lire_json
from .ecole import MATIERES

DOMAINES = sorted({m.domaine.split(" — ")[0] for m in MATIERES} | {
    "Biologie et microbiologie", "Physique", "Chimie", "Architecture", "Agriculture", "Médecine", "Musique",
    "Écologie", "Sport", "Artisanat marocain", "Énergie solaire", "Transport", "Jeux vidéo", "Cuisine"})
SCAMPER = ["Substituer", "Combiner", "Adapter", "Modifier / amplifier", "Autre usage", "Éliminer", "Inverser"]
CRITERES = {"nouveaute": 0.3, "impact": 0.3, "faisabilite": 0.25, "cout": 0.15}   # cout : 10 = très peu coûteux


def paires_eloignees(rng, n):
    paires = set()
    while len(paires) < n:
        a, b = rng.sample(DOMAINES, 2)
        paires.add(tuple(sorted((a, b))))
    return list(paires)


def _inventer(moteur, client, probleme, consignes):
    texte = demander(moteur, client, (
        "Tu es l'Inventeur d'IA AISSA. Problème à résoudre :\n" + probleme + "\n\n" + consignes +
        '\n\nRéponds uniquement par un tableau JSON : [{"titre": "...", "description": "3 phrases : principe, '
        'fonctionnement, pour qui", "domaines": ["...", "..."]}]'))
    return [i for i in lire_json(texte) if isinstance(i, dict) and i.get("titre")]


def generer_population(moteur, client, probleme, taille, rng):
    lignes = [f"{k + 1}. Croise « {a} » et « {b} », opérateur SCAMPER : {rng.choice(SCAMPER)}"
              for k, (a, b) in enumerate(paires_eloignees(rng, taille))]
    return _inventer(moteur, client, probleme, "Propose une idée originale pour chaque ligne :\n" + "\n".join(lignes))


def critiquer(moteur, client, probleme, idees):
    liste = "\n".join(f"{k}. {i['titre']} : {i.get('description', '')}" for k, i in enumerate(idees))
    texte = demander(moteur, client, (
        "Tu es le Contrôleur d'IA AISSA : exigeant, factuel, sans complaisance (règle de Dalio). Problème :\n"
        f"{probleme}\n\nIdées :\n{liste}\n\nNote chaque idée de 0 à 10 : nouveaute, impact, faisabilite, cout "
        "(10 = très peu coûteux), et donne son défaut principal en une phrase. Signale si l'idée existe déjà.\n"
        'Réponds uniquement par un tableau JSON : [{"index": 0, "nouveaute": 7, "impact": 6, "faisabilite": 5, '
        '"cout": 4, "defaut": "..."}]'))
    for note in lire_json(texte):
        if isinstance(note, dict) and isinstance(note.get("index"), int) and 0 <= note["index"] < len(idees):
            idee = idees[note["index"]]
            idee["notes"] = {c: max(0.0, min(10.0, float(note.get(c, 0)))) for c in CRITERES}
            idee["defaut"] = note.get("defaut", "")
    for idee in idees:
        idee.setdefault("notes", {c: 0.0 for c in CRITERES})
        idee["score"] = round(sum(idee["notes"][c] * p for c, p in CRITERES.items()), 2)
    return idees


def reproduire(moteur, client, probleme, survivants, nb_enfants, rng):
    couples = [rng.sample(survivants, 2) for _ in range(nb_enfants)]
    lignes = [f"{k + 1}. Parents : « {a['titre']} » ({a.get('description', '')}) défaut : {a.get('defaut', '-')} "
              f"× « {b['titre']} » ({b.get('description', '')}) défaut : {b.get('defaut', '-')} ; "
              f"mutation SCAMPER : {rng.choice(SCAMPER)}" for k, (a, b) in enumerate(couples)]
    return _inventer(moteur, client, probleme, (
        "Croise chaque couple d'idées parentes : garde leurs forces, corrige leurs défauts et applique la mutation "
        "indiquée, pour obtenir une idée enfant meilleure que ses deux parents :\n" + "\n".join(lignes)))


def evoluer(moteur, client, probleme, generations=3, taille=6, seed=None, callback=None):
    """Renvoie l'historique des générations (idées notées) et la meilleure idée obtenue."""
    rng = random.Random(seed)
    population = critiquer(moteur, client, probleme, generer_population(moteur, client, probleme, taille, rng))
    historique = [population]
    if callback:
        callback(1, generations, population)
    for g in range(2, generations + 1):
        survivants = sorted(population, key=lambda i: -i["score"])[:max(2, taille // 2)]
        enfants = critiquer(moteur, client, probleme,
                            reproduire(moteur, client, probleme, survivants, taille - len(survivants), rng))
        population = sorted(survivants + enfants, key=lambda i: -i["score"])[:taille]
        historique.append(enfants)
        if callback:
            callback(g, generations, population)
    meilleure = max((i for gen in historique for i in gen), key=lambda i: i["score"])
    return historique, meilleure


def resume(idee):
    return json.dumps({k: idee.get(k) for k in ("titre", "description", "domaines", "notes", "defaut", "score")},
                      ensure_ascii=False)


# ==========================================
# Auto-simulation : le Créateur et le Critique débattent
# ==========================================
def lire_objet(texte):
    debut, fin = texte.find("{"), texte.rfind("}")
    try:
        return json.loads(texte[debut:fin + 1]) if debut >= 0 and fin > debut else {}
    except json.JSONDecodeError:
        return {}


def _note(valeur):
    try:
        return max(0.0, min(10.0, float(valeur)))
    except (TypeError, ValueError):
        return 0.0


def debattre(moteur, client, probleme, idee, iterations=3, callback=None):
    """Le Critique (règle de Dalio) attaque, le Créateur répond et révise, pendant `iterations` tours.
    Renvoie l'idée affinée, la transcription du débat et le score du contrôleur de méta-intelligence."""
    courante = {k: idee.get(k) for k in ("titre", "description", "domaines")}
    transcription, critiques = [], []
    for tour in range(1, iterations + 1):
        critique = lire_objet(demander(moteur, client, (
            "Tu es le Critique d'IA AISSA (règle de Dalio) : exigeant, factuel. Problème :\n" + probleme +
            f"\n\nInvention actuelle : {courante['titre']} — {courante.get('description', '')}\n\n"
            "Attaque-la : faisabilité technique, efficience des ressources, équilibre financier (coûts, revenus, "
            "rentabilité). Liste aussi les affirmations douteuses ou invérifiables (risque d'hallucination). "
            "Note de 0 à 10 la faisabilite, l'efficience et l'equilibre_financier.\n"
            'Réponds uniquement en JSON : {"objections": ["..."], "affirmations_a_verifier": ["..."], '
            '"faisabilite": 6, "efficience": 5, "equilibre_financier": 4}')))
        critique = {"objections": [str(o) for o in critique.get("objections", [])][:5],
                    "affirmations_a_verifier": [str(a) for a in critique.get("affirmations_a_verifier", [])][:5],
                    **{c: _note(critique.get(c)) for c in ("faisabilite", "efficience", "equilibre_financier")}}
        critiques.append(critique)
        transcription.append({"tour": tour, "agent": "Critique", **critique})
        revision = lire_objet(demander(moteur, client, (
            "Tu es le Créateur d'IA AISSA (TRIZ, SCAMPER, analogies entre domaines éloignés). Problème :\n" +
            probleme + f"\n\nTon invention : {courante['titre']} — {courante.get('description', '')}\n\n"
            "Objections du Critique :\n- " + "\n- ".join(critique["objections"] or ["aucune"]) +
            "\nAffirmations à vérifier :\n- " + "\n- ".join(critique["affirmations_a_verifier"] or ["aucune"]) +
            "\n\nRévise l'invention pour répondre à chaque objection ; retire ou reformule prudemment toute "
            "affirmation invérifiable. Garde ce qui fait son originalité.\n"
            'Réponds uniquement en JSON : {"titre": "...", "description": "4 phrases", "reponses": ["..."]}')))
        if revision.get("titre"):
            courante.update(titre=revision["titre"], description=revision.get("description", ""))
        transcription.append({"tour": tour, "agent": "Créateur", "titre": courante["titre"],
                              "description": courante.get("description", ""),
                              "reponses": [str(r) for r in revision.get("reponses", [])][:5]})
        if callback:
            callback(tour, iterations, courante)
    return courante, transcription, score_meta(critiques)


def score_meta(critiques):
    """Contrôleur de méta-intelligence : confiance et faisabilité de l'invention finale.
    - faisabilité : moyenne des trois notes du dernier tour du Critique ;
    - confiance : faisabilité, progrès au fil du débat, stabilité finale, et pénalité pour chaque
      affirmation encore douteuse (filtre anti-hallucination)."""
    moyennes = [(c["faisabilite"] + c["efficience"] + c["equilibre_financier"]) / 30 for c in critiques]
    faisabilite = moyennes[-1]
    progres = max(0.0, moyennes[-1] - moyennes[0])
    stabilite = 1 - min(1.0, abs(moyennes[-1] - moyennes[-2]) * 5) if len(moyennes) > 1 else 0.5
    doutes = len(critiques[-1]["affirmations_a_verifier"])
    confiance = 0.55 * faisabilite + 0.15 * min(1.0, progres * 4) + 0.15 * stabilite + 0.15 * (1 - min(doutes, 5) / 5)
    return {"faisabilite": round(faisabilite, 3), "confiance": round(max(0.0, min(1.0, confiance)), 3),
            "progres": round(progres, 3), "doutes_restants": doutes,
            "evolution": [round(m, 3) for m in moyennes]}


# ==========================================
# Annonce en darija, avec la sagesse des proverbes marocains
# ==========================================
PROVERBES = [
    ("شاور اللي يبكيك وما تشاورش اللي يضحكك", "consulte celui qui te fait pleurer, pas celui qui te fait rire"),
    ("قطرة قطرة كيحمل الواد", "goutte après goutte, la rivière se remplit"),
    ("اللي بغا العسل يصبر لقريص النحل", "qui veut le miel supporte les piqûres des abeilles"),
    ("يد وحدة ما كتصفقش", "une seule main n'applaudit pas"),
]


def annonce_darija(idee, meta, nom=None, rng=None):
    """Salutation selon l'heure du Maroc, proverbe de sagesse, puis l'invention et la confiance."""
    from .reconnaissance import moment_de_la_journee
    from .visage import SALUTATIONS
    rng = rng or random.Random()
    proverbe, sens = rng.choice(PROVERBES)
    salut = SALUTATIONS["Darija"][moment_de_la_journee()].format(nom=nom) + " " if nom else ""
    texte = (f"{salut}{proverbe}. المخترع والناقد ديالي تناقشو مزيان، وها شنو خرج من المختبر ديالي: "
             f"{idee['titre']}. الثقة ديالي فهاد الفكرة {round(meta['confiance'] * 100)} فالمية.")
    return texte, f"« {proverbe} » : {sens}."
