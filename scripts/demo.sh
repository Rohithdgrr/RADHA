#!/usr/bin/env bash
set -e
API=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
echo "Demo: $API/council/query with 2 models"
curl -N -X POST "$API/council/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is quantum computing in one paragraph?","models":["claude","chatgpt"],"mode":"consensus","depth":"brief","show_reasoning":true,"chairman":"claude"}'

echo
echo "List recent sessions:"
curl -s "$API/council/sessions?limit=3" | python -m json.tool | head -n 60
