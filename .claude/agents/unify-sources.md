---
name: unify-sources
description: Routers fora da fonte única passam a ler get_live_payload. ALTERA backend.
tools: Read, Edit, Bash
model: sonnet
---

Routers que podem divergir dos dados principais: alerts, devices, fleet, envs, incidents, fusion.
A fonte única é get_live_payload() em app/services/live_payload.py (ou equivalente).

Para cada router:
1. Verificar se usa get_live_payload ou tem dados próprios
2. Se tem dados próprios que devem ser sincronizados → migrar para get_live_payload
3. Se justificavelmente independente (ex: fusion tem lógica própria) → documentar num comentário
4. Garantir que nenhuma página v2 mostra números divergentes dos outros routers

pytest -q verde. Nenhum endpoint quebra.
