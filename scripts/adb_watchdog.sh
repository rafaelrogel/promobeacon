#!/usr/bin/env bash
# adb_watchdog.sh — keep the PromoBeacon test tablet connected via ADB.
#
# Usage:  bash adb_watchdog.sh [DEVICE_SERIAL] [POLL_SECS]
# Default device: R9PW30T4JQM (Samsung SM-T220). Default poll: 30s.
#
# Behavior:
#   1. Probes adb devices every POLL_SECS.
#   2. If DEVICE_SERIAL present → exit 0 (success).
#   3. If missing → tries:
#        a) kill-server / start-server (USB re-enumeration)
#        b) adb connect <known_ips> (WiFi fallback if previously paired)
#   4. Logs every attempt to /home/rafael/.openclaw/workspace/memory/adb-watchdog.log
#   5. Returns 0 once reconnected, non-zero after MAX_ATTEMPTS consecutive failures.
#
# Known WiFi IPs (set to empty if unknown; agent can populate from `adb shell ip addr`):
#   - 192.168.1.x range (Castelo da Maia LAN, default gateway 192.168.1.1)
#
# Install as systemd service (optional, NOT auto-installed by this script):
#   /etc/systemd/system/adb-watchdog.service
#   [Service]
#   ExecStart=/home/rafael/.openclaw/workspace/scripts/adb_watchdog.sh R9PW30T4JQM 30
#   Restart=always
#
set -uo pipefail

DEV="${1:-R9PW30T4JQM}"
POLL="${2:-30}"
LOG="/home/rafael/.openclaw/workspace/memory/adb-watchdog.log"
STATE="/home/rafael/.openclaw/workspace/memory/adb-watchdog.state"
MAX_ATTEMPTS=10

# Known WiFi IPs for the tablet (populated manually if tablet has been paired
# over WiFi previously; otherwise leave empty → USB only).
KNOWN_IPS=(
    # "192.168.1.42"   # ← exemplo; descomente se souber o IP fixo do tablet
)

mkdir -p "$(dirname "$LOG")" "$(dirname "$STATE")"

log() {
    printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG" >&2
}

probe() {
    adb devices 2>/dev/null | awk -v dev="$DEV" 'NR>1 && $1==dev && $2=="device" {found=1} END{exit !found}'
}

restart_adb() {
    log "ADB: kill-server / start-server (USB re-enumeration)"
    adb kill-server 2>/dev/null
    sleep 2
    adb start-server 2>/dev/null
    sleep 2
}

try_wifi() {
    local ip
    for ip in "${KNOWN_IPS[@]}"; do
        [ -z "$ip" ] && continue
        log "ADB: try wifi connect $ip:5555"
        if adb connect "$ip:5555" 2>/dev/null | grep -q "connected to"; then
            sleep 1
            if probe; then
                log "ADB: reconnected via WiFi to $ip"
                return 0
            fi
        fi
    done
    return 1
}

attempts=0
log "ADB watchdog start (device=$DEV poll=${POLL}s)"
echo "running" > "$STATE"

while true; do
    if probe; then
        log "ADB: $DEV online"
        echo "online" > "$STATE"
        exit 0
    fi

    attempts=$((attempts + 1))
    log "ADB: $DEV MISSING (attempt $attempts/$MAX_ATTEMPTS)"

    if [ "$attempts" -ge "$MAX_ATTEMPTS" ]; then
        log "ADB: giving up after $MAX_ATTEMPTS attempts"
        echo "dead" > "$STATE"
        exit 1
    fi

    # Try WiFi first if we have known IPs
    if [ "${#KNOWN_IPS[@]}" -gt 0 ]; then
        try_wifi || restart_adb
    else
        restart_adb
    fi

    sleep "$POLL"
done
