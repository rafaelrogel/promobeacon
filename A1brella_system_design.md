# Sistema Lean “A1brella AI‑Native” – Guia de Arquitetura

## Visão
Rodar a A1brella como empresa **1ª geração AI‑Native** com **zero funcionários**, só você e seu irmão. Toda a operação (dev, marketing, suporte, pesquisa) será automatizada por **agentes OpenClaw** que chamam a **API da You.com**.

## Blocos Principais

| Bloco | Função | Como se conecta |
|-------|--------|-----------------|
| **Agent‑Core** | Motor de orquestração | `cron` (heartbeat 240 min) → dispara jobs |
| **Skill‑YouSearch** | Envolve a API da You.com (search, chat, embed) | Wrapper Python/Node criado via *Skill Workshop* |
| **Skill‑Dev** | Gera código, documenta APIs, cria testes | Usa modelo “code” da You.com ou modelos locales |
| **Skill‑Growth** | Cria posts, analisa métricas, otimiza SEO | Usa modelo “creative” da You.com |
| **Skill‑Support** | Responde clientes via WhatsApp, FAQ | Usa modelo “assistant” da You.com |
| **Ops‑Monitor** | Acompanha custo de tokens, health‑checks | Cron + dashboards (Grafana) |

## Fluxo de Trabalho (Passo‑a‑Passo)

1. **Criar Goal**  
   ```text
   /create_goal {"objective":"Lean A1brella AI‑Native","token_budget:150000}
   ```

2. **Criar Skills** (via *Skill Workshop*)  
   - `you-search-agent` – wrapper da API You.com (search, chat, embed).  
   - `dev-agent` – gera código e documentação.  
   - `growth-agent` – planeja e publica conteúdo.  
   - `support-agent` – responde WhatsApp e tickets.  
   - `ops-monitor` – verifica uso de tokens e health.

3. **Aplicar Skills**  
   ```text
   /skill_workshop {"action":"apply","proposal_id":"<id‑you‑search>","reason":"Integra API You.com"}
   /skill_workshop {"action":"apply","proposal_id":"<id‑dev>","reason":"Código e testes"}
   /skill_workshop {"action":"apply","proposal_id":"<id‑growth>","reason":"Marketing"}
   /skill_workshop {"action":"apply","proposal_id":"<id‑support>","reason":"Suporte WhatsApp"}
   /skill_workshop {"action":"apply","proposal_id":"<id‑ops>","reason":"Monitoramento"}
   ```

4. **Configurar Cron Jobs**  
   - **Heartbeat 240 min** (já existente) → dispara “check‑progress”.  
   - **Daily YouSearch Sync** – every 8 h → atualiza modelos e verifica quota.  
   - **Nightly Build** – 02:00 UTC → roda `dev‑agent` para gerar/atualizar bibliotecas.  
   - **Weekly Report** –Sunday 10:00 UTC → `growth‑agent` produz resumo de performance.

5. **Persistir Memória** (para histórico)  
   ```text
   /write {"path":"~/openclaw/workspace/memory/2026-07-30_A1B_system.md",
           "content":"[Resumo da arquitetura – 30/07/2026]\n- Goal ID: <id>\n- Skills instaladas: you‑search‑agent, dev‑agent, ...\n- Próximos heartbeat: 31/07 12:00 UTC." }
   ```

6. **Deploy de Agentes**  
   - Cada skill gera um **sub‑agent** isolado (`sessions_spawn`).  
   - Use `attachments` para passar credenciais da API You.com (token guardado em `~/.openclaw/secrets/you_api.key`).  
   - Os sub‑agents executam tarefas em paralelo (ex.: `dev‑agent` cria pacote, `growth‑agent` agenda posts).

7. **Monitoramento & Alertas**  
   - `ops‑monitor` envia evento `systemEvent` se custo > $10/dia ou latência > 200 ms.  
   - Configurar alerta via webhook para Telegram/WhatsApp.

## Opções de Arquitetura (Prós / Contras)

| Opção | Descrição | Prós | Contras |
|-------|-----------|------|----------|
| **A – Full‑You.com** | Todas as habilidades usam a API da You.com (search, chat, embed). | Simples de licenciar (vocês já têm token). | Dependência de taxa de uso; limites de ritmo. |
| **B – Hybrid (You.com + Open‑Source Models)** | Usa You.com para pesquisa/geração, mas modelos locais (ex.: Mistral, Llama) para código e design. | Maior controle, custo previsível. | Mais esforço de manutenção (infra local). |
| **C – Multi‑Provider** | Alterna entre You.com, OpenRouter, HuggingFace según disponibilidade. | Redundância, custo otimizado. | Complexidade de routing e credenciamento. |

**Recomendação inicial:** Opção **A** – iniciar só com You.com, porque vocês já possuem token registrado e a API cobre as necessidades de pesquisa, geração de texto e código. Depois avaliar para **B** quando o volume crescer.

## Checklist de Primeira Configuração

- [ ] Criar Goal e sub‑goals.  
- [ ] Gerar skills via *Skill Workshop* (YouSearch, Dev, Growth, Support, Ops).  
- [ ] Aplicar cada skill (`apply` com `proposal_id`).  
- [ ] Configurar cron jobs (heartbeat, daily sync, nightly build).  
- [ ] Persistir memória com resumo da arquitetura.  
- [ ] Testar sub‑agents (`sessions_spawn` + `sessions_yield`).  
- [ ] Verificar alertas de custo e health.  

## Próximos Passos (Heartbeat)

- **31/07 12:00 UTC** – heartbeat disparará a verificação de “All skills applied & running?”.  
- **Após** – ajustar cron se alguma skill ficar “blocked”.  

*Qualquer dúvida ou ponto a detalhar, basta dizer “ask” ou “add” e continuamos.*