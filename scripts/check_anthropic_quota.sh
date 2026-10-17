#!/bin/bash
# Verifica se a chave Anthropic tem cota ativa.
# Saída: "QUOTA_ACTIVE" (exit 0) | "QUOTA_INACTIVE: <msg>" (exit 1) | "NO_KEY_FILE" (exit 2)
KEY_FILE="$HOME/.openclaw/credentials/anthropic/api_key"
if [ ! -f "$KEY_FILE" ]; then
  echo "NO_KEY_FILE"
  exit 2
fi
ANTHROPIC_API_KEY=$(cat "$KEY_FILE")
RESP=$(curl -s -m 15 -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5","max_tokens":3,"messages":[{"role":"user","content":"."}]}' \
  -w "|||HTTP:%{http_code}")
HTTP_CODE=$(echo "$RESP" | tail -1 | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ]; then
  echo "QUOTA_ACTIVE"
  exit 0
else
  BODY=$(echo "$RESP" | head -1 | head -c 200)
  echo "QUOTA_INACTIVE: HTTP $HTTP_CODE - $BODY"
  exit 1
fi
