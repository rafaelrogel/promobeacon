#!/usr/bin/env bash
# Gate do monitor M3: dispara payload só quando a taxa de 429 está CRITICAL
# e o último alerta foi há >2h (cooldown anti-spam).
# Saída: {"fire": true} ou {"fire": false}
set -euo pipefail

SCRIPT="/home/rafael/.openclaw/workspace/scripts/gmi_m3_monitor.sh"
STATE_FILE="/tmp/gmi_m3_alert_state"
OUT_FILE="/tmp/gmi_m3_monitor_out.txt"
COOLDOWN=7200  # 2h entre alertas

OUT=$(bash "$SCRIPT" 30 2>&1 || true)
echo "$OUT" > "$OUT_FILE"

STATUS=$(echo "$OUT" | grep '^STATUS=' | cut -d= -f2)
NOW=$(date -u +%s)
LAST=0
[[ -f "$STATE_FILE" ]] && LAST=$(cat "$STATE_FILE" 2>/dev/null || echo 0)

if [[ "$STATUS" == "CRITICAL" && $(( NOW - LAST )) -ge $COOLDOWN ]]; then
  echo "$NOW" > "$STATE_FILE"
  echo '{"fire": true}'
else
  echo '{"fire": false}'
fi
