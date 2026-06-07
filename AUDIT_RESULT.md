# AUDIT_RESULT.md — PlantaOS · Rock in Rio Lisboa 2026
**Gerado:** 8 Junho 2026 · **Fase 1 — só leitura, 4 agentes em paralelo**

---

## A. AUDITORIA BACKEND

### A1. Rotas Duplicadas / Sobrepostas

- **`/kpis` duplicado:** `kpis.py` → `GET /api/v1/kpis` e `sections.py` → `GET /v1/kpis` — dois endpoints com comportamento idêntico, prefixos diferentes, confusão de contrato.
- **Payload `LivePayload` duplicado:** `state.py` → `GET /api/v1/state` e `sections.py` → `GET /v1/sections` devolvem ambos o mesmo payload completo.
- **`/alerts` e `/alerts/smart` com semântica sobreposta:** `alerts.py` serve alertas de `_ALERTS` em memória; `intelligence.py` serve alertas calculados. Dois routers para o mesmo propósito.
- **`/scor` partido em dois routers** (`scor.py` e `scor_observability.py`) que partilham prefixo `/api/v1/scor` sem coordenação.

### A2. Endpoints Pesados sem Cache

- **`get_live_payload()` chamado a nu em 10+ routers** (state, sections, kpis, clusters, routing, chat, forecast, scor, screen, tv) — cada pedido executa `simulate_tick()` (14 secções, cálculo probabilístico) + loop `get_fused()`. Sem cache entre chamadas.
- **`get_alerts()` chama `simulate_tick()` independentemente** — uma chamada a `/alerts` faz 2 simulate_tick se combinada com polling de estado.
- **`GET /api/v1/flow`** chama `_feed_engine()` por pedido sem cache — O(8 clusters × simulate).
- **`GET /api/v1/fusion` (all)** — 8 chamadas sequenciais a `fusion_cluster()` por pedido.
- **WebSocket `/api/v1/ws`** chama `get_live_payload()` + `get_flow_snapshot()` a cada 5 s **por cliente conectado** — N clientes = N×2 chamadas pesadas simultâneas.
- **Excepção positiva:** `GET /api/v1/telemetry/clusters/now` tem `_SNAP_CACHE` de 5 s bem implementado.

### A3. Estado em Memória — Risco Restart / Multi-Worker

| Variável | Ficheiro | Impacto |
|---|---|---|
| `CURRENT_SCENARIO`, `TICK`, `LIVE_DATA`, `_IR_STORE`, `_WIFI_STORE`, `_CAMERA_STORE`, `_ALERTS` | `services/state.py` | Cenário activo e dados ingested perdem-se no restart |
| `_STATE`, `_RESULTS` | `app/fusion.py` | Drift IR e resultados de fusão perdem-se; primeiros pedidos pós-restart voltam a `stale` |
| `_STORE` | `services/ingest_store.py` | Dados reais ingested perdem-se |
| `_HORA_OVERRIDE` | `services/fleet_sim.py` | Override de hora demo ignorado noutro worker |
| `_SNAP_CACHE` | `routers/telemetry.py` | Cache duplicado por worker sem coordenação |
| `_FLOW_ENGINE` | `services/flow.py` | Engine de fluxo e derivações IR reiniciam por worker |

**Em Railway multi-worker:** POST `/ingest` pode ir para um worker diferente do GET `/telemetry/clusters/now` — os dados nunca se encontram.

### A4. Onde Ligar o `copy_engine.py`

- **Já está ligado** em `routers/screen.py` (`GET /api/v1/screen/copy`) via `_state_to_clusters()` → `build_copy()`. **Correcto.**
- **Optimização recomendada:** emitir `{"type": "copy_update", "data": build_copy(...)}` no WebSocket (`main.py`) a cada ciclo de 5 s, reutilizando o payload já calculado — elimina polling do frontend.

### A5. Bugs Críticos Encontrados

- **`fuse_cluster` não existe:** `routers/fusion.py` chama `fusion_engine.fuse_cluster()` mas `services/fusion.py` só tem `fuse()`. Qualquer pedido a `GET /api/v1/fusion/{cluster_id}` falha silenciosamente (try/except esconde o `AttributeError`). **Fusão do router está quebrada.**
- **`_IR_STORE`, `_WIFI_STORE`, `_CAMERA_STORE` em `state.py` são dead code** — escritos por `ingest_ir/wifi/camera()` mas nunca lidos por `get_live_payload()`.
- **`get_alerts()` gera IDs `auto_{section_id}_{int(now)}` em cada chamada** — sem dedup adequado, lista cresce sem bound.
- **`routers/fleet.py` `_MODE` alterado por POST sem lock** — em multi-worker, modo sim/real pode diferir entre workers.

---

## B. AUDITORIA FRONTEND

### B1. Scroll

- **`/v2/screen`** — CORRECTO. `position: fixed; inset: 0; overflow: hidden`. Injecta overrides `!important` no layout pai — funciona mas é frágil.
- **`/wc01–wc08`** — CORRECTO. `height: 100vh + overflow: hidden`. Usam `100vh` em vez de `100dvh` — risco de corte ~75px em iOS Safari com barra de endereço visível.
- **`/v2/sensors`** — tem scroll **intencional** (página de gestão operacional, não mural público). `min-height: calc(100vh - 72px)`. Aceitável para uso staff.

### B2. Vermelho Proibido

- **LIMPO** — nenhum `#ff0000`, `#f00`, `color: red` em código de produto. Cor crítica `#C25A1A` usada correctamente em todos os alertas e badges.

### B3. "SIMULADO" Visível — PROBLEMA CONFIRMADO

Ficheiros que expõem a palavra "SIMULADO" ao utilizador:
- `app/app/page.tsx` — badge "SIMULADO" quando `route.any_simulated` (**potencialmente público**)
- `app/dashboard/page.tsx` — badge "SIMULADO" quando `anySimulated` (**potencialmente público**)
- `app/tv/[screen_id]/page.tsx` — exibe "SIMULADO" em ecrão TV (**ecrão público do festival**)
- `app/sensors/page.tsx` — rota legada `/sensors` exibe "SIMULADO" (não `/v2/sensors`)
- `app/v2/sensors/page.tsx` — "simulados (demo)" em KPIs e badges `◌ SIMULADO` (contexto staff — risco menor)
- `app/v2/scor/page.tsx` — badges "SIMULADO" em clusters
- `components/SimuladoBadge.tsx` + `SectionBar.tsx` — componente reutilizável que espalha o label

**Prioridade alta:** `tv/[screen_id]` e `app/page.tsx` são os mais críticos (públicos durante o festival).

### B4. Layout / Padding

- `v2.css` — `.page` com `min-height: 100vh` pode criar scroll em páginas leves.
- `v2.css` — `min-height: calc(100vh - var(--header-h) - var(--searchbar-h) - 36px)` idem.

---

## C. AUDITORIA SEGURANÇA

### C1. CRÍTICO

- **`app/config.py:33` — `mqtt_password: str = "planta2026mqtt"` hardcoded** no source. Password do broker MQTT com TLS exposta em qualquer instalação sem a env var definida.
- **`app/routers/rirstaff.py:218` — `_ADMIN_PASS = os.getenv("RIRSTAFF_ADMIN_PASS", "planta2026")`** — fallback hardcoded. Qualquer atacante que descubra o endpoint altera a calibração dos sensores.
- **`app/rirstaff_chat.py:21` — `GEMINI_KEY = os.getenv("GEMINI_RIRSTAFF_KEY", "POE_A_TUA_KEY_AQUI")`** — placeholder visível; módulo arrancaria com key inválida sem falhar.

### C2. ALTO

- **`/api/v1/ingest` sem autenticação efectiva** — `_check_auth()` em `ingest.py:55-56`: se `OPS_SECRET` não estiver definida ou for `"change-me"`, **qualquer pedido POST é aceite sem token**. Injecção de dados falsos em todos os 8 clusters.
- **`/api/v1/ingest_staff/{cluster}` sem validação robusta** — `rirstaff.py:138-154`: token só bloqueia se env var definida; sem token, aceita qualquer cluster incluindo IDs arbitrários.
- **`PLANTA_OPS_KEY` ausente = modo aberto total** — `app/core/auth.py:36-39`: sem a env var, aceita qualquer pedido de escrita (sensores, limpeza, incidentes, staff).
- **Múltiplos endpoints POST sem autenticação:** `/simulate/tick`, `/flow/tick`, `/flow/reanchor`, `/scor/dry-run`, `/devices/cmd`, `/devices/ota`, `/sensor_cmd/{id}/cmd`, `/fleet/mode`, `/intelligence/counterfactual`, `/intelligence/demo/hour`.
- **CORS com `allow_credentials=True` + regex ampla** — `main.py:127-128`: `r"https://planta-rock4-.*\.vercel\.app"` aceita qualquer subdomínio Vercel com esse prefixo. CSRF potencial.

### C3. MÉDIO

- **`database_url` com username de sistema** (`postgresql+asyncpg://goncalomelodemagalhaes@localhost/plantaos`) hardcoded em `config.py:27`.
- **`IngestParams` com `extra = "allow"`** — aceita campos arbitrários não declarados; dados inesperados ficam em `ingest_store`.
- **Password admin enviada em body JSON** em vez de header Authorization — fica em logs Railway.
- **`/rirstaff/{cluster}/reset` e `/capacidade` sem autenticação.**

### C4. BAIXO

- `chat.py:404` — `gemini_debug_state()` inclui primeiros 10 chars da API key (não exposto publicamente por agora).
- `.env.local` existe no disco mas não está no git — correcto, mas confirmar.

---

## D. ESTADO EM MEMÓRIA — PROPOSTA REDIS

**Redis NÃO está no stack** (`requirements.txt` não tem `redis`). É necessário instalá-lo antes de qualquer migração.

### Migrar para Redis (por prioridade):

1. **`ingest_store._STORE`** → Redis Hash `ingest:store` (campo = cluster_id, TTL = 30 s). Impacto imediato: dados de sensores sobrevivem a restart.
2. **`fusion._RESULTS` + `fusion._STATE`** → Redis Hash `fusion:results` e `fusion:state` (TTL 60 s / 120 s). Co-dependentes, migrar em conjunto.
3. **`sensor:ir/wifi/cam stores`** (`state.py`) → Redis Hashes separados, TTL 30 s. (Nota: actualmente são dead code — resolver esse bug primeiro.)
4. **`snap:telemetry`** (`_SNAP_CACHE`) → Redis String TTL 5 s. Opcional mas útil em multi-worker.

### NÃO migrar:

- `_ALERTS` — lógica stateful complexa, adiar para fase 2.
- `CURRENT_SCENARIO`, `TICK`, `LIVE_DATA`, `_TICK_TS` — variáveis de simulação efémeras, sem valor em produção.
- `_SHOWS` — configuração estática imutável.

### Ordem de implementação:
(a) `requirements.txt` + `REDIS_URL` no Railway → (b) `app/core/redis_client.py` singleton → (c) `ingest_store` → (d) `fusion._RESULTS`+`_STATE` → (e) sensor stores.

---

## RESUMO EXECUTIVO — PRIORIDADES

| # | Item | Gravidade | Fase |
|---|---|---|---|
| 1 | Segredos hardcoded (mqtt_password, admin pass, copy fallbacks) | CRÍTICO | Fase 2.2 |
| 2 | `/ingest` sem token efectivo — injecção de dados possível | CRÍTICO | Fase 2.2 |
| 3 | Múltiplos POST endpoints sem auth (devices, simulate, flow) | ALTO | Fase 2.2 |
| 4 | "SIMULADO" visível em ecrã TV e página pública | ALTO | Fase 2.4 |
| 5 | `copy_engine` já ligado, sem issues | OK (verificar) | Fase 2.1 |
| 6 | `fuse_cluster` não existe em router de fusão — bug silencioso | ALTO | Fase 2.3 |
| 7 | `get_live_payload()` sem cache em 10+ routers | ALTO | Fase 2.3 |
| 8 | Redis não instalado — estado perde-se no restart | MÉDIO | Fase 2.5 |
| 9 | CORS regex ampla + allow_credentials | MÉDIO | Fase 2.2 |
| 10 | wc01-wc08 usam 100vh em vez de 100dvh | BAIXO | Fase 2.4 |

**Bottom line:** O motor de fusão é sólido. Os riscos críticos antes de 11 Junho são: (1) definir todas as env vars de segredos no Railway e remover fallbacks permissivos; (2) adicionar token obrigatório ao `/ingest`; (3) suprimir "SIMULADO" do ecrã TV público.
