"""
L'espace unique d'IA AISSA (« Seul Espace ») : l'alien dans son portail cosmique et une seule ligne de conversation.

Tout passe par cette ligne : texte, voix (🎙️) et fichiers (📎). IA AISSA choisit seule son rôle
(programmeur, prof/savant, contrôleur de gestion, inventeur, lecteur, compagnon), répond par écrit et à voix haute,
calcule, exécute du code (avec Claude, dans le bac à sable d'Anthropic), lit, invente, et apprend de chaque échange
(lacunes, corrections, étude autonome, lectures). Les réglages tiennent dans un seul panneau ⚙️.
"""

import json
import random
import time

import anthropic
import openai
import pandas as pd
import streamlit as st

from .acces import verifier_acces
from .assistant import MOTEURS, NIVEAUX, client_moteur, converser_moteur, meta_conscience, profil_conversation
from .autonomie import SEUIL_ETUDE, etudier_seule, noter_si_lacune
from .avatar import avatar
from .bibliotheque import ErreurBroutage, brouter_fichier, brouter_lien, chercher, digerer
from .corrections import corriger, reviser_tout
from .croissance import afficher as afficher_croissance
from .croissance import serie as serie_croissance
from .ecole import MATIERES, charger, repondre
from .espace import EXTENSIONS_DONNEES, EXTENSIONS_LECTURE, ROLES, analyser_controle, detecter_role, intention, \
    reponse_locale, urls
from .invention import annonce_darija, debattre, evoluer
from .langues import LANGUES
from .memoire import historique_api
from .partage import broutage_autonome, etat_memoire, memoire, secret
from .parole import charger_oreille, synthetiser, transcrire
from .reconnaissance import Yeux, moment_de_la_journee, qui_est_ce
from .visage import SALUTATIONS
from .voix import atelier_prononciation

STYLE = """<style>
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
  .block-container { padding-top: 1.2rem; max-width: 860px; }
  .role { display:inline-block; font-size:13px; padding:3px 10px; border-radius:999px;
          border:1px solid rgba(56,189,248,.5); background: rgba(56,189,248,.08); }
</style>"""


@st.cache_resource(show_spinner="IA AISSA apprend à écouter (premier chargement)…")
def oreille():
    return charger_oreille()


@st.cache_resource(show_spinner="IA AISSA ouvre les yeux (premier chargement)…")
def yeux():
    return Yeux()


def _dire(texte, langue):
    try:
        return synthetiser(texte, langue)
    except Exception:
        return None                # sans service vocal, la voix du navigateur prend le relais


def ouvrir_conversation(utilisateur, conversation_id):
    lignes = memoire().messages_de(utilisateur, conversation_id) if conversation_id else []
    st.session_state["conversation_id"] = conversation_id
    st.session_state["affichage"] = [{"role": l["role"], "texte": l["texte"], "langue": "Français"} for l in lignes]
    st.session_state["messages_api"] = historique_api(lignes)
    st.session_state["moteur_historique"] = None


# ==========================================
# Le panneau unique des réglages
# ==========================================
def reglages(utilisateur):
    mem = memoire()
    with st.popover("⚙️ Réglages", width="content"):
        moteurs = list(MOTEURS)
        moteur = st.selectbox("🧠 Moteur", moteurs, index=moteurs.index(st.session_state.get("moteur_choisi", moteurs[0])))
        st.session_state["moteur_choisi"] = moteur
        config = MOTEURS[moteur]
        cle_visite = f"cle_visite_{config['secret']}"
        cle_api = secret(config["secret"]) or st.session_state.get(cle_visite)
        if not cle_api:
            saisie = st.text_input(f"Clé API ({moteur.split(' (')[0]})", type="password",
                                   help=f"Créez une clé sur {config['console']} ; gardée le temps de la visite.")
            if saisie:
                st.session_state[cle_visite] = cle_api = saisie.strip()
        elif not secret(config["secret"]) and st.button("Changer de clé"):
            st.session_state.pop(cle_visite, None)
            st.rerun()
        modes = ["✍️🔊 Écrites et vocales", "✍️ Écrites", "🔊 Vocales"]
        mode = st.radio("Réponses", modes, index=modes.index(st.session_state.get("mode_reponse", modes[0])),
                        horizontal=True)
        st.session_state["mode_reponse"] = mode
        niveaux = list(NIVEAUX)
        niveau = st.selectbox("Accompagnement (niveau scolaire, invention…)", niveaux,
                              index=niveaux.index(st.session_state.get("niveau", niveaux[0])))
        st.session_state["niveau"] = niveau
        voir_outils = st.toggle("Montrer le raisonnement (outils)", value=st.session_state.get("voir_outils", False))
        st.session_state["voir_outils"] = voir_outils
        etat_memoire(st)

        st.markdown("**📚 Conversations**")
        if st.button("➕ Nouvelle conversation", width="stretch"):
            ouvrir_conversation(utilisateur, None)
            st.rerun()
        for conv in mem.lister_conversations(utilisateur, limite=12):
            if st.button(conv["titre"][:45], key=f"conv{conv['id']}", width="stretch"):
                ouvrir_conversation(utilisateur, conv["id"])
                st.rerun()

        st.markdown("**🧠 Ce dont je me souviens**")
        for s in mem.souvenirs_de(utilisateur):
            c1, c2 = st.columns([6, 1])
            c1.caption(s["fait"])
            if c2.button("✖", key=f"oubli{s['id']}"):
                mem.oublier(utilisateur, s["id"])
                st.rerun()

        st.markdown("**📷 Me reconnaître**")
        photo = st.camera_input("Montre ton visage", label_visibility="collapsed")
        if photo is not None and st.session_state.get("photo_vue") != photo.file_id:
            st.session_state["photo_vue"] = photo.file_id
            empreinte = yeux().empreinte(photo.getvalue())
            if empreinte is None:
                st.warning("Je ne vois pas de visage.")
            else:
                qui, score = qui_est_ce(empreinte, mem.visages_connus())
                if qui:
                    texte = SALUTATIONS["Darija"][moment_de_la_journee()].format(nom=qui)
                    st.session_state["parole"] = {"texte": texte, "audio": _dire(texte, "Darija"), "voix": "ar-MA",
                                                  "nouveau": True}
                else:
                    mem.ajouter_visage(utilisateur, empreinte)
                    st.success(f"Visage mémorisé : je te reconnaîtrai, {utilisateur}.")
        image = st.file_uploader("🖼️ Mon visage d'alien (image)", type=["png", "jpg", "jpeg", "webp"])
        if image is not None and st.button("Utiliser cette image"):
            mem.sauver_media("avatar", image.getvalue(), image.type or "image/png")
            st.rerun()
    return {"moteur": moteur, "config": config, "cle_api": cle_api, "niveau": niveau, "voir_outils": voir_outils,
            "ecrit": "Écrites" in mode, "vocal": "Vocales" in mode or "vocales" in mode}


# ==========================================
# Les éléments affichés dans la conversation
# ==========================================
def afficher_element(e, cle):
    t = e["type"]
    if e.get("titre") and t not in ("telechargement",):
        st.markdown(f"**{e['titre']}**")
    if t == "metriques":
        for col, (libelle, valeur) in zip(st.columns(len(e["valeurs"])), e["valeurs"]):
            col.metric(libelle, valeur)
    elif t == "graphique":
        st.line_chart(e["donnees"])
    elif t == "tableau":
        st.dataframe(e["donnees"], hide_index=True, width="stretch")
    elif t == "liste":
        st.markdown("\n".join(f"- {l}" for l in e["lignes"]) or "_(rien)_")
    elif t == "telechargement":
        st.download_button(e["libelle"], e["donnees"], e["nom"], key=f"dl{cle}")
    elif t == "croissance":
        afficher_croissance(st, memoire())
    elif t == "bulletin":
        lignes = []
        for m in MATIERES:
            _, h = charger(m.cle)
            notes = [x["precision"] for x in h or [] if isinstance(x.get("pas"), int)]
            if notes:
                lignes.append({"Domaine": m.domaine, "Matière": m.nom, "Naissance": notes[0], "Aujourd'hui": notes[-1]})
        st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch", column_config={
            "Naissance": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
            "Aujourd'hui": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
    elif t == "atelier":
        st.iframe(atelier_prononciation(e["phrase"], LANGUES[e["langue"]]["voix"]), height=190)


def afficher_message(m, i, voir_outils):
    with st.chat_message(m["role"], avatar="👽" if m["role"] == "assistant" else None):
        if m.get("role_ia"):
            st.markdown(f'<span class="role">{ROLES[m["role_ia"]][0]}</span>', unsafe_allow_html=True)
        st.markdown(m["texte"])
        for k, e in enumerate(m.get("elements", [])):
            afficher_element(e, f"{i}_{k}")
        codes = [o for o in m.get("outils", []) if o["outil"] == "exécution de code"]
        for o in codes:
            with st.expander("💻 Code exécuté dans le bac à sable"):
                commande = o["entree"].get("command") or o["entree"].get("code") or json.dumps(o["entree"])
                st.code(commande)
                st.code(o["resultat"] or "(en cours)", language="text")
        autres = [o for o in m.get("outils", []) if o["outil"] != "exécution de code"]
        if voir_outils and autres:
            with st.expander(f"🔧 {len(autres)} outil(s) utilisé(s)"):
                for o in autres:
                    st.markdown(f"**{o['outil']}** `{o['entree']}`")
                    st.code(o["resultat"], language="json")
        if m.get("meta"):
            st.caption(f"🧠 Méta-conscience : confiance {m['meta']['confiance']:.0%} · {m['meta']['details']}")


# ==========================================
# Le traitement d'une demande : IA AISSA choisit son rôle et agit
# ==========================================
def converser_avec_moteur(r, utilisateur, question, role, journal):
    mem = memoire()
    if st.session_state.get("moteur_historique") not in (None, r["moteur"]):
        st.session_state["messages_api"] = historique_api(
            [{"role": m["role"], "texte": m["texte"]} for m in st.session_state["affichage"][:-1]])
    st.session_state["moteur_historique"] = r["moteur"]
    st.session_state["messages_api"].append({"role": "user", "content": question})
    profil = profil_conversation(utilisateur, r["niveau"], r["vocal"] and not r["ecrit"],
                                 [s["fait"] for s in mem.souvenirs_de(utilisateur)])
    profil += "\n" + ROLES[role][1]
    try:
        return converser_moteur(r["moteur"], client_moteur(r["moteur"], r["cle_api"]), st.session_state["messages_api"],
                                journal=journal, profil=profil,
                                memoriser=lambda fait: mem.memoriser(utilisateur, fait),
                                corriger=lambda cle, q, rep: corriger(mem, utilisateur, cle, q, rep),
                                bibliotheque=lambda q: chercher(mem, q),
                                execution_code=role == "programmeur" and r["config"]["type"] == "anthropic")
    except (anthropic.AuthenticationError, openai.AuthenticationError):
        st.session_state["messages_api"].pop()
        return "🔑 Ma clé API est refusée : vérifie-la dans ⚙️ Réglages."
    except (anthropic.APIError, openai.APIError) as e:
        st.session_state["messages_api"].pop()
        return f"Je n'arrive pas à joindre mon grand moteur ({e}). Réessaie dans un instant."


def traiter(r, utilisateur, texte, fichiers):
    """Renvoie (texte de la réponse, éléments à afficher, journal des outils, rôle, état du portail)."""
    mem = memoire()
    noms = [f.name for f in fichiers]
    role = detecter_role(texte, noms)
    if r["niveau"] and NIVEAUX.get(r["niveau"]) == "invention" and role == "compagnon":
        role = "inventeur"
    elements, journal = [], []
    client = client_moteur(r["moteur"], r["cle_api"]) if r["cle_api"] else None

    donnees = [f for f in fichiers if f.name.lower().endswith(EXTENSIONS_DONNEES)]
    lectures = [f for f in fichiers if f.name.lower().endswith(EXTENSIONS_LECTURE)]
    if donnees:
        resumes = []
        for f in donnees:
            try:
                resume, els, _ = analyser_controle(f.name, f.getvalue())
                resumes.append(resume)
                elements += els
            except Exception as e:
                resumes.append(f"Je n'ai pas pu analyser « {f.name} » : {e}")
        if client:
            reponse = converser_avec_moteur(r, utilisateur, (texte or "Analyse ces données de contrôle de gestion.")
                                            + "\n\nRésultats de mon agent de contrôle de gestion :\n" + "\n".join(resumes),
                                            "controleur", journal)
        else:
            reponse = "📊 " + "\n\n".join(resumes)
        return reponse, elements, journal, "controleur", "normal"

    if lectures or urls(texte):
        if not client:
            return ("📚 Pour manger et ruminer un document, j'ai besoin de mon grand moteur : ajoute une clé API dans "
                    "⚙️ Réglages."), [], [], "lecteur", "normal"
        bilans = []
        sources = [brouter_fichier(f.name, f.getvalue()) for f in lectures]
        for u in urls(texte):
            try:
                sources.append(brouter_lien(u))
            except (ErreurBroutage, Exception) as e:
                bilans.append(f"Je n'ai pas pu brouter {u} : {e}")
        for source, contenu in sources:
            try:
                b = digerer(mem, r["config"], client, source, contenu, utilisateur, nb_bouchees=4)
            except ErreurBroutage as e:
                bilans.append(f"{source} : {e}")
                continue
            bilans.append(f"J'ai mangé « {source} » : {b['concepts']} concept(s), {b['exercices']} exercice(s) pour "
                          f"mon école, {len(b['lacunes_comblees'])} lacune(s) comblée(s).")
            for d in b["digestions"]:
                elements.append({"type": "liste", "titre": f"🧬 {d['famille']} — digestion {d['confiance']:.0%}",
                                 "lignes": [f"**{c['nom']}** : {c.get('explication', '')}" for c in d["concepts"]]
                                 + ([f"💡 Analogie avec le contrôle de gestion : {d['analogie']}"] if d["analogie"] else [])})
        return "\n\n".join(bilans), elements, journal, "lecteur", "hyper"

    voulu = intention(texte)
    if voulu == "bulletin":
        return ("Voici où j'en suis : mes concepts par famille de sciences, ma vitesse d'apprentissage et mon bulletin "
                "de notes."), [{"type": "croissance"}, {"type": "bulletin", "titre": "📒 Mon bulletin"}], [], "savant", \
            "normal"
    if voulu == "bibliotheque":
        lignes = [f"{d['source']} — {d['famille']} ({len(json.loads(d['concepts']))} concept(s))"
                  for d in mem.digestions(30)]
        return ("Voici ce que j'ai lu et digéré." if lignes else "Je n'ai encore rien lu : donne-moi un lien ou un livre !"), \
            [{"type": "liste", "titre": "📚 Ma bibliothèque", "lignes": lignes}], [], "lecteur", "normal"
    if voulu == "prononciation":
        langue = next((l for l in LANGUES if l.lower() in texte.lower()), "Darija")
        phrase = random.choice(LANGUES[langue]["phrases"])
        return (f"Écoute-moi, puis répète : je te note sur 100 ({langue}).",
                [{"type": "atelier", "langue": langue, "phrase": phrase}], [], "savant", "normal")

    if role == "inventeur" and client:
        historique, meilleure = evoluer(r["config"], client, texte, generations=2, taille=4,
                                        inspirations=chercher(mem, texte, n=4))
        finale, debat, meta = debattre(r["config"], client, texte, meilleure, 3)
        mem.garder_idee(utilisateur, texte, finale["titre"], finale.get("description", ""), meta["confiance"],
                        meta["faisabilite"], json.dumps({"debat": debat, "meta": meta}, ensure_ascii=False))
        texte_darija, sens = annonce_darija(finale, meta, nom=utilisateur)
        elements = [{"type": "metriques", "valeurs": [("Confiance", f"{meta['confiance']:.0%}"),
                                                      ("Faisabilité", f"{meta['faisabilite']:.0%}"),
                                                      ("Doutes restants", str(meta["doutes_restants"]))]},
                    {"type": "liste", "titre": "⚔️ Débat intérieur (Critique)",
                     "lignes": [f"Tour {t['tour']} : " + " ; ".join(t["objections"]) for t in debat
                                if t["agent"] == "Critique"]}]
        return (f"{texte_darija}\n\n### 🏆 {finale['titre']}\n{finale.get('description', '')}\n\n_Proverbe : {sens}_",
                elements, journal, "inventeur", "hyper")

    if client:
        return converser_avec_moteur(r, utilisateur, texte, role, journal), [], journal, role, \
            "hyper" if role == "inventeur" else "normal"
    return reponse_locale(texte), [], [], role, "normal"


def apprendre_de_l_echange(r, utilisateur, question, texte):
    """Boucle d'auto-évolution : chaque échange nourrit ses lacunes, ses corrections et son étude autonome."""
    mem = memoire()
    if question:
        noter_si_lacune(mem, question)
    if not st.session_state.get("conversation_id"):
        st.session_state["conversation_id"] = mem.nouvelle_conversation(utilisateur, question or "Fichier")
    mem.ajouter_message(utilisateur, st.session_state["conversation_id"], "user", question or "(fichier)")
    mem.ajouter_message(utilisateur, st.session_state["conversation_id"], "assistant", texte)
    if mem.corrections_de(seulement_nouvelles=True):
        reviser_tout(mem)
    if r["cle_api"] and len(mem.lacunes_ouvertes(SEUIL_ETUDE)) >= SEUIL_ETUDE:
        try:
            etude = etudier_seule(mem, r["config"], client_moteur(r["moteur"], r["cle_api"]))
            st.toast(f"🧠 J'ai étudié seule {etude['etudiees']} question(s) : {etude['apprises']} nouvelle(s) "
                     "connaissance(s).")
        except Exception:
            pass          # l'étude autonome reprendra à la prochaine occasion


@st.fragment(run_every="60s")
def pouls_d_ia_aissa():
    """La croissance en direct : concepts maîtrisés et dernier repas du broutage autonome (rafraîchi chaque minute)."""
    etat = broutage_autonome()
    total = int(serie_croissance(memoire()).iloc[-1].sum())
    repas = etat.get("dernier_repas")
    if not etat.get("actif"):
        broutage = "broutage autonome en attente d'une clé API dans les secrets"
    elif repas:
        broutage = (f"dernier repas : « {repas['sujet']} » ({repas['source']}), {repas['concepts']} concept(s), "
                    f"{repas['injections']} analogie(s) injectée(s) dans l'atelier d'invention")
    else:
        broutage = "broutage autonome actif, premier repas en cours"
    st.caption(f"🌱 {total} concepts maîtrisés · {broutage}")


# ==========================================
# L'espace unique
# ==========================================
def espace_unique():
    st.set_page_config(page_title="IA AISSA", page_icon="👽", layout="centered", initial_sidebar_state="collapsed")
    st.markdown(STYLE, unsafe_allow_html=True)
    utilisateur = verifier_acces(st)
    mem = memoire()
    if "affichage" not in st.session_state:
        ouvrir_conversation(utilisateur, None)

    zone_alien = st.container()
    haut = st.columns([5, 1.4])
    with haut[1]:
        r = reglages(utilisateur)
    role_courant = st.session_state.get("role_ia", "compagnon")
    with haut[0]:
        st.markdown(f'<span class="role">{ROLES[role_courant][0]}</span>', unsafe_allow_html=True)
        pouls_d_ia_aissa()

    if "parole" not in st.session_state:          # première visite : l'alien salue, en darija et en français
        salut = SALUTATIONS["Darija"][moment_de_la_journee()].format(nom=utilisateur)
        texte = (f"{salut} — {SALUTATIONS['Français'][moment_de_la_journee()].format(nom=utilisateur)} Je suis IA AISSA. "
                 "Parle-moi, pose une question, demande du code, ou dépose un fichier de chiffres ou un livre.")
        st.session_state["parole"] = {"texte": texte, "audio": _dire(salut, "Darija"), "voix": "ar-MA",
                                      "nouveau": True}

    for i, m in enumerate(st.session_state["affichage"]):
        afficher_message(m, i, r["voir_outils"])

    saisie = st.chat_input("Parle-moi, écris, ou dépose un fichier (chiffres, livre, image)…",
                           accept_file="multiple", accept_audio=True, submit_mode="disable",
                           file_type=["csv", "xlsx", "xlsm", "xls", "pdf", "txt", "md", "html"])
    if saisie:
        texte = saisie.text or ""
        fichiers = list(saisie.files or [])
        if getattr(saisie, "audio", None) is not None:
            with st.spinner("👂 Je t'écoute…"):
                texte = f"{texte} {transcrire(oreille(), saisie.audio)[0]}".strip()
        affiche = (("🎙️ " if getattr(saisie, "audio", None) is not None else "") + texte
                   + "".join(f"\n\n📎 {f.name}" for f in fichiers)).strip()
        st.session_state["affichage"].append({"role": "user", "texte": affiche})
        afficher_message(st.session_state["affichage"][-1], len(st.session_state["affichage"]) - 1, False)
        debut = time.time()
        with st.spinner("🧠 IA AISSA réfléchit…"):
            reponse, elements, journal, role, etat = traiter(r, utilisateur, texte, fichiers)
        st.session_state["role_ia"] = role
        langue = repondre("langues", reponse[:300])[0]["reponse"]
        meta = meta_conscience(journal, time.time() - debut)
        message = {"role": "assistant", "texte": reponse, "elements": elements, "outils": journal, "langue": langue,
                   "meta": meta, "role_ia": role}
        st.session_state["affichage"].append(message)
        afficher_message(message, len(st.session_state["affichage"]) - 1, r["voir_outils"])
        apprendre_de_l_echange(r, utilisateur, texte, reponse)
        st.session_state["parole"] = {"texte": reponse, "audio": _dire(reponse, langue) if r["vocal"] else None,
                                      "voix": LANGUES[langue]["voix"], "nouveau": True, "etat": etat, "meta": meta}

    parole = st.session_state["parole"]
    image, type_image = mem.media("avatar")
    with zone_alien:
        st.iframe(avatar(parole["texte"][:400] + ("…" if len(parole["texte"]) > 400 else ""), parole.get("audio"),
                         parole.get("voix", "fr-FR"), image, type_image or "image/png",
                         lecture_auto=parole.get("nouveau", False) and r["vocal"], etat=parole.get("etat", "normal"),
                         indicateur=parole.get("meta")), height=380)
    parole["nouveau"] = False
