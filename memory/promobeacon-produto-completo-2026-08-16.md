# PromoBeacon — Plano rumo ao Produto Completo e Perfeito

Data: 16-08-2026 13:00 UTC. Objetivo do Rafael: seguir em direção ao produto completo e perfeito.

## Estado validado HOJE (16-08, tarde — E2E real, não confiar só em commits)
- Portal WiFi `192.168.4.1/` configurando SSID+senha via tablet, persiste no NVS → AP renomeou (modo G). ✅
- Fluxo BLE do app: conecta (MAC AC:A7:04:D4:23:8A), auth `12345`, Device Configuration. ✅
- **BUG descoberto HOJE e CORRIGIDO + INSTALADO (APK 2.1.4 verCode 9):** campo "Network Name (SSID)" do app era phantom — `writeSsid()` é no-op no BLE client; SSID é dirigido pelo promo text no firmware. Editar era descartado silenciosamente. Fix: campo SSID agora read-only (placeholder=promo text) + legenda; save persiste `ssid = promoText`. Commit `8720e66` (pushed 16-08).
- Beacons resetados: firmware como `PROMOBEACON` (AP + BLE), NVS limpo (só admin_pass=12345 default). ✅
- Keystore: RECRIADO 08-08 (chave nova). APK release 2.1.4 (verCode 9) assinado e instalado no tablet.

## Device name (BUG 1) — adicionar verificado
- Firmware `h_device_name` (UUID 12345684-...) registrado WRITABLE (commit 055901e). App `writeDeviceName` grava nessa char (commit 0752d91). **JOB 2 deve CONFIRMAR via E2E no tablet que Save Config escreve device name SEM erro 'Failed to write device name'.**

## Checklist produto completo (foco da run de hoje)
1. **Suíte de testes do app** (projeto começou com ZERO; há alguns unit/instrumented). Rodar:
   - `./gradlew testDebugUnitTest` (JVM)
   - `./gradlew connectedAndroidTest` no tablet conectado via ADB (R9PW30T4JQM) — validar instrumented E2E.
2. **Pendências do firmware** (conhecidas):
   - `<meta charset="UTF-8">` nos portais HTML (setup + promo) — hoje emoji quebram.
   - `captive_portal_mode` (comportamento de detection).
3. **App — UI stale pós-reconnect:** após reconectar, campos podem mostrar valor antigo; garantir reload do firmware (read), não cache local.
4. **Documentação de setup do cliente final:** roteiro de instalação do APK + config manual do beacon (portal) — para delivery do piloto/venda.
5. **Empacotamento/Release:** APK release 2.1.4 assinado e instalado; documentar que assinatura é a NOVA (builds anteriores precisam desinstalar).

## Prioridades por job (run de hoje)
- **Job 1 (firmware):** `meta charset` nos dois portais; revisar `captive_portal_mode`; build esp32c3 + QEMU selftest 79/79; flash real; commit.
- **Job 2 (app):** rodar `testDebugUnitTest` + `connectedAndroidTest` no tablet; corrigir UI stale pós-reconnect; build release; instalar; commit.
- **Job 3 (integração + relatório):** E2E completo — BLE auth, Save Config com device name (valida BUG 1), persistência promo text via REBOOT via BLE, portal WiFi; rodar testes que faltarem; push; relatório consolidado ≤30 linhas.

## Hardware
- ESP32-C3 real (PID 303a:1001). Porta detectar dinamicamente: `ESP_PORT=$(for p in /sys/class/tty/ttyACM*; do [ "$(cat $p/device/../idVendor 2>/dev/null)" = "303a" ] && echo "/dev/$(basename $p)"; done | head -1)` (hoje /dev/ttyACM1; ttyACM0=tablet Samsung 04e8:6860).
- Esptool: `/home/rafael/.platformio/packages/tool-esptoolpy/esptool.py` (via `python3`). qemu: `/home/rafael/.local/bin/qemu-system-riscv32`.
- Build firmware: `/home/rafael/pio_venv/bin/pio run -e esp32c3` (NUNCA esp32dev). Flash: SEMPRE erase_flash antes via `sg dialout`.
- Tablet ADB: R9PW30T4JQM (Samsung Tab A7 Lite, Android 14).
- Senha admin: `12345`. BLE MAC: AC:A7:04:D4:23:8A.

## Regras de contexto dos jobs (não reincidir erros de 08-09)
- Comandos ISOLADOS, um por exec. NUNCA cadeias gigantes/encadeadas.
- agy OBRIGATÓRIO p/ coding com parametrização: `cd ~/workspace/promobeacon && agy --model gemini-3.1-pro --effort low --dangerously-skip-permissions` (via tmux), COM `--effort low|high` (sem ele vira interativo).
- grep/sed em vez de ler arquivos inteiros. UI dumps resumidos ≤20 linhas. Estado em /tmp/promobeacon-notes.md. Commit frequente. Relatório SEMPRE entregue, mesmo parcial.
