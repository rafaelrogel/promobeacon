# Investigação: MeowCaller trava o WhatsApp — 06-08-2026

## Veredito: CONFIRMADO — toda chamada MeowCaller deixa a sessão WhatsApp do Rafael em estado stale (trava)

## Causa raiz
- **O meowcaller usa o MESMO device/número do canal WhatsApp**: store `wa-voip.db` está pareado como **`351913186919:4@s.whatsapp.net`** — exatamente o mesmo número/device do canal a1 do OpenClaw.
- Quando o meowcaller faz uma chamada, ele abre UMA SEGUNDA conexão ativa no mesmo device → o servidor do WhatsApp derruba a conexão do canal ou gera conflito:
  - Evidência: `[whatsapp] Web connection closed (status 428). Retry 1/12` às **17:21:29** (durante janela de chamadas)
- Resultado no runtime: o run da sessão `agent:main:whatsapp:direct:+351910070509` fica `stale_session_state` (`lastProgress=run:completed` mas `terminalProgressStale=true`), o embedded run nunca é liberado (`active_reply_work`), o recovery tenta `abort_embedded_run` mas `aborted=false drained=false released=0` → loop infinito de `status=skipped reason=active_reply_work`, fila acumula (37 → 44 → 45 msgs).

## Linha do tempo
- 17:21:29 — status 428 (canal caiu) → 17:21:38 reconectou
- Chamadas meowcaller: 17:31, 17:43, 18:09, 18:14 (estas 2 últimas via wrapper async, da sessão webchat)
- Stuck recovery em: 17:36, 18:00, 18:16, 18:22 — sempre correlacionado depois de chamadas

## O que resolveu temporariamente
- `openclaw gateway restart` (3x hoje) — limpa estado em memória; WhatsApp reconecta em ~9s
- **Wrapper `meowcaller-notify-async`** (`~/.local/bin/`) — chamada em background não segura mais o turno da conversa (resolve a META do problema, mas o conflito de device continua)

## Solução definitiva (pendente de decisão do Rafael)
1. **Parear o meowcaller num device/número SEPARADO** (ideal: o próprio número do Rafael, ou um segundo WhatsApp/tablet) — assim a chamada não derruba a conexão do canal a1
2. Alternativa: aceitar que toda chamada derruba o canal e fazer auto-restart do gateway após cada chamada (gambiarra)

## Arquivos relevantes
- Documentação do recovery: `dist/diagnostic-stuck-session-recovery.runtime-*.js` — `STUCK_SESSION_PROGRESS_STALE_MS = 5min`, `allowActiveAbort` etc.
- Doc: `docs/concepts/agent-loop.md` §Stuck session diagnostics
