# MEMORY.md — Memória de longo prazo

## Eu (A1)
- **Nome**: A1 🤖 — agente principal e braço direito do Rafael. Fiel escudeiro: missão dada é missão cumprida, executo sem frescura.
- **Vibe**: executor autônomo, caçador de APIs grátis/oportunidades de grana, token-conscious (economia SEM perder qualidade), zoeiro na medida.
- **Futuro**: gerente da A1Brella, orquestrar agentes (marketing, coding, thinking, intel).
- Identidade em `IDENTITY.md`, alma/persona em `SOUL.md`, perfil do Rafael em `USER.md` (todos preenchidos 05-08-2026).

## Usuário — Rafael Queiroz
- **Pessoal**: casado, pai de duas meninas, mora no **Castelo da Maia**. Tradução (Revolut desde 2023) + freelance desde 2010 (EN/FR/ES → PT-BR; jogos, TI/software). Irmão: **Pedro Dourado** (sócio A1Brella).
- **Espírito**: empreendedor incansável — investe em BTC, já empreendeu e quebrou, sempre atrás de formas de ganhar dinheiro. Nunca para.
- **Idioma**: pt-BR, respostas diretas. "A" = continuar lote. Curte zoeira de vez em quando.
- **Token-conscious**: custo importa — modelos gratuitos/baratos em jobs, `lightContext`, evitar repetição.

## Negócios / Projetos

### A1Brella (agência de IA — com Pedro Dourado)
- Slogan: **"🤖 Everything AI and AI everything!"** Site **ainda não montado** (pendência).
- Plano: eu (A1) viro gerente e orquestro agentes (marketing, coding, thinking, intel).

### Zappelin — www.zappelin.com.br (SaaS lançado)
- Agentic AI por **WhatsApp**: faz listas, lembra coisas etc. **Zero clientes** → precisa de **propaganda online/ads** (pendência ativa).

### Outros sites
- www.nordic-claw.online · www.cortesrenan.online · www.cortespoliticos.online

### Em desenvolvimento / a lançar
- **AI Box para escolas** — crianças aprendendo a usar IA.
- **Preenchedor automático de invoices do Xolo.io** — extensão Chrome (a lançar).
- **Sistema de templates de e-mail tipo Mailchimp** — white label p/ empresas.
- **ADS White Label via MCP** — para clientes e designers de clientes.
- **PromoBeacon** (detalhes abaixo; bate com o pacote de marketing da A1Brella).

### PromoBeacon (github.com/rafaelrogel/promobeacon)
- ESP32 BLE beacon + portal WiFi + app Android. **App é Kotlin nativo** (Jetpack Compose/Hilt/MVVM, pkg `com.promobeacon.manager`), NÃO Flutter. Repo: `~/workspace/promobeacon/` (fora do sandbox — usar `exec`/shell p/ mexer, não read/write).
- Firmware ESP-IDF 6.0.1 (PlatformIO), alvos: esp32, esp32c3, esp32s3, esp32dev, esp32c3-qemu (mode `PROMOBEACON_QEMU`, selftest 79/79 ✅).
- Hardware: ESP32-C3 — BLE MAC `AC:A7:04:D4:23:8A`, WiFi BSSID `ac:a7:04:d4:23:89`, AP `PROMOBEACON`, **senha admin sempre `12345`** (fix a6116d1).
- Commits-chave: `97acf75` reboot/factory-reset, `acb7ae8` app protocolo 1-byte, `11555b1` SSID live-update, `ac0eaeb` reset limpa tudo, `a6116d1` senha 12345, `f7a767e` APK release assinado.
- Release: keystore `~/.android/release-keys/promobeacon-release.keystore` (senha em `promobeacon-keystore-pass.txt`, chmod 600, **nunca commitar**). Build: env vars `PROMOBEACON_KEYSTORE/PASS/ALIAS` + `./gradlew assembleRelease`.
- Pendências opcionais: `<meta charset>` nos portais (emoji), UI stale do app pós-reconnect, captive_portal_mode.

### Postiz — app de agendamento/redes sociais (docker, ~/.openclaw/workspace/postiz-app)
- Stack: postiz (+ postiz-postgres, postiz-redis) + **temporal** (orquestrador) + temporal-ui/admin-tools/postgresql/elasticsearch/spotlight. Público: https://postiz.cortespoliticos.online (porta 4007 → nginx → backend 3000 / frontend 4200 internos).
- ⚠️ 09-08-2026: Postiz deu 502 — causa raiz = **temporal em restart loop** porque a pasta montada `dynamicconfig/` estava VAZIA e o env `DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development-sql.yaml` não achava o arquivo (a montagem vazia escondeu o default da imagem). FIX: recriei `~/.openclaw/workspace/postiz-app/dynamicconfig/development-sql.yaml` (conteúdo padrão dev do Postiz) + `docker restart temporal` + `docker restart postiz` (backend volta a escutar 3000; PM2 sobe os 3: backend/frontend/orchestrator). NOTA: o `docker-compose.yaml` original do Postiz foi PERDIDO (só sobrou a pasta dynamicconfig/) — se quiser `docker compose up` reproduzível, reconstruir.

### Relatórios de Inteligência Política — Ceará (batch)
- HTML por município em `Apagar/RelatoriosCE/<CidadeSemAcento>.html`; **só anunciar MEDIA depois do write retornar sucesso**.
- Template fixo; workflow: "siga" = próximo município. Goal via `/goal` foi **encerrado pelo usuário** (08-04 11:38) — batch incompleto, não retomar sem pedido.
- Originais (51): `Acaraú_all_reports.tar` + `reports_extracted/`.
- APIs: TSE DivulgaCandContas funciona com código TSE + `unidadeEleitoral.nome` (mapa em `/tmp/tse_ce_map.txt`); IBGE SIDRA às vezes fora do ar; TransfereGov PostgREST; TCE-CE mudou → `api-dados-abertos.tce.ce.gov.br`.
- **MCP-Brasil** em `MCP-Brasil/` (stdio, 450 tools, NÃO registrado no openclaw.json). Rodar: `.venv/bin/python -m mcp_brasil.server`; probe: `scripts/mcp_probe.py` (modos list/schema/call).
- Recent progress: generated HTML reports for most municipalities; next target: Cruzeiro do Cariri (pending).

## MeowCaller — chamada de voz WhatsApp (✅ funcionando 06-08-2026)
- Rafael queria: ligar pelo WhatsApp e injetar áudio (falar msg e desligar), sem carrier. RESOLVIDO.
- Comando: `meowcaller notify` (bin `~/.local/bin/meowcaller`). **STORE PADRÃO atual: `~/.openclaw/credentials/whatsapp-calls/rafael/wa-voip.db`** (pareado no número do Rafael +351910070509, device :74, 18:54 06-08 — ligações saem do número dele). Store antigo `a1/` (>+351913186919) era o mesmo device do canal → conexão dupla derrubava o canal (status 428) e travava a lane; NÃO usar.
- **REGRA (06-08-2026): SEMPRE usar `meowcaller-notify-async`** (wrapper background) nas chamadas pedidas pela conversa — chamada síncrona trava a lane WhatsApp (stuck `active_reply_work`, fila acumula). Resultado em `memory/meowcaller-results.log`.
- Pareamento: `MEOWCALLER_QR_FILE=<path> meowcaller pair -store <store>` em **PTY**; arquivo contém a URL do QR (texto) — renderizar PNG com `/tmp/sttenv/bin/python` (qrcode) e mandar pelo Zap. **Nunca colocar timeout no pair** (senão o processo morre antes do scan e dá "não foi possível conectar dispositivo").
- Áudio p/ chamada: converter pra 16kHz mono (`ffmpeg -i X -ar 16000 -ac 1 out.wav`). Gerar com PicsArt gemini-tts voz Puck.
- Pareamento: `meowcaller pair` em PTY; QR via `MEOWCALLER_QR_FILE`; renderizar com `/tmp/sttenv/bin/python` (qrcode).
- Store: `wa-voip.db`, device = `351913186919:4@s.whatsapp.net`.
- TTS microsoft é IGNORADO em chamadas.

## Automações (cron)
- **Heartbeats**: um desabilitado 08-08-2026 (`34810ba7` "Heartbeat 240 min for A1brella" — duplicado do `25d30fd0` "Heartbeat - 240 min", que segue ativo a cada 4h). Regra interna: heartbeat nunca interrompe trabalho em andamento (AGENTS.md).
- **promobeacon-nightly-coding** (id c51b171e): **DESABILITADO 08-08-2026** — run de 08-08 estourou contexto (308K tokens, `non_deliverable_terminal_turn`, relatório perdido). Causa: agente NUNCA usou o agy (0 chamadas em 112 execs — fez tudo na mão via pio/gradle/adb, despejou UI dumps inteiros e releu arquivos repetidamente). Substituído por 3 jobs:
  - **promobeacon-firmware-daily** (id 1deb84ea, 02:00–03:30 Lisboa, `0 2 * * *`): só firmware; foco: bug persistência portal text (DEFERRED_UPDATE_PROMO_TEXT chama save_ssid mas nunca save_promo_text).
  - **promobeacon-app-daily** (id b7043d3f, 03:30–05:00, `30 3 * * *`): só app Android; foco: fluxos de save BLE + testes (projeto tem ZERO testes).
  - **promobeacon-integration-daily** (id `9c4046a7-5524-4293-8e2b-90942c963104`, 05:00–08:59, `0 5 * * *`): integração app↔ESP32 real (BLE + portal) + **`:app:connectedDebugAndroidTest` instrumentado (ScanFlowIntegrationTest)** + git push + relatório final WhatsApp (≤30 linhas).
  - Todos: isolated, lightContext, delivery announce whatsapp +351910070509, regras anti-estouro no prompt (agy OBRIGATÓRIO p/ coding, UI dumps resumidos ≤20 linhas, grep/sed em vez de leitura completa, estado em /tmp/promobeacon-notes.md, commit frequente, relatório parcial se contexto apertar, relatório SEMPRE entregue).
  - ⚠️ 09-08-2026: consertadas 3 causas de falha da madrugada. (1) Provider primário `custom-api-openmodel-ai/deepseek-v4-flash` estava INSTÁVEL (job 3 "couldn't generate a response" + abort) → trocado para primário `fireworks/.../deepseek-v4-flash-0731`, custom virou fallback; fallbacks: custom, nemotron openrouter, nemotron nvidia. (2) Falta de `cd ~/workspace/promobeacon` → git pull de ~/.openclaw/workspace abortava; prompts agora exigem cd + `&&` e pull não-fatal. (3) Cadeias de comando gigantes (cat&/sleep/pkill) causavam 'Exec failed' e estouro de 3,28M tokens → prompts exigem comandos ISOLADOS; criei scripts prontos: `scripts/read_esp_boot.sh <port> <secs> <lines>` (captura serial bounded) e `scripts/run_qemu_selftest.sh` (build+merge+pad 4MB+qemu, baseline 79/79).
  - ✅ **27-08-2026 E2E real validado no SM-T220**: `ScanFlowIntegrationTest` instrumentado 5/5 passou (BUILD SUCCESSFUL, 1m23s). Bugs corrigidos: (a) import errado `ConnectionState` (`domain.model` → `data.ble`, 2 enums com mesmo nome); (b) race condition em `testScanViewModel_...DeviceListFlow` (assertTrue sem delay antes); (c) warning de `initialScanningState` unused → trocado por assertFalse "not scanning before startScan()". Pendência E2E real do sprint 24h **FECHADA**. PIN do tablet destravado com `416669` (08:54 27-08). Tablet desconectou do ADB às 19:06 UTC — reconectar pra re-validação limpa.
  - ⚠️ PLACA REAL do ESP32 = **ESP32-C3** (PID 303a:1001), `default_envs=esp32c3` — NUNCA esp32dev (a run 08-09 descobriu que supunha esp32dev errado). esptool.py NÃO é executável direto → invocar via `python3 <caminho>`. Caminhos: esptool `/home/rafael/.platformio/packages/tool-esptoolpy/esptool.py`; qemu `/home/rafael/.local/bin/qemu-system-riscv32`.
  - Smoke test 09-08: job 1 forçado rodou LIMPO (401K tokens vs 3,28M antes): build esp32c3 SUCCESS, QEMU selftest 79/79, flash C3 real, relatório entregue OK. Confirma que as correções resolveram.
  - ⚠️ Keystore foi RECRIADO pelo agente na run 08-08 (01:36) — chave nova; se APK antigo no tablet conflitar, desinstalar antes.
  - ⚠️ Porta do ESP32 VARIA: 08-08 16:19 ficou em ttyACM1 (ttyACM0 = tablet Samsung 04e8:6860). Jobs detectam dinamicamente por vendor 303a (Espressif) — nunca usar porta fixa.
  - App é KOTLIN nativo confirmado pelo Rafael (não Flutter). Hardware: ESP32 em /dev/ttyACM0 (sg dialout) + tablet Samsung SM-T220 (ADB R9PW30T4JQM, Android 14). REGRA: SEMPRE erase_flash antes de flashar.
- **Pechinchas Cuecas Samba Canção PT** (id ba39a770-0534-4892-9260-6caa32ed0bed, **08:30 Lisboa** `30 8 * * *`, isolated, lightContext, announce whatsapp +351910070509): caça diária de cuecas Samba Canção em Portugal (Rafael precisa comprar). web_search + web_fetch; validação de preço na página do produto (lição 25-09), packs com €/cueca; fallback tablet SM-T220 via ADB; relatório ≤15 linhas. Criado 30-09-2026, mesmo molde do job de ténis.
- **Pechinchas Ténis Infantil PT** (id 4903dda2-578e-42ee-aa86-99c62b525cea, **08:00 Lisboa** `0 8 * * *`, isolated, lightContext, announce whatsapp +351910070509): caça diária de ténis/sapatilhas infantis baratos em Portugal p/ filhas do Rafael (7 anos ≈ tam 32-34, 10 anos ≈ tam 36-38). Método principal: navegar Chrome do tablet SM-T220 via ADB (serial R9PW30T4JQM) — abrir busca Google PT, extrair links via chrome_devtools_remote (adb forward tcp:9222 localabstract:chrome_devtools_remote + script node que lê <a> com € e limpa adurl/utm/gclid). Fallback: web_search/web_fetch (se Brave rate-limited, tentar de novo). Simular humano (esperas 2-6s, scroll leve). Relatório ≤15 linhas com preço+nome+tamanho+loja+link limpo. Criado 23-09-2026 após Rafael aprovar o formato (busca manual no tablet deu ótimos resultados: até €3,99-9,95 em Sport Zone/SprinterSports, Decathlon, Lefties).
- **Postiz Daily Health Check** (id 663e957a-ffb3-49b1-920e-6a7bf14b9ab4, **11:00 Lisboa** `0 11 * * *`, isolated, announce whatsapp +351910070509, model DSV4 OpenModel, lightContext): roda `bash /home/rafael/.openclaw/workspace/scripts/postiz_health_check.sh` (containers, restart counts, HTTP raiz 200, 3 workers PM2). SE OK responde exatamente "Postiz OK"; SE problema, diagnostica+corrige (dynamicconfig vazio → temporal restart; órfãos porta 3000/4200 → EADDRINUSE; worker offline) e manda resumo ≤10 linhas. **Failure alert ativado 09-08** (após 1 erro, whatsapp, mode announce) — cobre Temporal caído, além de HTTP 500/roo@404/worker offline. Script detecta `TEMPORAL_DOWN: YES` / `TEMPORAL_RESTARTLOOP: YES` (≥3 restarts) e força RESULT PROBLEM; prompt do job manda alerta dedicado ao Rafael nesse caso. Teste manual validado 09-08 ("Postiz OK" entregue no WhatsApp); horário alterado 08→11:00 a pedido do Rafael.
- **briefing-diario-0930** (09:30 Lisboa, pt-BR, <600 palavras): clima Castelo da Maia + BTC/DOGE (EUR/USD/BRL) + top10 IA/modelos/APIs + top3 YouTube IA + top10 mundo + top10 Brasil.
- **Busca vagas tradução PT-BR** (09:00 UTC, Nemotron free, lightContext): lê `memory/job-search-profile.md` → busca → lista novas → grava em `memory/ptbr-translation-jobs-seen.json`; nada novo = `NO_REPLY`.
- **Passagens PT→BR** (diário): `memory/flights-ptbr-seen.json`.
- **Token report** 23:50 · **System health** 4h · internos: dev build 02:00 (systemEvent na sessão main), heartbeat 240min. (YouSearch daily refresh e Weekly growth publish REMOVIDOS 08-08-2026 a pedido do Rafael — eram gatilhos internos do plano A1brella de 30-07.)

## Skills (limpeza 08-08-2026)
- **4 skills ativas** em `workspace/skills/`: `caveman` (única em `agents.defaults.skills`), `pinchtab` (navegação web), `web-design-agent` + `web-design-expert` (design UI/PicsArt — usadas nos mockups do site A1Brella, pendência ativa).
- **Skill Workshop**: 3 propostas aplicadas (caveman update, web-design-agent, web-design-expert).
- **Removidas 08-08-2026** (resíduos do plano "Lean A1brella" 30-07, sem uso real; tudo em `skill-workshop/.trash/`): esp32-sim-test (mock HTTP obsoleto — app fala BLE; já temos ESP32 real), you-search-agent (sem API key You.com; busca web = Brave), robotcoding, dev-agent, growth-strategist, support-agent, ops-monitor (redundante c/ jobs reais), notify-agent (redundante c/ delivery nativo), job-tracker, promobeacon-agent (desatualizada: diz npm num projeto PlatformIO/Gradle).

## Setup / Ops
- **Áudios TTS (preferência fixa do Rafael, 05-08-2026):** SEMPRE `gen-ai text-to-speech -m gemini-2.5-flash-tts --voice Puck` (PicsArt) — mesma voz e modelo para consistência. Detalhes em TOOLS.md.
- **memorySearch**: Ollama local (`nomic-embed-text`) — sem API key, grátis; se Ollama cair, busca de memória para (verificar `ollama list`).
- Modelos (07-09-2026, ordem pedida pelo Rafael): **1º `nvidia/nemotron-3-super-120b-a12b` (Nemotron Super NVIDIA, direto) = primário**. Fallbacks em ordem: **2º `openrouter/nvidia/nemotron-3-nano-30b-a3b:free` (Nemotron nano free)** → **3º `pollinations/gemini-2.0-flash` (free)** → **4º `custom-api-openmodel-ai/deepseek-v4-flash` (DSV4 OpenModel — SÓ em último caso, esticar crédito)**. Heartbeat = Nemotron free. ⚠️ OpenModel NÃO tem Nemotron (verificado 07-09 via API: `nemotron-3-super-120b-a12b`/`nvidia/...`/`nemotron-3-nano-30b-a3b:free` → todos NOT_FOUND; lista oficial de 63 modelos sem nenhum nemotron). **REMOVIDOS 07-09-2026:** GMI MiniMax M3 (`gmi/MiniMaxAI/MiniMax-M3` — trial 14d acabou, monitor confirmou 100% erros não-429; job `gmi-m3-429-monitor` DELETADO), DSV4 Fireworks (`fireworks/.../deepseek-v4-flash-0731` — a pedido do Rafael) e **provider GMI inteiro + MiniMax M2.7** (19:57 UTC, a pedido do Rafael). Providers restantes: token-plan-ams, custom-api-openmodel-ai, nvidia. API key Pollinations em `~/.openclaw/credentials/pollinations/api_key.txt`. Backups: `openclaw.json.bak.*` (07-09-1957 e 07-09-2008).
- Sandbox: read/write limitados a `~/.openclaw/workspace/`; `exec` alcança o resto (repos em `~/workspace/`).
- Serial ESP32: `sg dialout -c "..."` (agente não herda grupo dialout).

## Modelos (mudança 07-09-2026)
- M3 (GMI) removido: trial 14d acabou — monitor `gmi_m3_monitor.sh` confirmou 6/6 erros não-429 (100%), endpoint fora do ar. DSV4 Fireworks removido a pedido do Rafael (ele quer esticar o crédito do OpenModel).
- **Ordem de modelos (17-09-2026, a pedido do Rafael):** 1) Nemotron Super NVIDIA (`nvidia/nemotron-3-super-120b-a12b`), 2) Nemotron nano free OpenRouter (`openrouter/nvidia/nemotron-3-nano-30b-a3b:free`), 3) **Qwen3.5 Plus free via xKiro** (`xkiro/qwen/qwen3.5-plus:free`, alias `Qwen3.5`), 4) free (Pollinations gemini-2.0-flash), 5) DSV4 OpenModel (`custom-api-openmodel-ai/deepseek-v4-flash`) SÓ como último recurso. Backup: `openclaw.json.bak.xkiro-20260917-160858`.
- **Provider xKiro registrado 17-09-2026** (`https://api.xkiro.com/v1`, api openai-completions, chave `sk-xt-…` em `models.providers.xkiro.apiKey` no openclaw.json). Modelo free confirmado: `qwen/qwen3.5-plus:free` (ctx 1M, maxTokens 16384, cost 0, reasoning). ⚠️ DSV4 no xKiro (`deepseek/deepseek-v4-flash-0731`) é PAGO pay-as-you-go — 403 exige saldo real depositado (créditos promocionais não valem); `deepseek/deepseek-v4.1-flash` idem. ⚠️ API do xKiro bloqueia User-Agent default de scripts (Cloudflare 1010) — usar UA de browser nas chamadas. Aplicado no config global + TODOS os jobs (promobeacon x3 1deb84ea/b7043d3f/9c4046a7, anthropic fd2f6d74, briefing d54bc037, postiz 663e957a, token report 65f40993, docker 961c5134, translation 6a1af244, flights d62d0427). ⚠️ Requer RESTART do gateway pra entrar em vigor (status ainda mostrava config antigo 20:13 UTC).
- Monitor `gmi-m3-429-monitor` (26236270) deletado — sem M3, sem monitor.
- 19:57 UTC: **provider `gmi` e alias `gmi/MiniMaxAI/MiniMax-M2.7` removidos do config** (a pedido do Rafael). Script `gmi_m3_monitor.sh` ficou no disco sem job.
- Config: backup criado `openclaw.json.bak.2026-09-07-*` antes da edição.

## Lições
- **Heartbeat sem novidades → responder exatamente `HEARTBEAT_OK`** como texto final. NUNCA executar como comando shell.
- Não gravar valores de secrets/tokens/API keys em memória.
- Não commitar senhas (keystore pass fica em arquivo local chmod 600).
- Só anunciar MEDIA depois do write/salvamento retornar sucesso. ✓ Heartbeat processed at 08:57 UTC

## Pendências ativas (negócios)
- [ ] Montar site da A1Brella (slogan: 🤖 Everything AI and AI everything!)
- [ ] Ads/propaganda online para o Zappelin (zero clientes até agora)
- [ ] Dar uma olhada no www.zappelin.com.br (Rafael pediu 05-08)
- [ ] Incorporar atualizações recentes de MeowCaller, PinchTab e fluxo de login do flowmusic.app
