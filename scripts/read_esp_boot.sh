#!/usr/bin/env bash
# read_esp_boot.sh — captura boot log do ESP32 com timeout BOUNDED p/ não queimar contexto.
# Uso: scripts/read_esp_boot.sh [porta] [segundos] [linhas]
# Padrões são seguros; este script NUNCA despeja stdout bruto no terminal.
set -u
PORT="${1:-/dev/ttyACM1}"
SECS="${2:-12}"
LINES="${3:-30}"
RAW=/tmp/esp_boot.log
CLEAN=/tmp/esp_boot_clean.log

if [ ! -e "$PORT" ]; then
  echo "ERRO: porta $PORT não existe. ESP32 ausente/outra porta?"
  exit 1
fi

rm -f "$RAW" "$CLEAN"

# timeout dentro do sg garante que cat morra mesmo sem saída do dispositivo.
# Depois do ctrl, nada de background & — é bloqueante e bounded por timeout.
sg dialout -c "timeout ${SECS} cat ${PORT}" > "$RAW" 2>/dev/null

# Sanitiza: remove \r, linhas vazias, e só mostra o final.
tr -d '\r' < "$RAW" | grep -v '^$' > "$CLEAN"

TOTAL=$(wc -l < "$CLEAN")
echo "== BOOT LOG capturado: ${TOTAL} linhas (últimas ${LINES}) =="
tail -n "$LINES" "$CLEAN"
echo "== fim (arquivo: ${CLEAN}, completo) =="
