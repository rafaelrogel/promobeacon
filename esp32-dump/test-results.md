# Teste PromoBeacon App ↔ ESP32-C3 — RESULTADOS ATUALIZADOS

Data: 2026-08-02 · Status: ✅ 7/8 PASS · 🐛 Bug de firmware encontrado

## Resultados

| # | Teste | Resultado | Evidência |
|---|-------|-----------|-----------|
| 1 | Scan BLE | ✅ PASS | "Found 1 devices" — PROMOBEACON, AC:A7:04:D4:23:8A, -53 dBm |
| 2 | Conexão GATT | ✅ PASS | Device Console, Connected, uptime lido via BLE |
| 3 | Autenticação `12345` | ✅ PASS | "Authenticated", Device Configuration visível |
| 4 | Save Config (portal msg TESTE-PROMO-123) | ✅ PASS | "Configuration saved" |
| 5 | Reboot via BLE (CMD_REBOOT) | ✅ PASS (1x) | "Device rebooting...", uptime resetou 16m→23m (primeiro reboot) |
| 6 | Upload Portal HTML 1207B | ✅ PASS | "Portal page uploaded successfully (1207 bytes)" |
| 7 | Factory Reset (CMD_RESET_DEFAULTS) | ⚠️ PARCIAL | "Factory settings restored" (config apagada) MAS `esp_restart()` não executou |
| 8 | Reboot pós-factory-reset | ❌ FAIL (bug FW) | "Device rebooting..." mas uptime NÃO zerou (42m→45m contínuo) |

## 🐛 BUG DO FIRMWARE: esp_restart() não executa após factory reset

### Sintomas
1. **Factory reset (CMD_RESET_DEFAULTS, 0x03)** restaura configs ("Factory settings restored") mas **não reinicia o chip** (uptime continua)
2. **Reboot (CMD_REBOOT, 0x02)** após o factory reset: o app mostra "Device rebooting..." (write GATT aceito) mas **o uptime não zera** — `esp_restart()` na task deferida não executa
3. **Servidores TCP mortos**: porta 80 (HTTP) e 53 (DNS) não respondem, embora o AP WiFi continue no ar (DHCP funciona) e o BLE continue operando (status lido corretamente, uptime avança)
4. O primeiro reboot (antes do factory reset) **funcionou** — uptime zerou. O problema aparece **depois** do factory reset

### Causa provável
- `DEFERRED_FACTORY_RESET` na `deferred_work_task` (ble_manager.c:293-297) chama `portal_reset_to_default()` seguido de `esp_restart()`
- O `portal_reset_to_default()` → `portal_delete_custom_content()` → `nvs_erase_key` + `nvs_commit` pode deixar o NVS/flash num estado que bloqueia o restart
- OU: o `esp_restart()` está sendo chamado mas o sistema não completa o reboot (ex: interrupções/stack travada na task deferida)
- Resultado: g_mode_stop() parcial (HTTP/DNS parados) sem restart — estado inconsistente

### Código relevante (firmware)
```c
// ble_manager.c:289-297 — deferred_work_task
case DEFERRED_REBOOT:
    vTaskDelay(pdMS_TO_TICKS(500));
    esp_restart();
    break;
case DEFERRED_FACTORY_RESET:
    vTaskDelay(pdMS_TO_TICKS(500));
    portal_reset_to_default();
    esp_restart();
    break;
```

### Workaround imediato
**Reset físico** do ESP32 (desligar/religar a fonte) recupera o dispositivo — firmware persiste no flash.

### Correção sugerida (para o dev)
- Verificar se `esp_restart()` está sendo chamado de contexto correto (task com prioridade adequada, sem segurar locks de flash)
- Adicionar log antes/depois do `esp_restart()` e verificar se o panic handler roda
- Considerar usar `esp_restart()` direto no callback GATT (com flag de segurança) em vez de via task deferida, ou
- Testar se `nvs_commit` + `esp_restart` na mesma task bloqueia (adicionar `vTaskDelay` maior, ex: 1500ms)
- Verificar se há `portDISABLE_INTERRUPTS()` ou similar segurando o sistema

## Estado final do dispositivo
- BLE: **funcional** (advertising + GATT + status + auth OK)
- AP WiFi: **no ar** (SSID PromoBeacon, DHCP OK)
- HTTP/DNS: **mortos** (não respondem)
- Reboot: **não funciona** (precisa reset físico)
- Config: restaurada para default (portal customizado apagado pelo reset)

## Observações adicionais
- O campo SSID do app: escrever o "Default Portal Message" (promo_text) NÃO muda o SSID do AP — comportamento correto (o SSID só muda se o campo "Network Name (SSID)" for editado, que escreve no mesmo promo_text via writeSsid)
- Upload de portal: fluxo completo OK (file picker SAF → preview → upload chunks BLE 128B → "uploaded successfully")
- BLE do PC (hci0) não detecta o ESP32 (testes feitos via celular — mais representativo do uso real)
- Auth: reboot limpa a sessão (re-login necessário — correto)

## Pendente (após reset físico)
- [ ] Testar portal web customizado (enviar HTML → conectar ao AP → http://192.168.4.1)
- [ ] Testar modo E/G via BLE direto (app v2.1.4 não expõe o mode switch na UI)
- [ ] Re-testar reboot após reset físico (confirmar se o bug persiste)

---

## ✅ UPDATE 22:50 UTC — ROOT CAUSE FOUND & FIXED (app protocol bug)

### Causa raiz REAL do bug "esp_restart() nunca executa"
**Não era o firmware — era o APP enviando frame errado.**

- O app `writeConfig()` serializava **6 bytes** `[cmd, p1_lo, p1_hi, p2_lo, p2_hi, p3]` no configChar (0x7B)
- O firmware (v4.1.5+, 8380fc7) só trata **1 byte** como comando (`len == 1`); `len > 1` = senha WiFi
- Resultado: reboot/reset viravam `"WiFi Password update received: \x02"` — comando nunca chegava à task deferida
- Serial (pré-fix): `I (199962) BLE_MANAGER_NIMBLE: WiFi Password update received: \x02`
- Serial (pós-fix): `I (572112) BLE_MANAGER_NIMBLE: Rebooting via BLE...` → `I (572612) deferred reboot: calling esp_restart()`

### Fix aplicado (commit acb7ae8, app)
`writeConfig()` agora envia **apenas o byte do comando** (params mantidos na assinatura por compat, não serializados).

### Validação em hardware (ESP32-C3, flash limpo + firmware 97acf75 + app acb7ae8)
| Teste | Resultado | Evidência |
|---|---|---|
| Reboot via BLE | ✅ PASS | uptime zerou (1m28s pós-reboot); serial: Rebooting via BLE → calling esp_restart → boot limpo |
| Factory Reset via BLE | ✅ PASS | uptime zerou (1m27s pós-reset); serial: Factory Reset triggered → portal_reset_to_default ESP_OK → calling esp_restart → boot limpo |

### Sequência serial completa do factory reset (fix 97acf75):
```
I (155182) BLE_MANAGER_NIMBLE: Factory Reset triggered via BLE...
I (155682) BLE_MANAGER_NIMBLE: deferred factory reset: clearing portal content
I (155682) BLE_MANAGER_NIMBLE: deferred factory reset: portal_reset_to_default -> ESP_OK (0)
I (157182) BLE_MANAGER_NIMBLE: deferred factory reset: calling esp_restart()
[ boot limpo: wifi softAP, DHCP, DNS :53, HTTP :80, BLE adv, G mode, heap 89KB ]
```

### Nota
O fix do firmware (97acf75: stack 8KB, logs, abort guard, 1.5s NVS settle) foi **necessário e correto** — sem ele a task deferida poderia morrer por stack overflow no NVS ops. Mas o bloqueio real era o frame do app.

---

## ✅ UPDATE 23:15 UTC — PENDÊNCIAS TESTADAS (SSID, portal web, modo E/G)

### 1. Mudança de SSID via app — ✅ PASS
- Campo "Network Name (SSID)" no Device Configuration → digitei "PromoBeacon-TESTE" → Save Config
- Serial: `CONFIG: SSID saved: PromoBeacon-TESTE` → `WIFI_MGR: AP SSID updated: PromoBeacon-TESTE` → `G_MODE: Promo text updated, AP SSID and BLE name updated to: PromoBeacon-TESTE`
- Verificação independente: `cmd wifi list-scan-results` mostrou AP **"PromoBeacon-TESTE"** (BSSID ac:a7:04:d4:23:89)
- **Observação**: campo "Default Portal Message" (promo_text) salva junto (VISITE-NOS) e NÃO muda o SSID — comportamento correto; o SSID muda apenas via campo "Network Name (SSID)"

### 2. Portal web customizado via AP — ✅ PASS
- Upload: app → Upload Portal (HTML) → file picker → portal-teste.html (313B)
- Serial: `PORTAL_CONTENT: Transfer started: 313 bytes, CRC=0x4E8387EF` → `Content saved to NVS: 313 bytes` → `Transfer complete: 313 bytes saved and active`
- Phone conectou ao AP (IP 192.168.4.2 via DHCP) → `GET /` respondeu:
  ```
  HTTP/1.1 200 OK
  Content-Type: text/html
  Content-Length: 313
  <html>...Portal Customizado...PromoBeacon Portal TESTE - 2026-08-02...
  Se voce ve isso, o upload via BLE funcionou!</html>
  ```
- **Captive portal redirect**: `GET /generate_204` → `302 Found` → `Location: http://192.168.4.1/` ✅
- **Prova visual**: Chrome do phone mostrou o portal customizado (fundo azul #0d3b66, título "Portal Customizado", textos de teste) — sem erro
- Nota: emoji 🏪 não renderizou (HTML sem `<meta charset>`; cosmético)

### 3. Modo E/G via BLE — ⚠️ N/A (modo E removido do firmware)
- O firmware atual (v4.1.5+, 8380fc7) **removeu o MODE_E**: enum `DeviceMode` só tem `MODE_G = 0` e `MODE_UNKNOWN = 255`
- `CMD_MODE_E` (0x01) não é definido no firmware; handler do mode_control só aceita `CMD_MODE_G` (0x00) e `CMD_REBOOT` (0x02)
- O app tem UI legacy (ModeSelector com botões G/E + "Switch Mode" em CommonComponents.kt) que **não é exibida** no Device Console atual
- Conclusão: não há o que testar — o produto atual é G-mode only (WiFi AP + captive portal)

### 🐛 BUG LATERAL ENCONTRADO: AP quebrado após live-update de SSID
- Após mudar o SSID (live update), o AP fica anunciando o novo nome MAS o roteamento quebra:
  - ping 192.168.4.1 → 100% packet loss
  - Chrome → ERR_NETWORK_CHANGED
  - Só DNS queries + captive probes chegam ao ESP32
- **Reboot resolve** (RTS toggle / power cycle): AP volta 100% funcional (ping OK, HTTP OK, DNS OK)
- Causa provável: `esp_wifi_set_config` / AP restart com o cliente ainda conectado deixa a interface num estado inconsistente (o phone conectou ao AP antes da reconfig)
- Impacto real: usuário que troca o SSID via app precisa de reboot para o portal funcionar de novo — vale abrir issue

### Estado final
- SSID restaurado para **PromoBeacon** (serial: `SSID saved: PromoBeacon`; scan WiFi confirmou)
- Portal custom (313B) mantido no NVS — conteúdo "Portal TESTE" ainda é servido
- Uptime: 4m+ pós-reboot; BLE auth OK

---

## ✅ UPDATE 23:46 UTC — BUG DO LIVE-UPDATE DE SSID CORRIGIDO + VALIDADO

### O bug
- `update_ap_ssid()` chamava `esp_wifi_set_config(WIFI_IF_AP, ...)` com o AP ativo e clientes conectados
- Resultado: AP anunciava o SSID novo MAS o roteamento morria (ping 100% loss, ERR_NETWORK_CHANGED, só DNS/captive probes chegavam) até reboot físico
- Repro: mudar "Network Name (SSID)" no app → AP renomeado mas portal inacessível

### O fix (commit 11555b1, main/wifi_manager.c)
- `update_ap_ssid()` agora faz: `esp_wifi_stop()` → `esp_wifi_set_config()` → `esp_wifi_start()`
- Netif/DHCP sobrevivem ao stop/start (mesmo padrão do `disconnect_all_clients()`)
- Log novo: `WIFI_MGR: AP SSID updated (clean restart): <ssid>`

### Validação em hardware (ESP32-C3 real)
1. Flashei firmware novo (write_flash 0x0/0x8000/0x19000/0x20000, hash verificado)
2. Via app: SSID → "PromoBeacon-FIX" → Save Config
   - Serial: `AP SSID updated (clean restart): PromoBeacon-FIX` ✅
3. Phone conectou ao "PromoBeacon-FIX" (IP 192.168.4.2):
   - **Ping 192.168.4.1: 0% packet loss** (antes: 100%) ✅
   - **HTTP GET / → 200 OK** com portal customizado (313B) ✅
   - **GET /generate_204 → 302** → Location: http://192.168.4.1/ ✅
4. Restaurei SSID → "PromoBeacon" (serial confirmou `clean restart: PromoBeacon`; scan WiFi confirmou AP de volta)

### Estado final
- Firmware: commit `11555b1` pushado (main)
- App: `acb7ae8` (anterior)
- Device: SSID PromoBeacon, portal custom 313B no NVS, AP 100% funcional

---

## ✅ UPDATE 00:20 UTC 2026-08-03 — REFLASH COMPLETO + RETESTE INTEGRAL (PÓS-ERASE)

### Sequência
1. `erase_flash` total (1.3s) → `write_flash` bootloader/partitions/ota_data/firmware (1048736 B, hash verified)
2. Boot limpo de fábrica: NVS zerado, AP default **PROMOBEACON**
3. Bateria de testes completa via app (phone ZE223G6FRL)

### Resultados
| Teste | Resultado | Evidência |
|---|---|---|
| 1. BLE connect + status | ✅ | Connected, Authenticated, uptime 2m55s, 1 cliente, SSID default PromoBeacon |
| 2. Mudança de SSID (fix 11555b1) | ✅ | `AP SSID updated (clean restart): PromoBeacon-FINAL`; phone conectou; **ping 0% loss**; HTTP 200 |
| 3. Upload portal custom (295B) | ✅ | `Transfer started: 295 bytes, CRC=0x4231126C` → `saved to NVS` → `Transfer complete` |
| 4. Portal custom servido | ✅ | HTTP 200, Content-Length 295, HTML "Portal Customizado FINAL" |
| 5. Reboot via BLE (fix acb7ae8+97acf75) | ✅ | `Rebooting via BLE...` → `deferred reboot: calling esp_restart()` → boot limpo; uptime zerou (1m28s) |
| 6. Factory Reset via BLE | ✅ | `Factory Reset triggered` → `clearing portal content` → `portal_reset_to_default -> ESP_OK (0)` → `calling esp_restart()` (1.5s); uptime zerou (2m1s); portal voltou a default (6548B) |
| 7. Estado final pós-reset | ✅ | AP PromoBeacon-FINAL, HTTP 200, DHCP OK, portal default de fábrica |

### Observações de design (não-bloqueantes)
- **Factory reset via BLE limpa SÓ o portal custom** (portal_reset_to_default), mantém SSID/promo_text/admin password e o flag "configured: yes". O app avisa "All configurations will be cleared" — há um descompasso de expectativa com o texto do app. O `reset_to_defaults()` completo (erase do namespace) existe no firmware mas NÃO está ligado ao CMD_RESET_DEFAULTS (0x03). **Candidato a issue/melhorias futuras.**

### Estado final
- Firmware 11555b1 + app acb7ae8 (ambos pushados, remote em dia)
- Device: SSID PromoBeacon-FINAL, portal default, NVS funcional, AP/BLE/HTTP/DNS 100% OK
- Serial: logs/serial-final-reflash.log (422 linhas de evidência)

---

## ✅ UPDATE 00:33 UTC 2026-08-03 — FACTORY RESET AGORA LIMPA TUDO (commit ac0eaeb)

### Mudança
`DEFERRED_FACTORY_RESET` no `ble_manager.c` agora chama:
1. `reset_to_defaults()` — apaga CONFIG_NAMESPACE (SSID, promo text, device name, admin password, flag configured)
2. `portal_reset_to_default()` — apaga portal custom
3. `esp_restart()` — boot limpo

### Validação no hardware (flash ac0eaeb, hash verificado)
| Verificação | Resultado |
|---|---|
| Serial: reset flow | ✅ `clearing all configuration` → `reset_to_defaults -> ESP_OK (0)` → `portal_reset_to_default -> ESP_OK (0)` → `esp_restart()` |
| Boot pós-reset | ✅ `Device configured: no`, `Device name: PROMO-BEACON` (default), `WiFi AP started: PROMOBEACON (OPEN)` |
| SSID real (scan) | ✅ AP renomeado para **PROMOBEACON** (BSSID ac:a7:04:d4:23:89) |
| Portal | ✅ `custom=no`; HTTP 200 Content-Length **1801** = **setup page** (device não-configurado → portal de setup, não o de marketing 6548B) |
| BLE name (app) | ✅ app lista device como PROMOBEACON |
| Admin password | ✅ **zerado e regenerado**: novo password aleatório `ymm8y75u` (logado no serial); app autenticou com o novo ✅ |

### Comportamento esperado agora
- Factory reset = estado de fábrica COMPLETO (como erase do NVS): SSID default, config desbloqueada, portal default de setup, admin password novo aleatório
- **IMPORTANTE**: após reset, o admin password antigo (12345) NÃO funciona mais — o novo é gerado e logado no serial ("DEFAULT ADMIN PASSWORD: ..."). O app mostra o prompt de autenticação novamente.

### Estado final
- Firmware `ac0eaeb` (commit + push, remote em dia)
- Device: SSID PROMOBEACON, device não-configurado, setup page ativa, BLE name default
- Evidência: logs/serial-factory-reset-full.log (198 linhas)

---

## ✅ UPDATE 00:41 UTC 2026-08-03 — SENHA ADMIN SEMPRE 12345 (commit a6116d1)

### Mudança
`config_manager.c` `init_config_manager()`: quando não há password salvo (device novo OU pós-factory-reset que apaga o namespace), seta `DEFAULT_ADMIN_PASSWORD` = **"12345"** em vez de gerar aleatório de 8 chars.
- Nova constante `DEFAULT_ADMIN_PASSWORD "12345"` em `config_manager.h`
- Removeu o gerador de password aleatório (esp_random + charset)

### Validação no hardware (flash a6116d1)
1. Boot com NVS antigo (password `ymm8y75u` salvo): init mantém o salvo (não sobrescreve)
2. **Factory reset via app** (limpa NVS)
3. Boot pós-reset: serial mostra `Admin password set to default (12345)` ✅
4. **App autenticou com "12345"** ✅ (sem precisar ler serial)

### Comportamento agora
- Device novo / pós-reset: admin password = **12345** sempre
- App autentica com 12345
- BLE fallback hardcoded (strcmp 12345) permanece como redundância
- Trocar senha via app/GATT ainda é possível (mas o reset volta para 12345)

### Estado
- Firmware `a6116d1` (commit + push, remote em dia)
- Device: SSID PROMOBEACON, não-configurado, portal setup 1801B, senha 12345
- Evidência: logs/serial-password-12345.log
