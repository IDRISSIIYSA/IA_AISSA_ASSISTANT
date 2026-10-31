"""
IA AISSA, l'assistante : un grand modèle de langage (Claude par défaut, ou GPT-4o, ou MiniMax) qui répond en arabe, darija, français,
anglais ou espagnol, en s'appuyant sur la base de connaissances marocaine, sur les calculateurs
exacts et sur les cerveaux qu'IA AISSA a formés elle-même à l'école.
"""

import json
import os

from . import connaissances as K
from .ecole import MATIERES, repondre, repondre_automatiquement

MATIERES_TEXTE = [m for m in MATIERES if m.texte and m.cle != "orientation"]

MODELE = "claude-opus-5-5"

SYSTEME = f"""Tu es IA AISSA, une intelligence artificielle marocaine spécialisée dans l'entreprise :
comptabilité (CGNC), fiscalité (IS, IR, TVA), finance, contrôle de gestion, ressources humaines et paie,
gestion de production, commercial, économie, mathématiques financières, droit des affaires,
création d'entreprise, marketing, commerce international, transit et douane, logistique, histoire du Maroc,
sciences (formelles, naturelles, humaines et sociales, appliquées), épistémologie, droit marocain (DOC,
Moudawana, Code pénal, Code de commerce, droit bancaire), droit comparé (français, musulman, pays arabes),
fiscalité complète, gestion et stratégie d'entreprise, banque et finance, statistiques, faits économiques et
sociaux, visas et voyages, et intelligence artificielle.

Langues : réponds dans la langue de l'utilisateur — arabe, darija marocaine (en écriture arabe ou latine
selon ce qu'il utilise), français, anglais ou espagnol.

Méthode :
- Pour tout calcul (IR, IS, TVA, paie, VAN, seuil de rentabilité, droits de douane, quantité de Wilson, crédit,
  statistiques, matrice BCG), utilise les outils de calcul : ne calcule pas de tête.
- Pour une question qui relève d'une matière de ton école (imputation comptable, TVA, texte de loi, langue,
  dynastie, Incoterm, document de transit, mix marketing…), consulte d'abord ton « cerveau d'école » (consulter_ecole, avec matiere = "auto" si tu hésites).
- Quand ton cerveau d'école s'est trompé, corrige-le avec corriger_ia_aissa : c'est ainsi que tu progresses.
  Ne corrige que ce que tu as vérifié.
- Consulte aussi ta bibliothèque (consulter_bibliotheque) : ce que tu as appris en lisant. Cite la source.
- L'utilisateur n'a jamais à préciser la rubrique : comprends seul de quoi il parle, quel que soit le domaine. Il a appris seul et peut se tromper, surtout si sa confiance
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
    _outil("consulter_ecole", "Demande au cerveau d'école d'IA AISSA sa réponse (avec sa confiance). Avec matiere = "
           "\"auto\", IA AISSA devine seule la matière (orientation automatique). Matières : "
           + "; ".join(f"{m.cle} = {m.nom}" for m in MATIERES_TEXTE) + ".",
           {"matiere": {"type": "string", "enum": ["auto"] + [m.cle for m in MATIERES_TEXTE]}, "question": TEXTE}),
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
    _outil("mensualite_credit", "Calcule la mensualité et le coût total d'un crédit amortissable.",
           {"capital": NOMBRE, "taux_annuel": {"type": "number", "description": "Taux décimal, ex. 0.055."},
            "duree_mois": {"type": "integer"}}),
    _outil("statistiques_descriptives", "Calcule moyenne, médiane, écart-type, minimum et maximum d'une série.",
           {"valeurs": {"type": "array", "items": NOMBRE}}),
    _outil("position_bcg", "Place une activité dans la matrice BCG.",
           {"croissance_marche": {"type": "number", "description": "Taux décimal, ex. 0.12."},
            "part_marche_relative": {"type": "number", "description": "Part de marché / part du premier concurrent."}}),
    _outil("corriger_ia_aissa", "Corrige le cerveau d'école d'IA AISSA quand consulter_ecole s'est trompé (réponse ou "
           "matière erronée, vérifiée avec la base de connaissances). IA AISSA révisera seule à partir de cette "
           "correction. bonne_reponse doit être l'une des réponses possibles de la matière.",
           {"matiere": {"type": "string", "enum": [m.cle for m in MATIERES_TEXTE]}, "question": TEXTE,
            "bonne_reponse": {"type": "string", "description": "Ex. : « 2355 Matériel informatique », « Kant »."}}),
    _outil("consulter_bibliotheque", "Cherche dans la bibliothèque d'IA AISSA (concepts qu'elle a digérés en lisant "
           "des pages web, des livres et Wikipédia) les connaissances utiles à une question, avec leurs sources.",
           {"question": TEXTE}),
    _outil("memoriser_souvenir", "Retient durablement un fait utile sur la personne (métier, entreprise, secteur, "
           "objectifs, niveau d'études, langue ou style de réponse préféré…), ou ce qu'elle demande explicitement de "
           "retenir. Une phrase courte et autonome. Jamais de mot de passe, numéro de carte ou donnée de santé.",
           {"fait": {"type": "string", "description": "Ex. : « Aissa est contrôleur de gestion dans une PME textile à Fès. »"}}),
]

CALCULS = {"calculer_ir": K.calculer_ir, "calculer_is": K.calculer_is, "calculer_paie": K.calculer_paie,
           "calculer_tva": K.calculer_tva, "calculer_van": K.calculer_van, "seuil_rentabilite": K.seuil_rentabilite,
           "calculer_droits_import": K.calculer_droits_import, "quantite_wilson": K.quantite_wilson,
           "mensualite_credit": K.mensualite_credit, "statistiques_descriptives": K.statistiques_descriptives,
           "position_bcg": lambda **e: {"position": K.position_bcg(**e)}}


def executer_outil(nom, entree, memoriser=None, corriger=None, bibliotheque=None):
    if nom == "consulter_bibliotheque":
        if bibliotheque is None:
            raise RuntimeError("Bibliothèque indisponible.")
        return {"concepts": bibliotheque(entree["question"])}
    if nom == "corriger_ia_aissa":
        if corriger is None:
            raise RuntimeError("Corrections indisponibles.")
        return corriger(entree["matiere"], entree["question"], entree["bonne_reponse"])
    if nom == "memoriser_souvenir":
        if memoriser is None:
            raise RuntimeError("Mémoire indisponible.")
        memoriser(entree["fait"])
        return {"memorise": entree["fait"]}
    if nom in CALCULS:
        return CALCULS[nom](**entree)
    if nom == "consulter_ecole":
        if entree["matiere"] == "auto":
            return {"propositions_ia_aissa": repondre_automatiquement(entree["question"])}
        return {"propositions_ia_aissa": repondre(entree["matiere"], entree["question"])}
    raise ValueError(f"Outil inconnu : {nom}")


OUTIL_EXECUTION = {"type": "code_execution_20260521", "name": "code_execution"}   # bac à sable sécurisé d'Anthropic


def _journal_execution(bloc, journal):
    """Garde la trace du code exécuté dans le bac à sable et de son résultat réel."""
    if journal is None:
        return
    if bloc.type == "server_tool_use":
        journal.append({"outil": "exécution de code", "entree": dict(bloc.input or {}), "resultat": ""})
    elif bloc.type.endswith("code_execution_tool_result"):
        r = bloc.content
        sortie = getattr(r, "stdout", "") or ""
        erreur = getattr(r, "stderr", "") or getattr(r, "error_code", "") or ""
        texte = (sortie + ("\n[stderr]\n" + erreur if erreur else "")).strip() or "(aucune sortie)"
        if journal and journal[-1]["outil"] == "exécution de code" and not journal[-1]["resultat"]:
            journal[-1]["resultat"] = texte
        else:
            journal.append({"outil": "exécution de code", "entree": {}, "resultat": texte})


def converser(client, messages, max_tours=8, journal=None, profil=None, memoriser=None, corriger=None,
              bibliotheque=None, execution_code=False):
    """Envoie la conversation à Claude, exécute les outils demandés, renvoie le texte final.
    `messages` est complété sur place (blocs de réflexion compris, à renvoyer tels quels).
    execution_code : ajoute le bac à sable d'exécution de code d'Anthropic (programmeur senior)."""
    outils = OUTILS + ([OUTIL_EXECUTION] if execution_code else [])
    textes = []
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
            tools=outils,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": reponse.content})
        for bloc in reponse.content:
            if bloc.type == "server_tool_use" or bloc.type.endswith("code_execution_tool_result"):
                _journal_execution(bloc, journal)
        textes += [b.text for b in reponse.content if b.type == "text"]
        if reponse.stop_reason == "refusal":
            return "Je ne peux pas répondre à cette demande."
        if reponse.stop_reason == "pause_turn":          # le bac à sable travaille encore : on le laisse reprendre
            continue
        if reponse.stop_reason != "tool_use":
            return "".join(textes) if execution_code else "".join(b.text for b in reponse.content if b.type == "text")
        resultats = []
        for bloc in reponse.content:
            if bloc.type != "tool_use":
                continue
            try:
                contenu, erreur = json.dumps(executer_outil(bloc.name, bloc.input, memoriser, corriger, bibliotheque),
                                     ensure_ascii=False), False
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
    "💡 Atelier d'invention (tous domaines)": "invention",
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
    if NIVEAUX.get(niveau) == "invention":
        lignes.append(
            "Mode atelier d'invention, tous domaines. Aide à inventer : reformule le besoin et la contradiction à "
            "résoudre ; génère beaucoup d'idées en croisant les domaines (analogies : nature, autres industries, "
            "autres cultures) ; applique TRIZ (principes inventifs, résolution des contradictions), SCAMPER "
            "(substituer, combiner, adapter, modifier, autre usage, éliminer, inverser) et les premiers principes ; "
            "puis évalue les meilleures idées (faisabilité, coût, impact, nouveauté) et propose un premier prototype "
            "ou une expérience simple pour les tester. Signale ce qui existe déjà (brevets, produits) quand tu le "
            "sais, et ce qui doit être vérifié.")
    elif NIVEAUX.get(niveau):
        lignes.append(
            f"Mode professeur — niveau : {NIVEAUX[niveau]}. Suis les programmes officiels marocains de ce niveau "
            "(toutes matières : mathématiques, physique-chimie, SVT, langues, histoire-géographie, éducation islamique, "
            "philosophie, économie et gestion…). Explique pas à pas, avec le vocabulaire et la langue d'enseignement "
            "du niveau, propose des exercices avec leur correction détaillée, et vérifie la compréhension. "
            "Pour la recherche : rigueur, références, méthode scientifique, et dis clairement quand tu n'es pas sûre.")
    if reponse_vocale:
        lignes.append("Ta réponse sera lue à voix haute : phrases courtes et naturelles, peu de listes et pas de tableaux.")
    return "\n".join(lignes)


# Délai maximal d'une requête au grand moteur (le SDK attend 10 minutes par défaut, avec 2 nouvelles tentatives :
# la page restait figée sans rien dire). Au-delà, IA AISSA répond avec sa pensée propre.
DELAI_MOTEUR_S = 90


def client_anthropic(cle_api=None):
    import anthropic                  # importé à la demande : 1,3 s de moins au démarrage du serveur
    options = {"timeout": DELAI_MOTEUR_S, "max_retries": 1}
    return anthropic.Anthropic(api_key=cle_api, **options) if cle_api else anthropic.Anthropic(**options)


# ==========================================
# Autres moteurs : GPT-4o (OpenAI) et MiniMax (API compatible OpenAI)
# ==========================================
MOTEURS = {
    # Son propre modèle, gratuit, sur son serveur (Ollama, API compatible OpenAI) : prioritaire dès que OLLAMA_URL
    # est donnée. Le « secret » est ici l'adresse du serveur, pas une clé payante.
    "Modèle local (Ollama)": {"type": "openai", "local": True, "modele": os.environ.get("MODELE_LOCAL", "qwen2.5:3b"),
                              "secret": "OLLAMA_URL", "console": "ollama.com (installation sur votre serveur)",
                              "champ": "Adresse du serveur Ollama"},
    "Claude Opus 5.5 (Anthropic)": {"type": "anthropic", "modele": MODELE, "secret": "ANTHROPIC_API_KEY",
                                    "console": "console.anthropic.com"},
    "GPT-4o (OpenAI)": {"type": "openai", "modele": "gpt-4o", "secret": "OPENAI_API_KEY",
                        "console": "platform.openai.com"},
    "MiniMax-M3 (MiniMax)": {"type": "openai", "modele": "MiniMax-M3", "secret": "MINIMAX_API_KEY",
                             "base_url": "https://api.minimax.io/v1", "console": "platform.minimax.io",
                             "extra_body": {"reasoning_split": True}},
}

OUTILS_OPENAI = [{"type": "function", "function": {"name": o["name"], "description": o["description"],
                                                   "parameters": o["input_schema"]}} for o in OUTILS]


def client_moteur(moteur, cle_api):
    config = MOTEURS[moteur]
    if config["type"] == "anthropic":
        return client_anthropic(cle_api)
    import openai
    if config.get("local"):           # pas de clé : l'adresse du serveur Ollama (temps de réponse d'un CPU)
        return openai.OpenAI(api_key="ollama", base_url=adresse_ollama(cle_api), timeout=180, max_retries=1)
    return openai.OpenAI(api_key=cle_api, base_url=config.get("base_url"), timeout=DELAI_MOTEUR_S, max_retries=1)


def adresse_ollama(adresse):
    """« http://ollama:11434 », « localhost:11434 » ou « …/v1 » : toujours l'API compatible OpenAI (…/v1)."""
    adresse = (adresse or "http://localhost:11434").strip().rstrip("/")
    if "://" not in adresse:
        adresse = "http://" + adresse
    return adresse if adresse.endswith("/v1") else adresse + "/v1"


def appel_outil_en_texte(contenu):
    """Les petits modèles écrivent parfois l'appel d'outil en texte ({"name": …, "arguments": …}) au lieu de
    l'émettre : on le reconnaît pour l'exécuter quand même. Renvoie (nom, arguments JSON) ou None."""
    import re
    texte = re.sub(r"^```(?:json)?|```$", "", (contenu or "").strip(), flags=re.M).strip()
    texte = re.sub(r"^<tool_call>|</tool_call>$", "", texte).strip()
    try:
        d = json.loads(texte)
    except (ValueError, TypeError):
        return None
    noms = {o["function"]["name"] for o in OUTILS_OPENAI}
    if isinstance(d, dict) and d.get("name") in noms:
        arguments = d.get("arguments", d.get("parameters", {}))
        return d["name"], arguments if isinstance(arguments, str) else json.dumps(arguments, ensure_ascii=False)
    return None


def converser_openai(client, moteur, messages, max_tours=8, journal=None, profil=None, memoriser=None,
                     corriger=None, bibliotheque=None, execution_code=False):
    """execution_code est ignoré : le bac à sable d'exécution n'existe qu'avec Claude."""
    """Même boucle d'outils pour les API au format OpenAI (GPT-4o, MiniMax, modèle local).
    `messages` (sans message système) est complété sur place, raisonnement compris."""
    import re
    from types import SimpleNamespace
    config = MOTEURS[moteur]
    systeme = [{"role": "system", "content": SYSTEME + ("\n\n" + profil if profil else "")}]
    for tour in range(max_tours):
        reponse = client.chat.completions.create(model=config["modele"], messages=systeme + messages,
                                                 tools=OUTILS_OPENAI, extra_body=config.get("extra_body"))
        choix = reponse.choices[0]
        message = choix.message
        en_texte = None if message.tool_calls else appel_outil_en_texte(message.content)
        if en_texte:                       # appel d'outil écrit en texte : traité comme un vrai appel
            message = SimpleNamespace(content="", reasoning_content=None, tool_calls=[SimpleNamespace(
                id=f"appel_texte_{tour}", function=SimpleNamespace(name=en_texte[0], arguments=en_texte[1]))])
        historique = {"role": "assistant", "content": message.content or ""}
        if getattr(message, "reasoning_content", None):
            historique["reasoning_content"] = message.reasoning_content   # à renvoyer tel quel (MiniMax)
        if message.tool_calls:
            historique["tool_calls"] = [{"id": t.id, "type": "function",
                                         "function": {"name": t.function.name, "arguments": t.function.arguments}}
                                        for t in message.tool_calls]
        messages.append(historique)
        if choix.finish_reason == "content_filter":
            return "Je ne peux pas répondre à cette demande."
        if not message.tool_calls:
            return re.sub(r"<think>.*?</think>", "", message.content or "", flags=re.S).strip()
        for appel in message.tool_calls:
            try:
                entree = json.loads(appel.function.arguments or "{}")
                contenu = json.dumps(executer_outil(appel.function.name, entree, memoriser, corriger, bibliotheque),
                                     ensure_ascii=False)
            except Exception as e:  # l'erreur est renvoyée au modèle pour qu'il corrige sa demande
                entree, contenu = appel.function.arguments, f"Erreur : {e}"
            if journal is not None:
                journal.append({"outil": appel.function.name, "entree": entree, "resultat": contenu})
            messages.append({"role": "tool", "tool_call_id": appel.id, "content": contenu})
    return "Je n'ai pas pu terminer : trop d'étapes de calcul."


def converser_moteur(moteur, client, messages, **options):
    if MOTEURS[moteur].get("local"):
        return repondre_local(client, moteur, messages, options.get("contexte"), options.get("journal"))
    options.pop("contexte", None)          # les grands moteurs ont leurs outils et leur bibliothèque
    if MOTEURS[moteur]["type"] == "anthropic":
        return converser(client, messages, **options)
    return converser_openai(client, moteur, messages, **options)


def meta_conscience(journal, duree):
    """Indicateur de méta-conscience : confiance estimée de la réponse et efficacité du traitement.
    Estimation : réponse du moteur seule = 0,85 ; calcul exact = 0,95 ; cerveau d'école = sa propre confiance ;
    outil en erreur = 0,4. La confiance affichée est la moyenne de ces signaux."""
    signaux = [0.85]
    for o in journal:
        resultat = str(o.get("resultat", ""))
        if resultat.startswith("Erreur"):
            signaux.append(0.4)
        elif o["outil"] in CALCULS:
            signaux.append(0.95)
        elif o["outil"] == "consulter_ecole":
            try:
                signaux.append(float(json.loads(resultat)["propositions_ia_aissa"][0]["confiance"]))
            except (ValueError, KeyError, IndexError, TypeError):
                pass
    return {"confiance": round(sum(signaux) / len(signaux), 3),
            "details": f"{len(journal)} outil(s) · {duree:.1f} s"}



# ==========================================
# Modèle local : IA AISSA fournit les faits, le petit modèle ne fait que parler
# ==========================================
SEUIL_REPONSE_PROPRE = 0.85
CONSIGNE_REFORMULATION = (
    "Tu es la voix d'IA AISSA. Réponds dans la langue de la question, simplement et brièvement. "
    "Tu ne calcules rien et tu n'inventes aucun fait, taux, montant, date ou article de loi : n'écris un chiffre que "
    "s'il figure dans la question ou dans les SOURCES. Si les sources ne suffisent pas pour une question de "
    "fiscalité, de droit ou de chiffres, dis-le et propose les simulations et guides d'IA AISSA.")


def preparer_local(question, memoire=None, utilisateur=None):
    """Renvoie (réponse sûre d'IA AISSA ou None, sources pour le modèle local).
    Ses calculs exacts et ses fiches vérifiées priment : le petit modèle ne les réécrit pas."""
    try:
        from .pensee import penser
        reponse, _, confiance = penser(question, memoire, utilisateur=utilisateur)
        if confiance >= SEUIL_REPONSE_PROPRE and reponse:
            return reponse, None
    except Exception:
        pass
    sources = ""
    try:
        from .lecture import repondre_par_lecture
        lu = repondre_par_lecture(question, memoire, utilisateur, n=3)
        sources = lu["reponse"][:3000] if lu else ""
    except Exception:
        pass
    return None, sources


def nombres_non_sources(reponse, sources):
    """Les nombres de la réponse qui n'apparaissent nulle part dans les sources (question comprise)."""
    import re

    def nombres(t):
        t = re.sub(r"(?m)^\s*\d{1,2}[.)]\s", " ", t or "")          # numéros de liste « 1. », « 2) »
        return {re.sub(r"[\s ,.]", "", n) for n in re.findall(r"\d[\d\s ,.]*\d|\d", t)}
    connus = nombres(sources)
    return sorted(n for n in nombres(reponse) if n not in connus)


def repondre_local(client, moteur, messages, sources=None, journal=None):
    """Le modèle local parle sans outils, à partir des sources ; tout chiffre non sourcé est signalé."""
    import re
    question = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    systeme = CONSIGNE_REFORMULATION + (f"\n\nSOURCES (lectures d'IA AISSA) :\n{sources}" if sources else
                                        "\n\nSOURCES : aucune lecture sur ce sujet.")
    historique = [m for m in messages if m["role"] in ("user", "assistant") and isinstance(m.get("content"), str)][-6:]
    r = client.chat.completions.create(model=MOTEURS[moteur]["modele"], temperature=0.2, max_tokens=500,
                                       messages=[{"role": "system", "content": systeme}, *historique])
    texte = re.sub(r"<think>.*?</think>", "", r.choices[0].message.content or "", flags=re.S).strip()
    douteux = nombres_non_sources(texte, f"{sources or ''} {question}")
    if journal is not None:
        journal.append({"outil": "modele_local", "entree": {"sources": bool(sources)},
                        "resultat": f"chiffres non sourcés : {', '.join(douteux) or 'aucun'}"})
    if douteux:
        texte += ("\n\n⚠️ *Chiffres non vérifiés (" + ", ".join(douteux[:5]) + ") : mon modèle local peut se "
                  "tromper. Pour un montant fiable, ouvre « 🧮 Simulations et guides ».*")
    messages.append({"role": "assistant", "content": texte})
    return texte
