#!/usr/bin/env bash
# adb_watchdog_loop.sh — long-running wrapper that re-invokes the watchdog
# whenever the device drops again. Designed to be run in the background.
#
# Usage:  nohup bash adb_watchdog_loop.sh </dev/null >/dev/null 2>&1 &
# Kill:   pkill -f adb_watchdog_loop.sh
#
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="/home/rafael/.openclaw/workspace/memory/adb-watchdog-loop.log"
echo "[$(date -u +%FT%TZ)] loop start" >> "$LOG"
while true; do
    bash "$SCRIPT_DIR/adb_watchdog.sh" "R9PW30T4JQM" "30" >> "$LOG" 2>&1 || true
    echo "[$(date -u +%FT%TZ)] watchdog exited, sleeping 60s before retry" >> "$LOG"
    sleep 60
done
