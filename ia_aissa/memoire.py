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


def maintenant():
    return datetime.now(timezone.utc)


class Memoire:
    def __init__(self, url=None):
        self.url = url or f"sqlite:///{FICHIER_LOCAL}"
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
