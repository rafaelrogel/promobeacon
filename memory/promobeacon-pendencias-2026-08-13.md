# PromoBeacon — Pendências do teste manual 13-08-2026 (job 3/3 fechado)

Teste E2E real (tablet Samsung SM-T220 + ESP32-C3 ttyACM1, BLE) executado 13-08 12:40-13:05 UTC.
Resultado: conexão/auth/reboot OK; fluxo de SAVE de config QUEBRADO em 2 pontos.

## BUG 1 — "Failed to write device name" (app tenta gravar GAP 0x2A00, firmware não intercepta)
- **Sintoma**: após Save Config, snackbar "Failed to write device name". Log Android: `GATT_WRITE is not allowed` na char 0x2A00 (GAP device name, READ-only no NimBLE).
- **Causa raiz (confirmada no código)**: `h_device_name` em `firmware/main/ble_manager.c` é só DECLARADO (linha 86) e usado no handler (linha 670) — **nunca é registrado na tabela GATT**. O app (fix abbc102, writeDeviceName via GAP) escreve numa característica que o firmware não controla.
- **Impacto**: save de config sempre reporta erro, mesmo com o resto ok.
- **Fix sugerido (job 1, firmware)**: ou (a) registrar char custom com WRITE p/ device name (ex. 12345684-...) e apontar o app pra ela, ou (b) usar `ble_svc_gap_device_name_set()` p/ mudar o nome e expor WRITE no GAP. Ajustar app em consequência (job 2).

## BUG 2 — Persistência do promo text FALHOU (grave, confirmado em hardware)
- **Sintoma**: write "TESTE-PB-0813" em 1234567d passou (status=0), app mostrou o valor; **após reboot via BLE, campo voltou a "VISITE-NOS"**.
- **Causa provável**: bug conhecido `DEFERRED_UPDATE_PROMO_TEXT` — o deferred handler (ble_manager.c:281/324) não chama `save_promo_text()` de fato na cadeia do portal (g_mode_update_promotion_text roda, save não persiste / ou chama save_ssid errado). CONFIRMAR no código e corrigir.
- **Impacto**: nenhuma config de portal sobrevive a reboot. 
- **Fix sugerido (job 1, firmware)**: garantir `save_promo_text()` no handler deferred; depois job 3 valida com teste de reboot.

## Validação p/ amanhã (job 3/3)
1. BUG 1 corrigido → Save Config sem erro, device name atualiza.
2. BUG 2 corrigido → salvar TESTE-INTEGRACAO-0814, reboot, reconectar, confirmar que o campo mantém o valor.
3. Portal WiFi (pendência antiga, ainda não testado E2E): tablet no AP PROMOBEACON, salvar SSID via portal, verificar firmware aplica.

## Registro nos jobs (13-08 13:10 UTC)
- ✅ BUG 1 + BUG 2 incorporados nos prompts dos 3 jobs (1deb84ea firmware, b7043d3f app, 9c4046a7 integração).
- Job 3 de amanhã valida: save sem erro (BUG 1), persistência após reboot (BUG 2), portal WiFi E2E.

## Estado do hardware (13-08 13:05 UTC)
- Tablet R9PW30T4JQM desbloqueado (PIN já usado), app com.promobeacon.manager instalado, BLE on.
- ESP32-C3 em ttyACM1 (MAC ac:a7:04:d4:23:88), fw build 10 (esp32c3) rodando.
- Senha admin 12345 · AP PROMOBEACON · auth BLE 12345.
