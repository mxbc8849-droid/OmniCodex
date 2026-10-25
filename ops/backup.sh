#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=${OMNICODEX_ROOT:-/opt/omnicodex}
BACKUP_ROOT=${OMNICODEX_BACKUP_ROOT:-/var/backups/omnicodex}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_ROOT/$STAMP"
mkdir -p "$DEST"
cd "$ROOT"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-omnicodex}" "${POSTGRES_DB:-omnicodex}" | gzip > "$DEST/postgres.sql.gz"
docker compose exec -T redis redis-cli --rdb - > "$DEST/redis.rdb"
if [ -f "$ROOT/.env" ]; then cp -f "$ROOT/.env" "$DEST/env.backup"; chmod 600 "$DEST/env.backup"; fi
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
echo "backup complete: $DEST"
