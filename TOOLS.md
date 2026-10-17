# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup: camera names and locations, SSH hosts and aliases, preferred TTS voices, speaker/room names, device nicknames, anything environment-specific.

## Coding / media CLIs (contas Pro do Rafael — homelab666)

- **Antigravity CLI (Google coding agent)** → binário `agy` em `~/.local/bin/agy` (v1.1.10). OAuth do Google já logado (`~/.gemini/antigravity-cli/antigravity-oauth-token`). Modelo: Gemini 3.1 Pro. Uso: `agy --model ... --dangerously-skip-permissions "<tarefa>"` (ou interactive). Workspaces confiáveis: `/home/rafael`.
- **GitHub CLI** → `gh` (v2.97) logado como **rafaelrogel** (scopes: repo, workflow, admin:org, copilot, etc.). Usar p/ push/pull/clone/issues/repos.
- **PicsArt AI CLI** → `gen-ai` (v2.54.2, npm global, @picsart/gen-ai) logado com **386 créditos**. Imagem/vídeo/áudio (t2a, tts, music, sfx), edit, enhance, describe, batch. Skills em `~/.agents/skills/picsart-api/` e `~/.openclaw/skills/picsart-api/`. Atualização disponível: 2.55.1 (`gen-ai update`).
  - **TTS padrão (fixo, por pedido do Rafael):** `gen-ai text-to-speech -m gemini-2.5-flash-tts --voice Puck --container mp3 -p "<texto>"` — SEMPRE esta voz/modelo p/ consistência. Exige `-m` (sem ele: "Model is required"). `openai-tts-1` → erro 404 (workflow não encontrado); vozes `*_uranus_bigtts` são de outro modelo e não funcionam com gemini tts. Saída vem em `.wav` na pasta `output/`; converter p/ mp3: `ffmpeg -i <f>.wav -codec:a libmp3lame -qscale:a 5 <f>.mp3`.
- **PlatformIO + esptool** → `pio_venv/bin/pio` (v6.1.19) + `esptool.py` (embarcado ESP32).
- **MeowCaller (chamadas WhatsApp)**: SEMPRE usar `meowcaller-notify-async -store ~/.openclaw/credentials/whatsapp-calls/rafael/wa-voip.db <numero> <audio-16k.wav>` — wrapper que roda em BACKGROUND para NÃO travar a lane da conversa (lição 06-08: chamada síncrona de 90s travava a sessão WhatsApp em `active_reply_work`). Resultado vai para `memory/meowcaller-results.log`; reportar na conversa quando terminar. Forma direta (`meowcaller notify`) só em casos onde segurar o turno é aceitável.
  - **STORE PADRÃO = rafael** (pareado no número do Rafael +351910070509, device `351910070509:74`, 18:54 06-08) — ligações saem do número dele. Store antigo do a1 (`whatsapp-calls/a1/wa-voip.db`, +351913186919) causava conflito: 2 conexões no mesmo device derrubavam o canal (status 428) e travavam a lane — NÃO usar mais.

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)
