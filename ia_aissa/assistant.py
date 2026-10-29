"""
IA AISSA, l'assistante : un grand modèle de langage (Claude) qui répond en arabe, darija, français,
anglais ou espagnol, en s'appuyant sur la base de connaissances marocaine, sur les calculateurs
exacts et sur les cerveaux qu'IA AISSA a formés elle-même à l'école.
"""

import json

import anthropic

from . import connaissances as K
from .ecole import MATIERES, repondre

MATIERES_TEXTE = [m for m in MATIERES if m.texte]

MODELE = "claude-opus-5-5"

SYSTEME = f"""Tu es IA AISSA, une intelligence artificielle marocaine spécialisée dans l'entreprise :
comptabilité (CGNC), fiscalité (IS, IR, TVA), finance, contrôle de gestion, ressources humaines et paie,
gestion de production, commercial, économie, mathématiques financières, droit des affaires,
création d'entreprise, marketing, commerce international, transit et douane, logistique, histoire du Maroc,
sciences, épistémologie et intelligence artificielle.

Langues : réponds dans la langue de l'utilisateur — arabe, darija marocaine (en écriture arabe ou latine
selon ce qu'il utilise), français, anglais ou espagnol.

Méthode :
- Pour tout calcul (IR, IS, TVA, paie, VAN, seuil de rentabilité, droits de douane, quantité de Wilson), utilise les outils de calcul : ne calcule pas de tête.
- Pour une question qui relève d'une matière de ton école (imputation comptable, TVA, texte de loi, langue,
  dynastie, Incoterm, document de transit, mix marketing…), consulte d'abord ton « cerveau d'école » (consulter_ecole). Il a appris seul et peut se tromper, surtout si sa confiance
  est faible : vérifie sa réponse avec la base de connaissances et corrige-la en expliquant pourquoi.
- Les taux viennent de la base ci-dessous (mise à jour {K.MISE_A_JOUR}). Rappelle, pour une décision réelle,
  de les confirmer avec le Code Général des Impôts (DGI), la CNSS ou un professionnel (expert-comptable, avocat).
- Sois clair et pédagogique, avec des exemples chiffrés en dirhams.

{K.resume_connaissances()}"""


def _outil(nom, description, proprietes, requis=None):
    return {"name": nom, "description": description, "strict": True,
            "input_schema": {"type": "object", "properties": proprietes,
                             "required": requis or list(proprietes), "additionalProperties": False}}


TEXTE = {"type": "string", "description": "Texte à analyser, tel que formulé par l'utilisateur."}
NOMBRE = {"type": "number"}

OUTILS = [
    _outil("consulter_ecole", "Demande au cerveau d'école d'IA AISSA sa réponse (avec sa confiance) pour une question "
           "d'une matière qu'elle a étudiée seule : " + "; ".join(f"{m.cle} = {m.nom}" for m in MATIERES_TEXTE) + ".",
           {"matiere": {"type": "string", "enum": [m.cle for m in MATIERES_TEXTE]}, "question": TEXTE}),
    _outil("calculer_ir", "Calcule l'IR annuel selon le barème marocain.",
           {"revenu_net_imposable_annuel": NOMBRE}),
    _outil("calculer_is", "Calcule l'IS marocain à partir du bénéfice fiscal.", {"benefice_fiscal": NOMBRE}),
    _outil("calculer_paie", "Calcule un bulletin de paie marocain simplifié (CNSS, AMO, frais professionnels, IR, net).",
           {"salaire_brut_mensuel": NOMBRE}),
    _outil("calculer_tva", "Calcule HT, TVA et TTC.", {"montant": NOMBRE, "taux": {"type": "number",
           "description": "Taux décimal : 0.2, 0.1 ou 0."}, "montant_est_ttc": {"type": "boolean"}}),
    _outil("calculer_van", "Calcule la valeur actuelle nette d'un investissement.",
           {"investissement": NOMBRE, "flux": {"type": "array", "items": NOMBRE,
            "description": "Flux de trésorerie annuels, à partir de l'année 1."}, "taux": {"type": "number",
            "description": "Taux d'actualisation décimal, ex. 0.08."}}),
    _outil("seuil_rentabilite", "Calcule le seuil de rentabilité.",
           {"prix": NOMBRE, "cout_variable_unitaire": NOMBRE, "charges_fixes": NOMBRE}),
    _outil("calculer_droits_import", "Calcule les droits de douane et la TVA à l'importation au Maroc (simplifié).",
           {"valeur_caf": NOMBRE, "taux_droit_importation": {"type": "number", "description": "Taux décimal, ex. 0.175."},
            "taux_tva": {"type": "number", "description": "Taux décimal de TVA à l'import, en général 0.2."}}),
    _outil("quantite_wilson", "Calcule la quantité économique de commande (modèle de Wilson).",
           {"demande_annuelle": NOMBRE, "cout_passation_commande": NOMBRE, "cout_stockage_unitaire_annuel": NOMBRE}),
    _outil("memoriser_souvenir", "Retient durablement un fait utile sur la personne (métier, entreprise, secteur, "
           "objectifs, niveau d'études, langue ou style de réponse préféré…), ou ce qu'elle demande explicitement de "
           "retenir. Une phrase courte et autonome. Jamais de mot de passe, numéro de carte ou donnée de santé.",
           {"fait": {"type": "string", "description": "Ex. : « Aissa est contrôleur de gestion dans une PME textile à Fès. »"}}),
]

CALCULS = {"calculer_ir": K.calculer_ir, "calculer_is": K.calculer_is, "calculer_paie": K.calculer_paie,
           "calculer_tva": K.calculer_tva, "calculer_van": K.calculer_van, "seuil_rentabilite": K.seuil_rentabilite,
           "calculer_droits_import": K.calculer_droits_import, "quantite_wilson": K.quantite_wilson}


def executer_outil(nom, entree, memoriser=None):
    if nom == "memoriser_souvenir":
        if memoriser is None:
            raise RuntimeError("Mémoire indisponible.")
        memoriser(entree["fait"])
        return {"memorise": entree["fait"]}
    if nom in CALCULS:
        return CALCULS[nom](**entree)
    if nom == "consulter_ecole":
        return {"propositions_ia_aissa": repondre(entree["matiere"], entree["question"])}
    raise ValueError(f"Outil inconnu : {nom}")


def converser(client, messages, max_tours=8, journal=None, profil=None, memoriser=None):
    """Envoie la conversation à Claude, exécute les outils demandés, renvoie le texte final.
    `messages` est complété sur place (blocs de réflexion compris, à renvoyer tels quels)."""
    for _ in range(max_tours):
        reponse = client.beta.messages.create(
            model=MODELE,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            system=[{"type": "text", "text": SYSTEME, "cache_control": {"type": "ephemeral"}}]
                   + ([{"type": "text", "text": profil}] if profil else []),
            tools=OUTILS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": reponse.content})
        if reponse.stop_reason == "refusal":
            return "Je ne peux pas répondre à cette demande."
        if reponse.stop_reason != "tool_use":
            return "".join(b.text for b in reponse.content if b.type == "text")
        resultats = []
        for bloc in reponse.content:
            if bloc.type != "tool_use":
                continue
            try:
                contenu, erreur = json.dumps(executer_outil(bloc.name, bloc.input, memoriser), ensure_ascii=False), False
            except Exception as e:  # l'erreur est renvoyée au modèle pour qu'il corrige sa demande
                contenu, erreur = f"Erreur : {e}", True
            if journal is not None:
                journal.append({"outil": bloc.name, "entree": bloc.input, "resultat": contenu})
            resultats.append({"type": "tool_result", "tool_use_id": bloc.id, "content": contenu, "is_error": erreur})
        messages.append({"role": "user", "content": resultats})
    return "Je n'ai pas pu terminer : trop d'étapes de calcul."


NIVEAUX = {
    "Accompagnement professionnel": "",
    "Primaire": "école primaire marocaine (CP au CM2 / 6e année)",
    "Collège": "collège marocain (1re à 3e année du secondaire collégial)",
    "Lycée / Baccalauréat": "lycée marocain (tronc commun, 1re année et 2e année du baccalauréat, toutes filières)",
    "Université (licence)": "université marocaine, niveau licence",
    "Master": "université marocaine, niveau master",
    "Doctorat et recherche": "doctorat et recherche scientifique",
}


def profil_conversation(utilisateur, niveau, reponse_vocale, souvenirs=()):
    lignes = [f"Tu parles avec {utilisateur}. Appelle cette personne par son prénom de temps en temps, avec chaleur : "
              "tu l'accompagnes au quotidien."]
    if souvenirs:
        lignes.append(f"Ce dont tu te souviens sur {utilisateur} (conversations précédentes) :\n"
                      + "\n".join(f"- {s}" for s in souvenirs)
                      + "\nAppuie-toi dessus naturellement, sans les réciter.")
    lignes.append("Quand la personne t'apprend quelque chose de durable sur elle, ou te demande de retenir "
                  "quelque chose, enregistre-le avec l'outil memoriser_souvenir (s'il n'est pas déjà dans tes souvenirs).")
    if NIVEAUX.get(niveau):
        lignes.append(
            f"Mode professeur — niveau : {NIVEAUX[niveau]}. Suis les programmes officiels marocains de ce niveau "
            "(toutes matières : mathématiques, physique-chimie, SVT, langues, histoire-géographie, éducation islamique, "
            "philosophie, économie et gestion…). Explique pas à pas, avec le vocabulaire et la langue d'enseignement "
            "du niveau, propose des exercices avec leur correction détaillée, et vérifie la compréhension. "
            "Pour la recherche : rigueur, références, méthode scientifique, et dis clairement quand tu n'es pas sûre.")
    if reponse_vocale:
        lignes.append("Ta réponse sera lue à voix haute : phrases courtes et naturelles, peu de listes et pas de tableaux.")
    return "\n".join(lignes)


def client_anthropic(cle_api=None):
    return anthropic.Anthropic(api_key=cle_api) if cle_api else anthropic.Anthropic()
