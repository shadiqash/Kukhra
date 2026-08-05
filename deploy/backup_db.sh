#!/usr/bin/env bash
# Nightly Postgres backup for the production stack.
# Keeps the last BACKUP_KEEP (default 14) dumps in BACKUP_DIR.

set -euo pipefail

cd "$(dirname "$0")/.."
source .env

BACKUP_DIR="${BACKUP_DIR:-/var/backups/everfresh}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
STAMP="$(date +%F)"

mkdir -p "$BACKUP_DIR"

export PGPASSWORD="$DB_PASSWORD"
pg_dump -U "$DB_USER" -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" "$DB_NAME" | gzip > "$BACKUP_DIR/everfresh-$STAMP.sql.gz"

ls -1t "$BACKUP_DIR"/everfresh-*.sql.gz | tail -n "+$((BACKUP_KEEP + 1))" | xargs -r rm --

echo "backup ok: $BACKUP_DIR/everfresh-$STAMP.sql.gz ($(date))"
