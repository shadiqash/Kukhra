#!/usr/bin/env bash
# Nightly Postgres backup for the production compose stack.
# Keeps the last BACKUP_KEEP (default 14) dumps in BACKUP_DIR.
#
# Install on the host:
#   crontab -e
#   30 2 * * * /opt/everfresh/deploy/backup_db.sh >> /var/log/everfresh-backup.log 2>&1
#
# Restore:
#   gunzip -c /var/backups/everfresh/everfresh-YYYY-MM-DD.sql.gz | \
#     docker compose -f docker-compose.prod.yml exec -T db psql -U "$DB_USER" "$DB_NAME"
set -euo pipefail

cd "$(dirname "$0")/.."
source .env

BACKUP_DIR="${BACKUP_DIR:-/var/backups/everfresh}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
STAMP="$(date +%F)"

mkdir -p "$BACKUP_DIR"

docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/everfresh-$STAMP.sql.gz"

# Drop dumps beyond the retention window (oldest first).
ls -1t "$BACKUP_DIR"/everfresh-*.sql.gz | tail -n "+$((BACKUP_KEEP + 1))" | xargs -r rm --

echo "backup ok: $BACKUP_DIR/everfresh-$STAMP.sql.gz ($(date))"
