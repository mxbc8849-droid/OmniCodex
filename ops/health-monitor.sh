#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=/opt/omnicodex
URL=${OMNICODEX_HEALTH_URL:-https://www.udn4f.com/health}
ALERT=${OMNICODEX_ALERT_WEBHOOK:-}
TG_TOKEN=${OMNICODEX_TELEGRAM_BOT_TOKEN:-}
TG_CHAT=${OMNICODEX_TELEGRAM_CHAT_ID:-}
msg=''
if ! curl --fail --silent --show-error --max-time 15 "$URL" >/dev/null; then msg="OmniCodex health check failed: $URL"; fi
if ! docker compose -f "$ROOT/docker-compose.yml" ps --status running | grep -q omnicodex-api; then msg="OmniCodex API container is not running"; fi
if [ -n "$msg" ]; then
  logger -t omnicodex-monitor "$msg"
  if [ -n "$ALERT" ]; then for n in 1 2 3; do curl --fail --silent --max-time 10 -H 'Content-Type: application/json' -d "{\"text\":\"$msg\"}" "$ALERT" && break || sleep $((n * 2)); done; fi
  if [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ]; then for n in 1 2 3; do curl --fail --silent --max-time 10 -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" --data-urlencode "chat_id=$TG_CHAT" --data-urlencode "text=$msg" >/dev/null && break || sleep $((n * 2)); done; fi
  exit 1
fi
echo "healthy $(date -u +%FT%TZ)"
