# Plano de Teste — PromoBeacon App Android ↔ ESP32-C3

Data: 2026-08-02 · Status: AGUARDANDO desbloqueio do celular

## Setup

| Item | Valor |
|------|-------|
| ESP32-C3 | /dev/ttyACM0, MAC ac:a7:04:d4:23:88, flash 4MB |
| Firmware | build local `.pio/build/esp32c3/` (Aug 2 03:19) gravado com sucesso |
| AP WiFi | PROMOBEACON no ar (scan OK, -52 dBm) |
| Celular | Moto G35 5G, Android 16, adb OK, USB debugging ON |
| App | com.promobeacon.manager v2.1.4 (APK debug instalado, pid ativo) |
| Senha admin | fallback garantido: `12345` (firmware aceita) — ou a aleatória gerada no NVS (via UART0) |

## Compatibilidade verificada (análise estática)

- ✅ Serviço BLE `12345678-1234-1234-1234-123456789ABC` idêntico app ↔ firmware
- ✅ 13 características com UUIDs iguais (mode, message, config, status, promo_text, stats, sessions, session_ctrl, portal_data, portal_ctrl, auth, auth_status, admin_password)
- ✅ Comandos: CMD_MODE_G=0x00, CMD_MODE_E=0x01, CMD_REBOOT=0x02, CMD_RESET_DEFAULTS=0x03
- ✅ Auth: app envia senha raw bytes → firmware compara com verify_admin_password() OU "12345"
- ✅ Portal upload: chunks de 128B, controle via PORTAL_CMD_*
- ⚠️ NVS zerado (flash foi apagada) → firmware gera senha admin aleatória no 1º boot; `12345` sempre funciona como fallback

## Checklist de Teste (quando celular desbloqueado)

### 1. Scan BLE
- [ ] App mostra o dispositivo (nome PROMOBEACON / ESP32-C3)
- [ ] RSSI visível e atualizando
- [ ] Fallback show-all funciona (se UUID não aparecer)

### 2. Conexão GATT
- [ ] Conectar (MTU request → discover services)
- [ ] Estado CONNECTED
- [ ] Read device name
- [ ] Read promo text
- [ ] Notificações de status ativas

### 3. Autenticação
- [ ] Tentar senha errada → AUTH_STATUS_FAILED
- [ ] Tentar `12345` → AUTH_STATUS_SUCCESS
- [ ] Tentar senha admin real (se conhecida) → SUCCESS

### 4. Controle de Modo
- [ ] Mudar para Modo E (BLE beacon) → AP WiFi some, beacon aparece
- [ ] Mudar para Modo G (AP) → AP WiFi volta
- [ ] Verificar beacon no scan BLE externo

### 5. Configuração
- [ ] Escrever promo text → ler de volta
- [ ] Escrever SSID → AP muda de nome
- [ ] Escrever WiFi password

### 6. Portal Captive
- [ ] Upload de HTML via BLE (chunks 128B)
- [ ] Conectar ao AP PROMOBEACON e abrir portal
- [ ] Testar admin via X-Admin-Pwd (web)

### 7. Stress Test
- [ ] 20× conectar/desconectar rapidamente
- [ ] 50× write/read no promo text
- [ ] Upload portal 32KB completo
- [ ] Reboot do dispositivo (CMD_REBOOT)
- [ ] Reset de fábrica (CMD_RESET_DEFAULTS) — cuidado: apaga config
- [ ] Monitorar RSSI ao afastar/aproximar
- [ ] Verificar memória/estabilidade (sem crash do firmware)

### 8. Estabilidade
- [ ] App sem crash durante 10 min de uso contínuo
- [ ] Reconexão automática após ESP32 reiniciar
- [ ] Logcat sem erros fatais

## Observações

- Console serial do firmware vai para UART0 (GPIO), não USB — logs de boot só até "cpu_start" via USB.
- Senha admin aleatória é logada no UART0 no 1º boot: `DEFAULT ADMIN PASSWORD: XXXXXXXX`.
- Backup original: `esp32-dump/flash_full.bin` (SHA256 f93333c9...).
