#!/usr/bin/env bash

set -euo pipefail

API_URL="http://localhost:8000"
TEAM_ID=""
CHANNEL_ID=""
CONVERSATION_ID=""
REPLY_TO_MESSAGE_ID=""
TIMEOUT_SECONDS=120

print_usage() {
  cat <<'USAGE'
Usage:
  scripts/validate_runtime.sh \
    --team-id <team_id> \
    --channel-id <channel_id> \
    --conversation-id <conversation_id> \
    --reply-to-message-id <reply_to_message_id> \
    [--api-url <api_url>] \
    [--timeout-seconds <seconds>]

What it validates:
1. docker compose up -d --build
2. alembic upgrade head
3. GET /health == 200
4. POST /teams/adaptive-card == 202
5. Worker transitions dispatch to SENT
6. DB row contains SENT state with sent_at and delivery id

Manual step (required):
- Confirm in Teams UI that the adaptive card arrived as a reply on the expected thread.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --team-id)
      TEAM_ID="$2"
      shift 2
      ;;
    --channel-id)
      CHANNEL_ID="$2"
      shift 2
      ;;
    --conversation-id)
      CONVERSATION_ID="$2"
      shift 2
      ;;
    --reply-to-message-id)
      REPLY_TO_MESSAGE_ID="$2"
      shift 2
      ;;
    --api-url)
      API_URL="$2"
      shift 2
      ;;
    --timeout-seconds)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --help|-h)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_usage
      exit 1
      ;;
  esac
done

if [[ -z "$TEAM_ID" || -z "$CHANNEL_ID" || -z "$CONVERSATION_ID" || -z "$REPLY_TO_MESSAGE_ID" ]]; then
  echo "Missing required arguments." >&2
  print_usage
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not installed." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not installed." >&2
  exit 1
fi

CORRELATION_ID="corr-e2e-$(date +%s)"

log_step() {
  echo
  echo "==> $1"
}

log_step "Starting stack"
docker compose up -d --build

log_step "Running database migrations"
docker compose exec -T api alembic -c alembic.ini upgrade head

log_step "Checking health endpoint"
HEALTH_STATUS=$(curl -sS -o /tmp/health_response.json -w "%{http_code}" "$API_URL/health")
if [[ "$HEALTH_STATUS" != "200" ]]; then
  echo "Health check failed with status $HEALTH_STATUS" >&2
  cat /tmp/health_response.json >&2 || true
  exit 1
fi
echo "Health endpoint returned 200 OK"

log_step "Submitting dispatch request"
DISPATCH_PAYLOAD=$(cat <<JSON
{
  "teamId": "$TEAM_ID",
  "channelId": "$CHANNEL_ID",
  "conversationId": "$CONVERSATION_ID",
  "replyToMessageId": "$REPLY_TO_MESSAGE_ID",
  "adaptiveCard": {
    "type": "AdaptiveCard",
    "version": "1.4",
    "body": [
      {
        "type": "TextBlock",
        "text": "Runtime validation card: $CORRELATION_ID",
        "wrap": true
      }
    ]
  },
  "correlationId": "$CORRELATION_ID"
}
JSON
)

DISPATCH_STATUS=$(curl -sS -o /tmp/dispatch_response.json -w "%{http_code}" \
  -X POST "$API_URL/teams/adaptive-card" \
  -H "Content-Type: application/json" \
  -d "$DISPATCH_PAYLOAD")

if [[ "$DISPATCH_STATUS" != "202" && "$DISPATCH_STATUS" != "200" ]]; then
  echo "Dispatch request failed with status $DISPATCH_STATUS" >&2
  cat /tmp/dispatch_response.json >&2 || true
  exit 1
fi

echo "Dispatch endpoint returned HTTP $DISPATCH_STATUS"
cat /tmp/dispatch_response.json

log_step "Waiting for worker to process dispatch"
START_TIME=$(date +%s)
FINAL_ROW=""
while true; do
  FINAL_ROW=$(docker compose exec -T postgres psql -U postgres -d teams_dispatcher -t -A -F '|' -c \
    "SELECT status,retry_count,COALESCE(last_error,''),COALESCE(graph_message_id,''),COALESCE(sent_at::text,'') FROM adaptive_card_dispatches WHERE correlation_id='${CORRELATION_ID}' LIMIT 1;")

  STATUS=$(echo "$FINAL_ROW" | cut -d'|' -f1)
  if [[ "$STATUS" == "SENT" || "$STATUS" == "FAILED" ]]; then
    break
  fi

  NOW=$(date +%s)
  if (( NOW - START_TIME > TIMEOUT_SECONDS )); then
    echo "Timed out waiting for dispatch final state after ${TIMEOUT_SECONDS}s" >&2
    break
  fi

  sleep 3
done

STATUS=$(echo "$FINAL_ROW" | cut -d'|' -f1)
RETRY_COUNT=$(echo "$FINAL_ROW" | cut -d'|' -f2)
LAST_ERROR=$(echo "$FINAL_ROW" | cut -d'|' -f3)
DELIVERY_ID=$(echo "$FINAL_ROW" | cut -d'|' -f4)
SENT_AT=$(echo "$FINAL_ROW" | cut -d'|' -f5)

echo
echo "Correlation ID: $CORRELATION_ID"
echo "DB status: $STATUS"
echo "retry_count: $RETRY_COUNT"
echo "last_error: ${LAST_ERROR:-<null>}"
echo "delivery_id(graph_message_id column): ${DELIVERY_ID:-<empty>}"
echo "sent_at: ${SENT_AT:-<null>}"

log_step "Recent worker logs"
docker compose logs --since 2m worker | tail -n 60

if [[ "$STATUS" != "SENT" ]]; then
  echo "Validation failed: expected status SENT." >&2
  exit 1
fi

if [[ -z "$SENT_AT" ]]; then
  echo "Validation failed: sent_at is empty." >&2
  exit 1
fi

echo
echo "Validation succeeded up to runtime and DB checks."
echo "Manual check still required: verify Teams received the adaptive card reply on the target thread."
