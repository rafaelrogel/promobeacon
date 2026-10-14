#!/usr/bin/env bash
# run_qemu_selftest.sh — roda a bateria de selftest do firmware sob QEMU.
# Uso: scripts/run_qemu_selftest.sh [env]
#   env padrão: esp32c3-qemu  (PROMOBEACON_QEMU=1, que ativa os testes)
# Baseline histórico: 79 passed / 0 failed. Grep por "SELFTEST: ALL PASSED".
set -u
ENV="${1:-esp32c3-qemu}"
SUF="${ENV//-/_}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FW="$ROOT/firmware"
BUILD="$FW/.pio/build/$ENV"
OUT="/tmp/qemu_selftest_${SUF}.log"
MERGED="/tmp/qemu_${SUF}_flash.bin"

# Descoberta de binários com fallback portátil
# 1. PIO
if [ -n "${PIO:-}" ]; then
  :
elif command -v pio >/dev/null 2>&1; then
  PIO="$(command -v pio)"
elif [ -x "$HOME/pio_venv/bin/pio" ]; then
  PIO="$HOME/pio_venv/bin/pio"
elif [ -x "$HOME/.platformio/penv/bin/pio" ]; then
  PIO="$HOME/.platformio/penv/bin/pio"
else
  echo "ERRO: pio não encontrado no PATH nem em PIO. Defina PIO=/caminho/para/pio"
  exit 1
fi

# 2. ESPTOOL
if [ -n "${ESPTOOL:-}" ]; then
  :
elif command -v esptool.py >/dev/null 2>&1; then
  ESPTOOL="$(command -v esptool.py)"
elif [ -f "${PLATFORMIO_CORE_DIR:-$HOME/.platformio}/packages/tool-esptoolpy/esptool.py" ]; then
  ESPTOOL="${PLATFORMIO_CORE_DIR:-$HOME/.platformio}/packages/tool-esptoolpy/esptool.py"
elif [ -f "$HOME/.platformio/venv/bin/esptool.py" ]; then
  ESPTOOL="$HOME/.platformio/venv/bin/esptool.py"
else
  echo "ERRO: esptool.py não encontrado. Defina ESPTOOL=/caminho/para/esptool.py"
  exit 1
fi

# 3. QEMU
if [ -n "${QEMU:-}" ]; then
  :
elif command -v qemu-system-riscv32 >/dev/null 2>&1; then
  QEMU="$(command -v qemu-system-riscv32)"
elif [ -x "$HOME/.local/bin/qemu-system-riscv32" ]; then
  QEMU="$HOME/.local/bin/qemu-system-riscv32"
else
  echo "ERRO: qemu-system-riscv32 não encontrado. Baixe de https://github.com/espressif/qemu (release esp-develop) e coloque no PATH ou defina QEMU=/caminho/para/qemu-system-riscv32"
  exit 1
fi

# 1) Build do env QEMU
echo "== BUILD $ENV =="
( cd "$FW" && "$PIO" run -e "$ENV" ) || {
  echo "ERRO: build $ENV falhou"; exit 1; }
echo "BUILD OK"

# 2) Merge flash 4MB (bootloader@0x0, partitions@0x8000, app@0x20000) com pad
for f in "$BUILD/bootloader.bin" "$BUILD/partitions.bin" "$BUILD/firmware.bin"; do
  [ -f "$f" ] || { echo "ERRO: falta $f"; exit 1; }
done
rm -f "$MERGED"
echo "== MERGE (pad 4MB) =="
if [[ "$ESPTOOL" == *.py ]]; then
  ESPTOOL_CMD=(python3 "$ESPTOOL")
else
  ESPTOOL_CMD=("$ESPTOOL")
fi
"${ESPTOOL_CMD[@]}" --chip esp32c3 merge_bin \
  -o "$MERGED" --flash_mode dout --flash_size 4MB --flash_freq 40m \
  0x0 "$BUILD/bootloader.bin" \
  0x8000 "$BUILD/partitions.bin" \
  0x20000 "$BUILD/firmware.bin" || { echo "ERRO: merge falhou"; exit 1; }
# QEMU exige imagem de 2/4/8/16MB — pad até 4MB
truncate -s 4M "$MERGED"
echo "pad 4MB OK ($(wc -c < "$MERGED" | tr -d ' ') bytes)"

# 3) Roda QEMU (bounded pelo timeout de qemu; captura só linhas relevantes)
echo "== QEMU SELFTEST ($ENV) =="
rm -f "$OUT"
run_qemu() {
  if command -v timeout >/dev/null 2>&1; then
    timeout 120 "$QEMU" -machine esp32c3 -nographic -no-reboot \
      -drive file="$MERGED",if=mtd,format=raw
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c '
import subprocess, sys
try:
    sys.exit(subprocess.run(sys.argv[1:], timeout=120).returncode)
except subprocess.TimeoutExpired:
    sys.exit(124)
' "$QEMU" -machine esp32c3 -nographic -no-reboot \
  -drive file="$MERGED",if=mtd,format=raw
  else
    # Fallback portátil (macOS/BSD): watchdog com sleep+kill
    "$QEMU" -machine esp32c3 -nographic -no-reboot \
      -drive file="$MERGED",if=mtd,format=raw &
    local qemu_pid=$!
    (
      sleep 120
      kill -9 "$qemu_pid" 2>/dev/null
    ) &
    local watchdog_pid=$!
    wait "$qemu_pid" 2>/dev/null
    kill "$watchdog_pid" 2>/dev/null
    wait "$watchdog_pid" 2>/dev/null
  fi
}
run_qemu 2>&1 | grep -E "SELFTEST|ALL PASSED|FAIL|panic|abort" > "$OUT"

# 4) Resumo
echo "--- linhas SELFTEST ($(wc -l < "$OUT")) ---"
grep -c "PASS:" "$OUT" 2>/dev/null | xargs echo "PASS count:"
grep -c "FAIL" "$OUT" 2>/dev/null | xargs echo "FAIL count:"
tail -5 "$OUT"
if grep -q "ALL PASSED" "$OUT"; then
  echo "RESULTADO: ✅ SELFTEST ALL PASSED (baseline 79/79)"
  exit 0
else
  echo "RESULTADO: ❌ selftest NÃO passou (ver $OUT)"
  exit 1
fi
