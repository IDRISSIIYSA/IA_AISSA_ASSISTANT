"""
Étude autonome : IA AISSA développe ses compétences de sa propre initiative.

1. Elle repère ses lacunes : toute question à laquelle son cerveau d'école n'a pas su répondre avec assurance.
2. Quand des lacunes s'accumulent, elle les étudie seule : elle demande à son moteur de conversation
   (Claude, GPT-4o ou MiniMax) de classer chaque question dans la bonne matière et la bonne réponse,
   transforme ces réponses en corrections, puis révise (avec la règle de Dalio contre les régressions).
3. Plus on lui parle, plus elle a de matière à apprendre : son apprentissage s'accélère avec l'usage.
"""

import json
import re

from .corrections import ORIENTATION, corriger, reviser_tout
from .ecole import PAR_CLE, SEUIL_CONFIANCE, repondre_automatiquement

SEUIL_ETUDE = 3                 # nombre de lacunes à partir duquel IA AISSA étudie d'elle-même
MATIERES_ETUDIABLES = [m for m in PAR_CLE.values() if m.texte and m.cle not in (ORIENTATION, "langues")]


def noter_si_lacune(memoire, question, propositions=None):
    """Note la question comme lacune si IA AISSA n'est pas sûre de sa réponse. Renvoie True si c'est le cas."""
    question = " ".join(str(question).split())
    if not 3 <= len(question) <= 300:
        return False
    propositions = propositions or repondre_automatiquement(question)
    meilleure = propositions[0]
    if meilleure["confiance"] >= SEUIL_CONFIANCE:
        return False
    memoire.ajouter_lacune(question, meilleure["cle"], meilleure["confiance"])
    return True


def consigne_etude(lacunes):
    programme = "\n".join(f"- {m.cle} ({m.nom}) : " + " | ".join(m.actions) for m in MATIERES_ETUDIABLES)
    questions = "\n".join(f"{l['id']}. {l['question']}" for l in lacunes)
    return (
        "Tu aides IA AISSA, une petite IA marocaine, à apprendre. Pour chaque question ci-dessous, indique la "
        "matière de son programme qui permet d'y répondre et la bonne réponse, en recopiant EXACTEMENT un des "
        "libellés proposés. Si aucune matière ne convient (salutation, question générale, hors programme), "
        "mets null. Ne devine pas : en cas de doute, mets null.\n\n"
        f"Programme (clé (nom) : réponses possibles) :\n{programme}\n\nQuestions :\n{questions}\n\n"
        'Réponds uniquement par un tableau JSON : [{"id": 1, "matiere": "cle" ou null, "reponse": "libellé" ou null}]'
    )


def demander(moteur_config, client, consigne):
    """Une question simple au moteur de conversation, réponse en texte."""
    if moteur_config["type"] == "anthropic":
        r = client.messages.create(model=moteur_config["modele"], max_tokens=8000,
                                   output_config={"effort": "low"},
                                   messages=[{"role": "user", "content": consigne}])
        return "".join(b.text for b in r.content if b.type == "text")
    r = client.chat.completions.create(model=moteur_config["modele"], extra_body=moteur_config.get("extra_body"),
                                       messages=[{"role": "user", "content": consigne}])
    return re.sub(r"<think>.*?</think>", "", r.choices[0].message.content or "", flags=re.S)


def lire_json(texte):
    debut, fin = texte.find("["), texte.rfind("]")
    return json.loads(texte[debut:fin + 1]) if debut >= 0 and fin > debut else []


def etudier_seule(memoire, moteur_config, client, limite=25):
    """Étudie les lacunes ouvertes, enregistre les corrections et révise. Renvoie un bilan."""
    lacunes = memoire.lacunes_ouvertes(limite)
    if not lacunes:
        return {"etudiees": 0, "apprises": 0, "hors_programme": 0, "revisions": []}
    reponses = {r.get("id"): r for r in lire_json(demander(moteur_config, client, consigne_etude(lacunes)))
                if isinstance(r, dict)}
    apprises = hors_programme = 0
    for l in lacunes:
        r = reponses.get(l["id"], {})
        if r.get("matiere") and r.get("reponse") and r["matiere"] in PAR_CLE:
            try:
                corriger(memoire, "IA AISSA", r["matiere"], l["question"], r["reponse"], source="étude autonome")
                apprises += 1
            except ValueError:
                hors_programme += 1
        else:
            hors_programme += 1
        memoire.resoudre_lacune(l["id"])
    return {"etudiees": len(lacunes), "apprises": apprises, "hors_programme": hors_programme,
            "revisions": reviser_tout(memoire) if apprises else []}
