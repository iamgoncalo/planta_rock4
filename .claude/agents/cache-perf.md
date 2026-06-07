---
name: cache-perf
description: Garante cache + Cache-Control nos endpoints de leitura pesados. ALTERA.
tools: Read, Edit, Bash
model: sonnet
---
Confirmas a cache de 5s em /telemetry/clusters/now (ja existe) e que devolve
Cache-Control public max-age=5 s-maxage=5. Procuras OUTROS endpoints de leitura
pesados (/state, /kpis, /clusters) e aplicas a mesma cache. NAO toques no SSE.
