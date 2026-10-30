"""Les tables (mêmes colonnes que schema.sql), créées via SQLAlchemy : PostgreSQL en production, SQLite en test."""

from sqlalchemy import (BigInteger, Column, DateTime, Float, ForeignKey, Index, Integer, MetaData, String, Table, Text,
                        CheckConstraint, create_engine)

meta = MetaData()
ID = BigInteger().with_variant(Integer, "sqlite")      # BIGSERIAL sous PostgreSQL, auto-incrément sous SQLite

utilisateurs = Table("utilisateurs", meta,
                     Column("id", String(64), primary_key=True), Column("ip_creation", String(64), nullable=False),
                     Column("cree_le", DateTime(timezone=True), nullable=False),
                     Column("bloque", Integer, nullable=False, default=0))
portefeuilles = Table("portefeuilles", meta,
                      Column("utilisateur_id", String(64), ForeignKey("utilisateurs.id"), primary_key=True),
                      Column("solde", Integer, nullable=False, default=0),
                      Column("version", Integer, nullable=False, default=0),
                      Column("sceau", String(64), nullable=False),
                      Column("maj_le", DateTime(timezone=True), nullable=False),
                      CheckConstraint("solde >= 0 AND solde <= 20", name="solde_borne"))
recompenses = Table("recompenses", meta,
                    Column("transaction_id", String(128), primary_key=True),
                    Column("utilisateur_id", String(64), ForeignKey("utilisateurs.id"), nullable=False),
                    Column("reseau", String(32), nullable=False), Column("ip", String(64)),
                    Column("messages", Integer, nullable=False), Column("revenu_estime", Float, nullable=False),
                    Column("recue_le", DateTime(timezone=True), nullable=False),
                    Index("idx_recompenses_utilisateur", "utilisateur_id", "recue_le"))
compteurs = Table("compteurs_jour", meta,
                  Column("jour", String(10), primary_key=True), Column("cle", String(96), primary_key=True),
                  Column("videos", Integer, nullable=False, default=0),
                  Column("messages", Integer, nullable=False, default=0),
                  Column("sessions", Integer, nullable=False, default=0))
consommation = Table("consommation", meta,
                     Column("id", ID, primary_key=True, autoincrement=True),
                     Column("utilisateur_id", String(64), nullable=False),
                     Column("jetons_entree", Integer, nullable=False), Column("jetons_caches", Integer, nullable=False, default=0),
                     Column("jetons_sortie", Integer, nullable=False), Column("cout_usd", Float, nullable=False),
                     Column("cree_le", DateTime(timezone=True), nullable=False),
                     Index("idx_consommation_date", "cree_le"))
revenus_reels = Table("revenus_reels", meta, Column("jour", String(10), primary_key=True),
                      Column("revenu_usd", Float, nullable=False))
messages = Table("messages", meta,
                 Column("id", ID, primary_key=True, autoincrement=True),
                 Column("utilisateur_id", String(64), nullable=False), Column("role", String(16), nullable=False),
                 Column("contenu", Text, nullable=False), Column("cree_le", DateTime(timezone=True), nullable=False),
                 Index("idx_messages_utilisateur", "utilisateur_id", "id"))


def moteur(url):
    e = create_engine(url, future=True, pool_pre_ping=True)
    meta.create_all(e)
    return e
