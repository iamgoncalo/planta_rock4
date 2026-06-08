---
name: unify-cleaning
description: Um só router de limpeza. Funde cleaning_v9 + cleaning_calendar em cleaning. ALTERA backend.
tools: Read, Edit, Bash
model: sonnet
---

Três routers existem: cleaning.py, cleaning_calendar.py, cleaning_v9.py.
O resultado deve ser um só router app/routers/cleaning.py com todas as funcionalidades.

Passos:
1. Ler os três routers para perceber o que cada um faz
2. Fundir endpoints úteis em cleaning.py
3. Actualizar app/main.py para remover imports de cleaning_calendar e cleaning_v9
4. Apagar cleaning_calendar.py e cleaning_v9.py
5. app/models/cleaning_v9.py — avaliar se pode ser movido para cleaning.py ou models.py
6. pytest -q verde

/v2/cleaning consome o router unificado. Nenhuma rota pública quebra.
