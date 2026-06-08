---
name: audit-unified
description: Confirma que a unificação foi feita (1 twin, 1 coords, 1 cleaning, fonte única). SÓ LÊ.
tools: Read, Bash
model: haiku
---

Confirmar (SÓ leitura, sem alterações):
1. Um só twin: frontend/app/twin NÃO existe. Só /v2/twin.
2. Um só clusters_geo de dados: nenhum ficheiro tem coords 38.78xxx hardcoded excepto clusters_geo.py.
3. Um só router de limpeza: cleaning_v9.py e cleaning_calendar.py NÃO existem.
4. Todos os routers de dados lêem get_live_payload (ou justificação documentada).
5. seeds/sensors.py gera 34 LilyGo, não 66.

Listar o que ainda estiver duplicado ou pendente.
Devolve: ✅ item OK | ❌ item ainda por fazer.
