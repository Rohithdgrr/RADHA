#!/usr/bin/env bash
set -e
BRIDGE_URL=${LMARENA_BRIDGE_URL:-http://localhost:8001}
TOKEN=${LMARENA_TOKEN:-}

if [ -z "$TOKEN" ]; then
  echo "LMARENA_TOKEN not set — skip live bridge test (mock fallback active)"
  exit 0
fi

echo "Testing bridge at $BRIDGE_URL ..."

curl -s "$BRIDGE_URL/health" || echo "no /health endpoint"

for model in claude chatgpt gemini; do
  echo "--- $model ---"
  curl -N -X POST "$BRIDGE_URL/v1/chat/completions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"$model\", \"messages\": [{\"role\":\"user\",\"content\":\"Hi, 2+2?\"}], \"stream\": false, \"session_id\": \"$(uuidgen || cat /proc/sys/kernel/random/uuid)\" }" \
    | head -c 500
  echo
done
