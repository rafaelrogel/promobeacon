#!/usr/bin/env bash
# Postiz daily health check. Prints a short report; exit 0 if healthy, non-zero if problem.
# Usage: bash scripts/postiz_health_check.sh

echo "=== POSTIZ HEALTH CHECK $(date -u +%Y-%m-%dT%H:%MZ) ==="

# 1) Containers up + restart counts (no Go templates)
echo "-- containers --"
docker ps --filter name=postiz --filter name=temporal --format "{{.Names}} {{.Status}}" 2>&1
echo "-- restarts (json) --"
for c in postiz temporal; do
  rc=$(docker inspect "$c" --format "{{.RestartCount}}" 2>/dev/null)
  st=$(docker inspect "$c" --format "{{.State.Status}}" 2>/dev/null)
  echo "$c status=$st restarts=${rc:-n/a}"
done

# Temporal health: is it up and NOT in restart loop? (flag for dedicated alert)
TEMP_ST=$(docker inspect temporal --format "{{.State.Status}}" 2>/dev/null)
TEMP_RC=$(docker inspect temporal --format "{{.RestartCount}}" 2>/dev/null)
if [ "$TEMP_ST" != "running" ]; then
  echo "TEMPORAL_DOWN: YES (status=$TEMP_ST)"
elif [ -n "$TEMP_RC" ] && [ "$TEMP_RC" -ge 3 ]; then
  echo "TEMPORAL_RESTARTLOOP: YES (restarts=$TEMP_RC)"
else
  echo "TEMPORAL_DOWN: NO"
fi

# 2) HTTP checks
echo "-- http --"
for path in / /login; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 -L "http://127.0.0.1:4007${path}" 2>&1)
  echo "${path} -> $code"
done

# 3) PM2 workers (3 processes online?)
echo "-- pm2 --"
docker exec postiz sh -c 'pm2 list' 2>&1 | grep -E "backend|frontend|orchestrator"

# Decide health. Root returns 200 (login is a redirect).
root=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 -L "http://127.0.0.1:4007/" 2>&1)
temp_ok=yes
if [ "$TEMP_ST" != "running" ]; then temp_ok=no; fi
if [ -n "$TEMP_RC" ] && [ "$TEMP_RC" -ge 3 ]; then temp_ok=no; fi

if [ "$root" = "200" ] && [ "$temp_ok" = "yes" ]; then
  echo "RESULT: OK"
  exit 0
else
  echo "RESULT: PROBLEM"
  exit 1
fi
