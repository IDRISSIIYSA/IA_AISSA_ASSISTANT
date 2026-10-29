"""
La mémoire d'IA AISSA : conversations et souvenirs, séparés pour chaque utilisateur.

- Conversations : chaque échange est enregistré et peut être repris plus tard.
- Souvenirs : faits durables qu'IA AISSA retient sur la personne (métier, entreprise, préférences…)
  et qu'elle relit au début de chaque conversation.

Stockage : la base indiquée par le secret MEMOIRE_URL (PostgreSQL recommandé sur Streamlit Cloud,
ex. Neon ou Supabase : postgresql+psycopg://utilisateur:motdepasse@hote/base), sinon un fichier
SQLite local, qui sur Streamlit Cloud est effacé à chaque redémarrage de l'application.
"""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, MetaData, String, Table,
                        Text, create_engine, delete, insert, select, update)

FICHIER_LOCAL = Path(__file__).resolve().parent.parent / "memoire_ia_aissa.db"

meta = MetaData()
conversations = Table(
    "conversations", meta,
    Column("id", Integer, primary_key=True),
    Column("utilisateur", String(80), index=True, nullable=False),
    Column("titre", String(200), nullable=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
    Column("modifie_le", DateTime(timezone=True), nullable=False),
)
messages = Table(
    "messages", meta,
    Column("id", Integer, primary_key=True),
    Column("conversation_id", Integer, ForeignKey("conversations.id", ondelete="CASCADE"), index=True),
    Column("role", String(20), nullable=False),
    Column("texte", Text, nullable=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
)
souvenirs = Table(
    "souvenirs", meta,
    Column("id", Integer, primary_key=True),
    Column("utilisateur", String(80), index=True, nullable=False),
    Column("fait", Text, nullable=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
)

# Apprentissage par les corrections (partagé : c'est le même cerveau d'IA AISSA pour tous ses utilisateurs)
corrections = Table(
    "corrections", meta,
    Column("id", Integer, primary_key=True),
    Column("utilisateur", String(80), nullable=False),
    Column("matiere", String(60), index=True, nullable=False),
    Column("question", Text, nullable=False),
    Column("bonne_reponse", String(200), nullable=False),
    Column("source", String(20), nullable=False),          # « assistante » ou « utilisateur »
    Column("apprise", Boolean, nullable=False, default=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
)
cerveaux = Table(
    "cerveaux", meta,
    Column("matiere", String(60), primary_key=True),
    Column("donnees", LargeBinary, nullable=False),
    Column("modifie_le", DateTime(timezone=True), nullable=False),
)
revisions = Table(
    "revisions", meta,
    Column("id", Integer, primary_key=True),
    Column("matiere", String(60), index=True, nullable=False),
    Column("nb_corrections", Integer, nullable=False),
    Column("examen_avant", Float, nullable=False),
    Column("examen_apres", Float, nullable=False),
    Column("corrections_avant", Float, nullable=False),
    Column("corrections_apres", Float, nullable=False),
    Column("adoptee", Boolean, nullable=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
)

# Lacunes : questions auxquelles IA AISSA n'a pas su répondre avec assurance (sa matière d'étude autonome)
lacunes = Table(
    "lacunes", meta,
    Column("id", Integer, primary_key=True),
    Column("question", Text, nullable=False),
    Column("matiere_devinee", String(60)),
    Column("confiance", Float, nullable=False),
    Column("resolue", Boolean, nullable=False, default=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
)
# Galerie des inventions du laboratoire
idees = Table(
    "idees", meta,
    Column("id", Integer, primary_key=True),
    Column("utilisateur", String(80), index=True, nullable=False),
    Column("probleme", Text, nullable=False),
    Column("titre", String(300), nullable=False),
    Column("description", Text, nullable=False),
    Column("confiance", Float, nullable=False),
    Column("faisabilite", Float, nullable=False),
    Column("details", Text, nullable=False),               # débat et évolution (JSON)
    Column("cree_le", DateTime(timezone=True), nullable=False),
)
# Bibliothèque : concepts digérés à partir de pages web, de livres et de Wikipédia (jamais le texte complet)
digestions = Table(
    "digestions", meta,
    Column("id", Integer, primary_key=True),
    Column("utilisateur", String(80), nullable=False),
    Column("source", String(500), nullable=False),
    Column("famille", String(60), nullable=False),
    Column("concepts", Text, nullable=False),             # JSON : [{"nom", "explication"}]
    Column("analogie", Text, nullable=False),
    Column("confiance", Float, nullable=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
)
# Réglages de l'application (administration) : empreintes des mots de passe, clés API de l'application…
reglages = Table(
    "reglages", meta,
    Column("cle", String(120), primary_key=True),
    Column("valeur", Text, nullable=False),
    Column("modifie_le", DateTime(timezone=True), nullable=False),
)
# Visages des personnes autorisées (empreintes de 128 nombres, jamais la photo elle-même)
visages = Table(
    "visages", meta,
    Column("id", Integer, primary_key=True),
    Column("utilisateur", String(80), index=True, nullable=False),
    Column("empreinte", LargeBinary, nullable=False),
    Column("cree_le", DateTime(timezone=True), nullable=False),
)
# Médias d'IA AISSA (ex. l'image de son visage d'alien)
medias = Table(
    "medias", meta,
    Column("nom", String(60), primary_key=True),
    Column("donnees", LargeBinary, nullable=False),
    Column("type", String(60), nullable=False),
    Column("modifie_le", DateTime(timezone=True), nullable=False),
)


def normaliser_url(url):
    """Accepte l'adresse telle que la donnent Neon ou Supabase (postgresql://… ou postgres://…)."""
    url = str(url).strip().strip('"').strip("'")
    for prefixe in ("postgres://", "postgresql://"):
        if url.startswith(prefixe):
            url = "postgresql+psycopg://" + url[len(prefixe):]
    if url.startswith("postgresql+psycopg://") and "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def maintenant():
    return datetime.now(timezone.utc)


class Memoire:
    def __init__(self, url=None):
        self.url = normaliser_url(url) if url else f"sqlite:///{FICHIER_LOCAL}"
        self.persistante = url is not None
        self.moteur = create_engine(self.url, pool_pre_ping=True)
        meta.create_all(self.moteur)

    # ---------- Conversations ----------
    def nouvelle_conversation(self, utilisateur, premiere_question):
        titre = " ".join(premiere_question.split())[:80] or "Conversation"
        with self.moteur.begin() as c:
            return c.execute(insert(conversations).values(
                utilisateur=utilisateur, titre=titre, cree_le=maintenant(), modifie_le=maintenant())).inserted_primary_key[0]

    def ajouter_message(self, utilisateur, conversation_id, role, texte):
        with self.moteur.begin() as c:
            if not self._appartient(c, utilisateur, conversation_id):
                raise PermissionError("Conversation inconnue pour cet utilisateur.")
            c.execute(insert(messages).values(conversation_id=conversation_id, role=role, texte=texte,
                                              cree_le=maintenant()))
            c.execute(update(conversations).where(conversations.c.id == conversation_id)
                      .values(modifie_le=maintenant()))

    def lister_conversations(self, utilisateur, limite=30):
        with self.moteur.connect() as c:
            lignes = c.execute(select(conversations.c.id, conversations.c.titre, conversations.c.modifie_le)
                               .where(conversations.c.utilisateur == utilisateur)
                               .order_by(conversations.c.modifie_le.desc()).limit(limite))
            return [dict(l._mapping) for l in lignes]

    def messages_de(self, utilisateur, conversation_id):
        with self.moteur.connect() as c:
            if not self._appartient(c, utilisateur, conversation_id):
                return []
            lignes = c.execute(select(messages.c.role, messages.c.texte)
                               .where(messages.c.conversation_id == conversation_id).order_by(messages.c.id))
            return [dict(l._mapping) for l in lignes]

    def supprimer_conversation(self, utilisateur, conversation_id):
        with self.moteur.begin() as c:
            if self._appartient(c, utilisateur, conversation_id):
                c.execute(delete(messages).where(messages.c.conversation_id == conversation_id))
                c.execute(delete(conversations).where(conversations.c.id == conversation_id))

    @staticmethod
    def _appartient(c, utilisateur, conversation_id):
        return c.execute(select(conversations.c.id).where(conversations.c.id == conversation_id,
                                                          conversations.c.utilisateur == utilisateur)).first() is not None

    # ---------- Souvenirs ----------
    def memoriser(self, utilisateur, fait):
        fait = " ".join(str(fait).split())[:500]
        if not fait:
            return None
        with self.moteur.begin() as c:
            existe = c.execute(select(souvenirs.c.id).where(souvenirs.c.utilisateur == utilisateur,
                                                            souvenirs.c.fait == fait)).first()
            if existe:
                return existe[0]
            return c.execute(insert(souvenirs).values(utilisateur=utilisateur, fait=fait,
                                                      cree_le=maintenant())).inserted_primary_key[0]

    def souvenirs_de(self, utilisateur):
        with self.moteur.connect() as c:
            lignes = c.execute(select(souvenirs.c.id, souvenirs.c.fait)
                               .where(souvenirs.c.utilisateur == utilisateur).order_by(souvenirs.c.id))
            return [dict(l._mapping) for l in lignes]

    def oublier(self, utilisateur, souvenir_id):
        with self.moteur.begin() as c:
            c.execute(delete(souvenirs).where(souvenirs.c.id == souvenir_id, souvenirs.c.utilisateur == utilisateur))


    # ---------- Corrections et cerveaux révisés ----------
    def ajouter_correction(self, utilisateur, matiere, question, bonne_reponse, source):
        question = " ".join(str(question).split())[:500]
        with self.moteur.begin() as c:
            existe = c.execute(select(corrections.c.id).where(corrections.c.matiere == matiere,
                                                              corrections.c.question == question,
                                                              corrections.c.bonne_reponse == bonne_reponse)).first()
            if existe:
                return existe[0]
            return c.execute(insert(corrections).values(
                utilisateur=utilisateur, matiere=matiere, question=question, bonne_reponse=bonne_reponse,
                source=source, apprise=False, cree_le=maintenant())).inserted_primary_key[0]

    def corrections_de(self, matiere=None, seulement_nouvelles=False):
        requete = select(corrections).order_by(corrections.c.id)
        if matiere:
            requete = requete.where(corrections.c.matiere == matiere)
        if seulement_nouvelles:
            requete = requete.where(corrections.c.apprise.is_(False))
        with self.moteur.connect() as c:
            return [dict(l._mapping) for l in c.execute(requete)]

    def marquer_non_apprises(self, matiere):
        with self.moteur.begin() as c:
            c.execute(update(corrections).where(corrections.c.matiere == matiere).values(apprise=False))

    def matieres_revisees(self):
        with self.moteur.connect() as c:
            return [l[0] for l in c.execute(select(cerveaux.c.matiere))]

    def oublier_cerveau(self, matiere):
        with self.moteur.begin() as c:
            c.execute(delete(cerveaux).where(cerveaux.c.matiere == matiere))

    def marquer_apprises(self, matiere):
        with self.moteur.begin() as c:
            c.execute(update(corrections).where(corrections.c.matiere == matiere).values(apprise=True))

    def sauver_cerveau(self, matiere, donnees):
        with self.moteur.begin() as c:
            c.execute(delete(cerveaux).where(cerveaux.c.matiere == matiere))
            c.execute(insert(cerveaux).values(matiere=matiere, donnees=donnees, modifie_le=maintenant()))

    def cerveau(self, matiere):
        with self.moteur.connect() as c:
            ligne = c.execute(select(cerveaux.c.donnees).where(cerveaux.c.matiere == matiere)).first()
            return ligne[0] if ligne else None

    def noter_revision(self, **valeurs):
        with self.moteur.begin() as c:
            c.execute(insert(revisions).values(cree_le=maintenant(), **valeurs))

    def revisions(self, limite=50):
        with self.moteur.connect() as c:
            return [dict(l._mapping) for l in c.execute(select(revisions).order_by(revisions.c.id.desc()).limit(limite))]


    # ---------- Lacunes ----------
    def ajouter_lacune(self, question, matiere_devinee, confiance):
        question = " ".join(str(question).split())[:500]
        with self.moteur.begin() as c:
            if c.execute(select(lacunes.c.id).where(lacunes.c.question == question)).first():
                return
            c.execute(insert(lacunes).values(question=question, matiere_devinee=matiere_devinee,
                                             confiance=float(confiance), resolue=False, cree_le=maintenant()))

    def lacunes_ouvertes(self, limite=30):
        with self.moteur.connect() as c:
            return [dict(l._mapping) for l in c.execute(select(lacunes).where(lacunes.c.resolue.is_(False))
                                                        .order_by(lacunes.c.id).limit(limite))]

    def resoudre_lacune(self, lacune_id):
        with self.moteur.begin() as c:
            c.execute(update(lacunes).where(lacunes.c.id == lacune_id).values(resolue=True))

    def croissance(self):
        """Corrections apprises au fil du temps (pour la courbe de croissance)."""
        with self.moteur.connect() as c:
            return [dict(l._mapping) for l in c.execute(
                select(corrections.c.cree_le, corrections.c.source, corrections.c.apprise).order_by(corrections.c.id))]

    # ---------- Galerie des inventions ----------
    def garder_idee(self, utilisateur, probleme, titre, description, confiance, faisabilite, details):
        with self.moteur.begin() as c:
            c.execute(insert(idees).values(utilisateur=utilisateur, probleme=probleme, titre=titre[:300],
                                           description=description, confiance=confiance, faisabilite=faisabilite,
                                           details=details, cree_le=maintenant()))

    def idees_de(self, utilisateur, limite=50):
        with self.moteur.connect() as c:
            return [dict(l._mapping) for l in c.execute(select(idees).where(idees.c.utilisateur == utilisateur)
                                                        .order_by(idees.c.id.desc()).limit(limite))]

    def compter_lacunes(self):
        with self.moteur.connect() as c:
            lignes = list(c.execute(select(lacunes.c.resolue)))
        return len(lignes), sum(1 for l in lignes if l.resolue)

    # ---------- Bibliothèque ----------
    def garder_digestion(self, utilisateur, source, famille, concepts, analogie, confiance):
        with self.moteur.begin() as c:
            c.execute(insert(digestions).values(utilisateur=utilisateur, source=source[:500], famille=famille,
                                                concepts=concepts, analogie=analogie, confiance=confiance,
                                                cree_le=maintenant()))

    def digestions(self, limite=2000):
        with self.moteur.connect() as c:
            return [dict(l._mapping) for l in c.execute(select(digestions).order_by(digestions.c.id.desc())
                                                        .limit(limite))]

    # ---------- Réglages (administration) ----------
    def reglage(self, cle):
        with self.moteur.connect() as c:
            l = c.execute(select(reglages.c.valeur).where(reglages.c.cle == cle)).first()
            return l[0] if l else None

    def reglages(self, prefixe=""):
        with self.moteur.connect() as c:
            return {l.cle: l.valeur for l in c.execute(select(reglages).where(reglages.c.cle.startswith(prefixe)))}

    def definir_reglage(self, cle, valeur):
        with self.moteur.begin() as c:
            c.execute(delete(reglages).where(reglages.c.cle == cle))
            c.execute(insert(reglages).values(cle=cle, valeur=valeur, modifie_le=maintenant()))

    def supprimer_reglage(self, cle):
        with self.moteur.begin() as c:
            c.execute(delete(reglages).where(reglages.c.cle == cle))

    # ---------- Visages ----------
    def ajouter_visage(self, utilisateur, empreinte):
        import numpy as np
        with self.moteur.begin() as c:
            c.execute(insert(visages).values(utilisateur=utilisateur, cree_le=maintenant(),
                                             empreinte=np.asarray(empreinte, np.float32).tobytes()))

    def visages_connus(self):
        import numpy as np
        connus = {}
        with self.moteur.connect() as c:
            for l in c.execute(select(visages.c.utilisateur, visages.c.empreinte)):
                connus.setdefault(l.utilisateur, []).append(np.frombuffer(l.empreinte, np.float32))
        return connus

    def oublier_visage(self, utilisateur):
        with self.moteur.begin() as c:
            c.execute(delete(visages).where(visages.c.utilisateur == utilisateur))

    # ---------- Médias ----------
    def sauver_media(self, nom, donnees, type_mime):
        with self.moteur.begin() as c:
            c.execute(delete(medias).where(medias.c.nom == nom))
            c.execute(insert(medias).values(nom=nom, donnees=donnees, type=type_mime, modifie_le=maintenant()))

    def media(self, nom):
        with self.moteur.connect() as c:
            l = c.execute(select(medias.c.donnees, medias.c.type).where(medias.c.nom == nom)).first()
            return (l.donnees, l.type) if l else (None, None)

    def supprimer_media(self, nom):
        with self.moteur.begin() as c:
            c.execute(delete(medias).where(medias.c.nom == nom))


def historique_api(lignes):
    """Messages enregistrés -> historique pour l'API (texte seul, en alternant les rôles)."""
    historique = []
    for l in lignes:
        if historique and historique[-1]["role"] == l["role"]:
            historique[-1]["content"] += "\n\n" + l["texte"]
        else:
            historique.append({"role": l["role"], "content": l["texte"]})
    while historique and historique[-1]["role"] != "assistant":
        historique.pop()          # une question restée sans réponse sera reposée
    return historique
