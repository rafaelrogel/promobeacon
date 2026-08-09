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
ESPTOOL="/home/rafael/.platformio/packages/tool-esptoolpy/esptool.py"
QEMU="${QEMU:-/home/rafael/.local/bin/qemu-system-riscv32}"
OUT="/tmp/qemu_selftest_${SUF}.log"
MERGED="/tmp/qemu_${SUF}_flash.bin"

# 1) Build do env QEMU
echo "== BUILD $ENV =="
( cd "$FW" && /home/rafael/pio_venv/bin/pio run -e "$ENV" ) || {
  echo "ERRO: build $ENV falhou"; exit 1; }
echo "BUILD OK"

# 2) Merge flash 4MB (bootloader@0x0, partitions@0x8000, app@0x20000) com pad
for f in "$BUILD/bootloader.bin" "$BUILD/partitions.bin" "$BUILD/firmware.bin"; do
  [ -f "$f" ] || { echo "ERRO: falta $f"; exit 1; }
done
rm -f "$MERGED"
echo "== MERGE (pad 4MB) =="
python3 "$ESPTOOL" --chip esp32c3 merge_bin \
  -o "$MERGED" --flash_mode dout --flash_size 4MB --flash_freq 40m \
  0x0 "$BUILD/bootloader.bin" \
  0x8000 "$BUILD/partitions.bin" \
  0x20000 "$BUILD/firmware.bin" || { echo "ERRO: merge falhou"; exit 1; }
# QEMU exige imagem de 2/4/8/16MB — pad até 4MB
truncate -s 4M "$MERGED"
echo "pad 4MB OK ($(stat -c%s "$MERGED") bytes)"

# 3) Roda QEMU (bounded pelo timeout de qemu; captura só linhas relevantes)
echo "== QEMU SELFTEST ($ENV) =="
rm -f "$OUT"
timeout 120 "$QEMU" -machine esp32c3 -nographic -no-reboot \
  -drive file="$MERGED",if=mtd,format=raw 2>&1 | grep -E "SELFTEST|ALL PASSED|FAIL|panic|abort" > "$OUT"

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
