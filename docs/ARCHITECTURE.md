# ARCHITECTURE.md

> Como o **PlantaOS** está construído, de cima a baixo.

---

## 1. Visão geral

```
                          ┌────────────────────────────┐
                          │  www.plantarockinrio.com   │
                          │  (Vercel · Next.js 14 SPA) │
                          └──────────────┬─────────────┘
                                         │ HTTPS + WSS
                                         ▼
                          ┌────────────────────────────┐
                          │  api.plantarockinrio.com   │
                          │  (Railway · FastAPI 3.11)  │
                          ├────────────────────────────┤
                          │  · REST sob /api/v1/*      │
                          │  · WebSocket /ws/sensors   │
                          │  · SSE /sse/sensors        │
                          │  · MQTT broker (TLS)       │
                          └──┬────────┬──────────┬─────┘
                             │        │          │
                  ┌──────────▼──┐  ┌──▼──┐  ┌────▼─────┐
                  │ PostgreSQL  │  │Redis│  │ Mosquitto│
                  │ (Railway)   │  │     │  │  MQTT    │
                  └─────────────┘  └─────┘  └────┬─────┘
                                                 │
                                  ┌──────────────▼───────────────┐
                                  │  Parque Tejo (Junho 2026)    │
                                  │  62 dispositivos físicos     │
                                  └──────────────────────────────┘
```

---

## 2. Frontend (Vercel)

**Pasta**: `~/planta_rock4/frontend/`

### Framework
- **Next.js 14.2.3** · App Router (server + client components)
- **React 18** + **TypeScript** strict
- Sem Tailwind. Apenas `frontend/app/v2/v2.css` global com variáveis CSS.

### Estrutura
```
frontend/
├── app/
│   ├── layout.tsx              # root (favicon, metadata)
│   ├── v2/
│   │   ├── layout.tsx          # TopBar + PlantaSearchBar
│   │   ├── v2.css              # design system global
│   │   ├── page.tsx            # Home — hero editorial + 8 clusters live
│   │   ├── chat/page.tsx       # Chat com histórico localStorage
│   │   ├── twin/page.tsx       # 3D twin (Three.js CDN)
│   │   ├── sensors/page.tsx    # malha de 62 dispositivos
│   │   ├── scor/page.tsx       # KPIs SCOR ao segundo
│   │   ├── cleaning/page.tsx   # calendário preditivo + 8 staff
│   │   ├── shows/page.tsx
│   │   ├── operations/page.tsx
│   │   ├── incidents/page.tsx
│   │   └── pipelines/page.tsx
├── components/v2/
│   ├── TopBar.tsx              # hamburger veggie + drawer slide-in
│   ├── PlantaSearchBar.tsx     # botão verde → /v2/chat?q=
│   ├── ClusterCard.tsx
│   └── Sparkline.tsx
└── public/
    ├── favicon.svg
    └── planta-logo.svg
```

### Fontes
```css
@import url('https://rsms.me/inter/inter.css');
/* DM Mono via next/font/google em layout.tsx */
```

### Conexão ao backend
```ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE
                 || 'https://api.plantarockinrio.com';
```

CORS no backend está restrito a:
- `https://www.plantarockinrio.com`
- `https://plantarockinrio.com`
- `https://plantarockinrio.vercel.app`

---

## 3. Backend (Railway)

**Pasta**: `~/planta_rock4/app/`

### Framework
- **FastAPI** (Python 3.11)
- **SQLAlchemy** async com `asyncpg`
- **Pydantic v2** para validação
- **Uvicorn** com workers

### Estrutura
```
app/
├── main.py                     # FastAPI app + CORS + lifespan
├── api/
│   ├── v1/
│   │   ├── health.py
│   │   ├── state.py
│   │   ├── clusters.py
│   │   ├── kpis.py
│   │   ├── sensors.py
│   │   ├── shows.py
│   │   ├── alerts.py
│   │   ├── tv.py
│   │   ├── chat.py              # Gemini 2.5 Flash
│   │   ├── route.py
│   │   ├── prosegur.py
│   │   ├── simulate.py
│   │   ├── scor.py              # /scor/overview, /dry-run
│   │   ├── gateways.py
│   │   └── sections.py
│   └── ws/
│       └── sensors.py           # WebSocket hub
├── services/
│   ├── cluster_telemetry.py    # gera payload SCOR-compatible
│   ├── cleaning_staff.py       # 8 pessoas PT
│   └── cleaning_predictive.py  # calendário 24h round-robin
├── workers/
│   ├── mqtt_ingestor.py        # consume MQTT → Redis
│   └── scor_adapter.py         # push aos KPIs SCOR
└── persistence/
    ├── postgres.py
    └── redis.py
```

### LLM
```bash
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=...
```
Fallback obrigatório: se Gemini falhar em 3s, devolve resposta template. O
chat **nunca** inventa dados ao vivo.

### Comandos comuns
```bash
railway logs                     # tail
railway logs --service planta_rock4
railway variables                # ver env
railway up                       # deploy manual
railway run python -c "..."     # one-off com env do prod
```

---

## 4. Real-time strategy (3 camadas)

Para garantir UX fluido em qualquer condição de rede:

```
[Cliente] ── tenta WebSocket ── 5s timeout ──┐
                │                            │
                │ OK                         │ Falha
                ▼                            ▼
       [Streaming WS]                ── tenta SSE ── 5s timeout ──┐
       ping a cada 30s                       │                    │
                                             │ OK                 │ Falha
                                             ▼                    ▼
                                    [Streaming SSE]         [Polling 5s]
                                    chunks event/data       since=ts
```

**Reconexão**:
- Backoff exponencial 3 tentativas no nível actual.
- Esgotado → cai para o nível abaixo.
- Polling tenta upgrade para WS a cada 60s.

**Store local único** (Zustand/useState):
- As 3 camadas escrevem todas no mesmo store.
- A UI não sabe qual está activa — só vê dados frescos + `connection` state.

---

## 5. Fusão sensorial

Para cada cluster WC, ocupação é calculada por:

```
ocupacao = Σ obs_i × peso_i × disp_i / Σ peso_i × disp_i
```

Pesos:
| Tipo | Peso | Notas |
|---|---|---|
| IR ESP32 | **0.50** | sensor primário |
| WiFi 6E aggregate | **0.30** | anónimo, sem MAC |
| Câmara OAK-D | **0.20** | edge ML, sem rosto |

Se um sensor está `offline`, o seu peso é **redistribuído** entre os
restantes do mesmo cluster.

Se um cluster perde **>60%** do peso disponível, observação fica
`low_confidence` e a UI mostra-o em amber.

**Regras invioláveis**:
- Nunca dividir por zero.
- Nunca extrapolar sem dados.
- Sempre mostrar confiança ao utilizador.

---

## 6. Redundância

| Camada | Primário | Failover 1 | Failover 2 |
|---|---|---|---|
| Sensor de pessoas | IR | WiFi aggregate | Câmara |
| Gateway → backend | LoRaWAN (GW-N ou GW-S) | WiFi via AP local | Cellular directo |
| Edge → cloud | 4G NOS | 4G Vodafone | Ethernet venue |
| Edge compute | RPi 5 EDGE-1 | RPi 5 EDGE-2 hot standby | — |
| Transporte cliente | WebSocket | SSE | Polling 5s |
| Cache | Redis (Railway) | Postgres (source of truth) | — |

---

## 7. Comandos e infra de deploy

### Vercel (frontend)
- Project: `iamgoncalos-projects/planta-rock4`
- Branch: `main`
- Build: `next build`
- Domain: `www.plantarockinrio.com` + alias `plantarockinrio.com`
- Build cache: restaurado automaticamente entre deploys

### Railway (backend)
- Project: `genuine-imagination` (id `b29c7a30-7384-405d-b4d5-2ec6073b7fda`)
- Service: `planta_rock4` (id `5f2d3ef8-cbc4-4900-be18-23f43e4a00f7`)
- Nixpacks build (Python 3.11)
- Healthcheck: `GET /api/v1/health`

### Custom domains
- `api.plantarockinrio.com` aponta para Railway service
- `www.plantarockinrio.com` aponta para Vercel

---

## 8. Observabilidade (mínimo viável)

- **Request ID**: UUID em todos os logs HTTP.
- **WS seq**: incremental por conexão para detectar gaps.
- **Métricas Prometheus** em `/metrics` (a implementar):
  - `sensor_updates_total`
  - `ws_connections_active`
  - `insight_engine_duration_seconds`
  - `mqtt_messages_received_total`
  - `scor_adapter_lag_seconds`
- **Logs estruturados** JSON com `service`, `route`, `latency_ms`, `status_code`.

---

## 9. Segurança

- Toda a API atrás de **JWT bearer** (excepto `/health` e `/ready`).
- WebSocket autenticado no handshake (`Sec-WebSocket-Protocol: bearer.<jwt>`).
- Rate limit nginx/Railway: 100 req/min REST, 1 WS por sessão.
- Inputs validados com Pydantic v2.
- Comandos hardware (restart, calibrate) requerem role `ops` no JWT.
- Leitura requer apenas `viewer`.
