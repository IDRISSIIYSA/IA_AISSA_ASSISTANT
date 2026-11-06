#!/usr/bin/env bash
# Sauvegarde quotidienne de la base Neon (serveur dédié) : pg_dump compressé, 30 jours gardés.
# Installée par installer.sh dans /etc/cron.d/ia_aissa_sauvegarde (chaque nuit à 3 h 17).
# Copiez aussi le dossier de temps en temps hors du serveur (stockage à part : disque externe, autre machine).
set -euo pipefail
DOSSIER="${DOSSIER_SAUVEGARDES:-/opt/ia_aissa/sauvegardes}"
GARDER_JOURS="${GARDER_JOURS:-30}"
source /opt/ia_aissa/deploy/.env                           # MEMOIRE_URL (jamais affichée)
mkdir -p "$DOSSIER" && chmod 700 "$DOSSIER"
URL="${MEMOIRE_URL/postgresql+psycopg:/postgresql:}"        # pg_dump ne comprend pas le préfixe SQLAlchemy
FICHIER="$DOSSIER/ia_aissa-$(date +%Y-%m-%d).sql.gz"
# pg_dump 17 (image Docker officielle) : il sait sauvegarder une base Neon en PostgreSQL 16 ou 17
docker run --rm postgres:17 pg_dump --no-owner --no-privileges "$URL" | gzip -9 > "$FICHIER.partiel"
mv "$FICHIER.partiel" "$FICHIER"                            # jamais de fichier à moitié écrit sous le bon nom
find "$DOSSIER" -name 'ia_aissa-*.sql.gz' -mtime +"$GARDER_JOURS" -delete
echo "Sauvegarde : $FICHIER ($(du -h "$FICHIER" | cut -f1))"
