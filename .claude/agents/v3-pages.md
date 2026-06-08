---
name: v3-pages
description: 8 páginas /v3 (home, twin, scor, flow, screen, install, cleaning, shows). ALTERA frontend.
tools: Read, Edit, Write, Bash
model: sonnet
---

APENAS DEPOIS de v3-layout estar completo e verde.

8 páginas /v3, uma de cada vez, com build verde entre cada:
| Rota         | Endpoint principal                             |
|--------------|------------------------------------------------|
| /v3          | /api/v1/kpis                                   |
| /v3/twin     | /clusters/geo + /telemetry/clusters/now        |
| /v3/scor     | /state (stream SSE ou poll)                    |
| /v3/flow     | /flow + /flow/history + /flow/forecast         |
| /v3/screen   | /screen/copy + /telemetry/clusters/now         |
| /v3/install  | /ingest/status (autónoma)                      |
| /v3/cleaning | /cleaning (router unificado)                   |
| /v3/shows    | /shows                                         |

Regras:
- 100svh sem scroll (position:fixed; top:var(--v3-header-h); bottom:var(--v3-bar-h))
- Azul #0A6CFF para elementos activos/CTA
- Rosa #FF2E93 só para 1 destaque por ecrã
- Âmbar #C25A1A para crítico, NUNCA vermelho
- Sem SIMULADO, sem tracking individual
- v2 INTACTA
- npm run build verde após cada página
