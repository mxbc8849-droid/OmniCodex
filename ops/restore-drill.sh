#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=${OMNICODEX_ROOT:-/opt/omnicodex}
BACKUP_ROOT=${OMNICODEX_BACKUP_ROOT:-/var/backups/omnicodex}
DRILL_DB=omnicodex_restore_drill
cd "$ROOT"
latest=$(find "$BACKUP_ROOT" -mindepth 2 -maxdepth 2 -name postgres.sql.gz -printf '%h\n' | sort | tail -1)
test -n "$latest" && test -s "$latest/postgres.sql.gz" && test -s "$latest/redis.rdb"
docker compose exec -T postgres dropdb -U "${POSTGRES_USER:-omnicodex}" --if-exists "$DRILL_DB"
docker compose exec -T postgres createdb -U "${POSTGRES_USER:-omnicodex}" "$DRILL_DB"
gzip -dc "$latest/postgres.sql.gz" | docker compose exec -T postgres psql -U "${POSTGRES_USER:-omnicodex}" -d "$DRILL_DB" >/dev/null
count=$(docker compose exec -T postgres psql -U "${POSTGRES_USER:-omnicodex}" -d "$DRILL_DB" -Atc 'select count(*) from users')
test "${count:-0}" -ge 1
docker compose exec -T postgres dropdb -U "${POSTGRES_USER:-omnicodex}" "$DRILL_DB"
echo "restore drill passed: users=$count backup=$latest"
