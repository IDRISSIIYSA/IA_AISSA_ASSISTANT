-- Schéma de la base PostgreSQL (référence). Le serveur crée les mêmes tables via SQLAlchemy (app/base.py),
-- ce qui permet aussi SQLite pour les tests.

CREATE TABLE IF NOT EXISTS utilisateurs (
    id           VARCHAR(64) PRIMARY KEY,           -- identifiant aléatoire émis par le serveur (jamais par le client)
    ip_creation  VARCHAR(64) NOT NULL,
    cree_le      TIMESTAMPTZ   NOT NULL,
    bloque       INTEGER     NOT NULL DEFAULT 0      -- 1 = fraude détectée (sceau du portefeuille invalide…)
);

-- Portefeuille : solde en messages, toujours entre 0 et le plafond (20).
-- « sceau » = HMAC-SHA256(secret serveur, id:solde:version) : toute modification directe de la ligne est détectée.
CREATE TABLE IF NOT EXISTS portefeuilles (
    utilisateur_id VARCHAR(64) PRIMARY KEY REFERENCES utilisateurs(id),
    solde          INTEGER     NOT NULL DEFAULT 0 CHECK (solde >= 0 AND solde <= 20),
    version        INTEGER     NOT NULL DEFAULT 0,   -- verrou optimiste : chaque mise à jour l'incrémente
    sceau          VARCHAR(64) NOT NULL,
    maj_le         TIMESTAMPTZ   NOT NULL
);

-- Chaque récompense reçue de la régie, une seule fois (transaction_id unique = rejeu impossible).
CREATE TABLE IF NOT EXISTS recompenses (
    transaction_id VARCHAR(128) PRIMARY KEY,
    utilisateur_id VARCHAR(64)  NOT NULL REFERENCES utilisateurs(id),
    reseau         VARCHAR(32)  NOT NULL,            -- admob, webhook…
    ip             VARCHAR(64),
    messages       INTEGER      NOT NULL,            -- messages réellement crédités (0 si plafond atteint)
    revenu_estime  REAL         NOT NULL,            -- USD, d'après l'eCPM configuré
    recue_le       TIMESTAMPTZ    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_recompenses_utilisateur ON recompenses (utilisateur_id, recue_le);

-- Compteurs journaliers anti-fraude par IP et par utilisateur.
CREATE TABLE IF NOT EXISTS compteurs_jour (
    jour   VARCHAR(10) NOT NULL,                     -- AAAA-MM-JJ (UTC)
    cle    VARCHAR(96) NOT NULL,                     -- « ip:1.2.3.4 » ou « user:… »
    videos INTEGER     NOT NULL DEFAULT 0,
    messages INTEGER   NOT NULL DEFAULT 0,
    sessions INTEGER   NOT NULL DEFAULT 0,
    PRIMARY KEY (jour, cle)
);

-- Coût réel de chaque appel à l'IA (jetons facturés).
CREATE TABLE IF NOT EXISTS consommation (
    id               BIGSERIAL PRIMARY KEY,
    utilisateur_id   VARCHAR(64) NOT NULL,
    jetons_entree    INTEGER NOT NULL,
    jetons_caches    INTEGER NOT NULL DEFAULT 0,
    jetons_sortie    INTEGER NOT NULL,
    cout_usd         REAL    NOT NULL,
    cree_le          TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_consommation_date ON consommation (cree_le);

-- Revenus réels déclarés par l'administrateur à partir des rapports de la régie (corrige l'eCPM estimé).
CREATE TABLE IF NOT EXISTS revenus_reels (
    jour       VARCHAR(10) PRIMARY KEY,
    revenu_usd REAL NOT NULL
);

-- Fenêtre de mémoire : seuls les derniers messages sont gardés (les plus anciens sont supprimés).
CREATE TABLE IF NOT EXISTS messages (
    id             BIGSERIAL PRIMARY KEY,
    utilisateur_id VARCHAR(64) NOT NULL,
    role           VARCHAR(16) NOT NULL,                 -- user | assistant
    contenu        TEXT        NOT NULL,
    cree_le        TIMESTAMPTZ   NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_utilisateur ON messages (utilisateur_id, id);
