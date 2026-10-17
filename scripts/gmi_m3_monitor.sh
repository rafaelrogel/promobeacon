#!/usr/bin/env bash
# Monitor: taxa de 429 (rate limit) do M3 no log do gateway OpenClaw
# Saída: STATUS (OK/WARN/CRITICAL) + métricas em JSON-like lines
# Uso: bash gmi_m3_monitor.sh [minutos_janela]
# Default janela: 30 minutos
set -euo pipefail

LOG_DIR="/tmp/openclaw"
WINDOW_MIN="${1:-30}"
THRESHOLD_WARN=30   # % de 429 na janela → WARN
THRESHOLD_CRIT=70   # % de 429 na janela → CRITICAL
MIN_SAMPLES=5       # mínimo de chamadas M3 pra considerar amostra válida

# Janela de tempo: agora - WINDOW_MIN min (epoch seconds)
NOW_EPOCH=$(date -u +%s)
WINDOW_START_EPOCH=$(( NOW_EPOCH - WINDOW_MIN * 60 ))
WINDOW_START_ISO=$(date -u -d "@${WINDOW_START_EPOCH}" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || gdate -u -d "@${WINDOW_START_EPOCH}" '+%Y-%m-%dT%H:%M:%S')

# Encontrar logs do dia atual e anterior (janela pode atravessar meia-noite UTC)
TODAY_LOG="${LOG_DIR}/openclaw-$(date -u '+%Y-%m-%d').log"
YESTERDAY_LOG="${LOG_DIR}/openclaw-$(date -u -d 'yesterday' '+%Y-%m-%d' 2>/dev/null || date -u -d '1 day ago' '+%Y-%m-%d').log"

CANDIDATES=("$TODAY_LOG")
[[ -f "$YESTERDAY_LOG" ]] && CANDIDATES=("$YESTERDAY_LOG" "$TODAY_LOG")

# Filtrar entradas: provider=gmi, model=MiniMax-M3, na janela, status=NNN
# Formato: cada linha do log é um JSON; o campo relevante está em message
# Usar python (já disponível) para parsing confiável
python3 - "$WINDOW_START_ISO" "$THRESHOLD_WARN" "$THRESHOLD_CRIT" "$MIN_SAMPLES" "${CANDIDATES[@]}" <<'PY'
import sys, json, os
from datetime import datetime, timezone

window_start_iso = sys.argv[1]
thresh_warn = int(sys.argv[2])
thresh_crit = int(sys.argv[3])
min_samples = int(sys.argv[4])
candidates = sys.argv[5:]

window_start = datetime.fromisoformat(window_start_iso).replace(tzinfo=timezone.utc)

total = 0
ok = 0
rate_limited = 0
other_errors = 0
first_at = None
last_at = None

for path in candidates:
    if not os.path.isfile(path):
        continue
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith('{'):
                continue
            # O log tem o JSON como STRING dentro de "0" (é nested) — checar ambas as formas
            try:
                obj = json.loads(line)
            except Exception:
                continue
            # Encontrar a mensagem model-fetch relevante
            msg = obj.get('message') or obj.get('1') or ''
            if not isinstance(msg, str):
                continue
            if 'provider=gmi' not in msg or 'MiniMax-M3' not in msg:
                continue
            # Filtrar só responses
            if 'response' not in msg:
                continue
            # Status
            import re
            m = re.search(r'status=(\d+)', msg)
            if not m:
                continue
            status = int(m.group(1))
            # Timestamp
            ts_str = obj.get('date') or obj.get('time')
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00') if ts_str.endswith('Z') else ts_str)
            except Exception:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < window_start:
                continue
            total += 1
            if first_at is None or ts < first_at:
                first_at = ts
            if last_at is None or ts > last_at:
                last_at = ts
            if 200 <= status < 300:
                ok += 1
            elif status == 429:
                rate_limited += 1
            else:
                other_errors += 1

if total == 0:
    print("STATUS=NO_DATA")
    print(f"WINDOW_MIN={30}")
    print(f"SAMPLES=0")
    sys.exit(0)

pct_429 = (rate_limited * 100.0) / total
pct_ok = (ok * 100.0) / total
pct_other = (other_errors * 100.0) / total

if total < min_samples:
    status = "INSUFFICIENT"
elif pct_429 >= thresh_crit or pct_other >= 50:
    status = "CRITICAL"
elif pct_429 >= thresh_warn or pct_other > 0:
    status = "WARN"
else:
    status = "OK"

print(f"STATUS={status}")
print(f"WINDOW_MIN=30")
print(f"SAMPLES={total}")
print(f"OK={ok} ({pct_ok:.1f}%)")
print(f"429={rate_limited} ({pct_429:.1f}%)")
print(f"OTHER_ERR={other_errors} ({pct_other:.1f}%)")
print(f"FIRST={first_at.isoformat() if first_at else 'n/a'}")
print(f"LAST={last_at.isoformat() if last_at else 'n/a'}")
print(f"THRESHOLD_WARN_PCT={thresh_warn}")
print(f"THRESHOLD_CRIT_PCT={thresh_crit}")
PY
