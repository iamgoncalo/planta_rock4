# CLAUDE.md

> Contexto-base do projecto **PlantaOS · Rock in Rio Lisboa 2026**.  
> Este ficheiro é a primeira leitura obrigatória para qualquer agente de IA
> (Claude, Cursor, etc.) ou novo colaborador. Lê **todo** antes de mexer em
> código.

---

## 1. Identidade

| | |
|---|---|
| **Produto** | PlantaOS — recomendador inteligente de WC ao segundo |
| **Cliente** | Rock in Rio Lisboa 2026 · Parque Tejo · 20–28 Junho 2026 |
| **Empresa** | Planta Smart Homes (Planta Design Unipessoal Lda, Porto) |
| **CEO** | Gonçalo Melo de Magalhães · `hi@planta.design` |
| **Repo** | `github.com/iamgoncalo/planta_rock4` (NUNCA `planta_rock3`) |
| **Pasta-fonte** | `~/planta_rock4` |
| **Domínio site** | `https://www.plantarockinrio.com` (Vercel) |
| **Domínio API** | `https://api.plantarockinrio.com` (Railway) |

---

## 2. Para que serve o PlantaOS

**Uma frase**: para cada pessoa no Rock in Rio Lisboa, recomendar o caminho
mais rápido, leve e seguro até uma casa-de-banho disponível, **agora**.

**Como**: combinando 62 dispositivos físicos espalhados pelo Parque Tejo
(sensores IR, APs WiFi agregado, câmaras edge ML, reed switches em portas) com
um motor de fusão sensorial e um sistema de routing inteligente.

**Custo de rota** =
```
walk_time + queue_wait + congestion_penalty
  + show_surge_penalty + low_confidence_penalty + safety_penalty
```

---

## 3. ⛔ Vocabulário PROIBIDO

Os termos seguintes **NUNCA** aparecem em:
- código de produto
- UI / cópias visíveis
- chats com o utilizador
- documentação operacional
- conselhos de deploy

> Termos proibidos: `seed=2026`, `simulation seed`, `F=P/D`,
> `Freedom Index`, `FREE algorithm`, `Distortion`, `FLRP`, `Architecture of
> Freedom Intelligence`, `AFI`, `HORSE CFT`, `Deucalion`, `hypothesis under
> test`.

Estes conceitos académicos vivem **só** em papers/Zenodo separados. No produto
falamos de **pessoas, fluxos, ocupação, filas, recomendações, tempos**.

---

## 4. ⛔ Não-objectivos do produto

- ❌ Não fazemos **tracking individual** (nem MAC, nem rosto, nem ID).
- ❌ Não medimos **CO₂, temperatura, humidade** no produto. WiFi é
  **agregado anónimo**.
- ❌ Não usamos a cor **vermelha** em alertas. Cor crítica única: `#C25A1A`
  (laranja Planta).
- ❌ Não mostramos a label **`SIMULADO`** ao utilizador final em produção
  pública — só em contextos académicos (Zenodo, FCT, papers).
- ❌ Não inventamos dados ao vivo no chat — quando o backend não responde,
  o chat diz isso honestamente.

---

## 5. Stack

### Frontend (Vercel, `~/planta_rock4/frontend`)
- Next.js 14.2.3 · App Router
- React 18 + TypeScript
- Inter sans-serif via `@import 'https://rsms.me/inter/inter.css'`
- Sem framework CSS — só `v2.css` global com variáveis e `clamp(vw)`
- Páginas em `app/v2/*`

### Backend (Railway, `~/planta_rock4/app`)
- FastAPI Python 3.11 (Nixpacks)
- SQLAlchemy async + PostgreSQL
- Redis (cache, pub/sub)
- Mosquitto MQTT (TLS) para ingestão de sensores físicos
- ~28 rotas REST + WebSocket + SSE
- LLM chat: Gemini 2.5 Flash (env `GEMINI_MODEL=gemini-2.5-flash`)

### Infraestrutura física (Parque Tejo, junho 2026)
- 16 sensores IR ESP32+E18-D80NK · LoRaWAN
- 11 APs WiFi 6E (TP-Link EAP670) · PoE
- 5 câmaras Luxonis OAK-D Lite · edge ML
- 2 gateways LoRaWAN (Dragino DLOS8) · norte e sul
- 2 hubs 4G (LilyGo T-SIM7000G) · NOS primário, Vodafone failover
- 2 edge nodes (Raspberry Pi 5) · broker MQTT local
- 24 reed switches MC-38 · GPIO ESP32 LoRaWAN

Detalhe em [`docs/SENSORS.md`](docs/SENSORS.md).

---

## 6. Design system (APROVADO 28 Mai 2026)

**Inspiração**: Oxman editorial — sans-serif gigante, branco, micro-tipografia
mono, sem cromos.

### Tipografia
- **Display + sans**: Inter (rsms.me CDN)
- **Mono**: DM Mono (Google Fonts)
- Sizes em `clamp(min, vw, max)` — fluido

### Paleta
```
--ink:        #0D1A0F   (texto principal)
--muted:      #6B7268
--faint:      #B7B9B0

--green-dark: #1B3A21   (CTA + activo)
--green:      #2E7D4F
--green-pale: #EDF4EF

--amber:      #C25A1A   (alertas — NUNCA vermelho)
--border:     #ECE9E2
--bg-soft:    #FAFAF8
```

### Layout
- **TopBar** fixo 72px com hamburger veggie à direita (mobile <920px)
- **PlantaSearchBar** fixa em baixo, botão verde escuro, submit → `/v2/chat?q=`
- Páginas em `.page` ou `.page-full` com `clamp()` padding

Detalhe em [`docs/DESIGN.md`](docs/DESIGN.md).

---

## 7. Estado do código (Maio 2026)

```
Último deploy:    v16 · ae1dbe7 · 28 Mai 2026
Páginas /v2:      10 (Início, Twin, Sensores, Shows, Operações,
                       Limpeza, Incidentes, SCOR, Pipelines, Chat)
Endpoints API:    ~28 rotas (ver /openapi.json)
Sensores activos: 0 (instalação 11–12 Jun 2026)
```

---

## 8. Regras para alterações

### Sempre
- ✅ Lê o ficheiro **antes** de o editar.
- ✅ Faz `.bak.{versao}.{timestamp}` antes de overwrite.
- ✅ Smoke test em `/tmp` antes de tocar no real.
- ✅ Empacota mudanças em `install_vN.py` numerado.
- ✅ Push pequenos, atómicos, com mensagem de commit clara.
- ✅ Em PT-PT (Portugal). Inglês só para identificadores técnicos.

### Nunca
- ❌ Não imprimir paths absolutos com `/Users/...` em respostas.
- ❌ Não inventar APIs que não existem — confirma com `grep` no código.
- ❌ Não usar Cormorant Garamond serif no v2 (foi substituído por Inter).
- ❌ Não introduzir `BottomNav` — foi removido em v12.
- ❌ Não usar `useSearchParams()` sem `<Suspense>` wrapper (Next.js 14 build
  estático exige).

---

## 9. Comandos essenciais

```bash
# Frontend
cd ~/planta_rock4 && git pull
vercel ls                  # ver deploys
vercel inspect --logs URL  # logs de um deploy específico

# Backend
railway logs               # tail logs Railway
railway variables          # ver env vars
railway up                 # deploy manual

# Curl rápido API
curl https://api.plantarockinrio.com/api/v1/health
curl https://api.plantarockinrio.com/api/v1/telemetry/clusters/now | jq
```

---

## 10. Documentos complementares

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — stack completa, real-time strategy
- [`docs/PRODUCT.md`](docs/PRODUCT.md) — produto, KPIs, 14 secções
- [`docs/SENSORS.md`](docs/SENSORS.md) — 62 dispositivos, fusão, posições
- [`docs/DESIGN.md`](docs/DESIGN.md) — Oxman editorial, Inter, paleta
- [`docs/DEPLOY.md`](docs/DEPLOY.md) — Vercel + Railway + troubleshooting
- [`docs/OPS.md`](docs/OPS.md) — runbook diário Junho 2026

---

## 11. Contactos

| Pessoa | Papel | Email |
|---|---|---|
| Gonçalo Melo de Magalhães | CEO Planta Smart Homes | hi@planta.design |
| Ricardo Acto | COO Rock World | ricardoacto@rockinrio.com |
| Matheus Zanin | Operações Rock World | matheuszanin@rockinrio.com |
| Giullia Kormann | Smart City of Rock | giullia@liquidinnovation.co |
| Egon Barbosa | CEO Liquid Innovation | egon@liquidinnovation.co |
| Francisco Lino | Hardware (Flinotech) | francisco.lino@flinotech.com |

---

> _"I design to free."_ — Planta Smart Homes
