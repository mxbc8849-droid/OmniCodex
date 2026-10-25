#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/opt/omnicodex
URL=${OMNICODEX_HEALTH_URL:-https://www.udn4f.com/health}
ALERT=${OMNICODEX_ALERT_WEBHOOK:-}
msg=''
if ! curl --fail --silent --show-error --max-time 15 "$URL" >/dev/null; then msg="OmniCodex health check failed: $URL"; fi
if ! docker compose -f "$ROOT/docker-compose.yml" ps --status running | grep -q omnicodex-api; then msg="OmniCodex API container is not running"; fi
if [ -n "$msg" ]; then
  logger -t omnicodex-monitor "$msg"
  if [ -n "$ALERT" ]; then curl --fail --silent --max-time 10 -H 'Content-Type: application/json' -d "{\"text\":\"$msg\"}" "$ALERT" || true; fi
  exit 1
fi
echo "healthy $(date -u +%FT%TZ)"
