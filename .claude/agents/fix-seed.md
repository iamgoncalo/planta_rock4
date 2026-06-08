---
name: fix-seed
description: Seed de sensores para a arquitetura REAL (34 LilyGo) com coords de clusters_geo. ALTERA backend.
tools: Read, Edit, Bash
model: sonnet
---

O seed actual (seeds/sensors.py) gera 66 nós da arquitetura antiga com coords erradas.
O seed correto deve gerar a arquitetura REAL:

Por cluster M/F (wc-01,02,03,04,07,08): 5 LilyGo (LLH/LRH/LLW/LRW/LC) = 30 nós
Por cluster UNI (wc-05,06): 2 LilyGo (UNI-A/UNI-B) = 4 nós
Total LilyGo: 34

Mais por cluster (opcionais, não-LilyGo):
- Luxonis OAK-D Lite por cluster M/F = 6 câmaras
- Prosegur por cluster = 8 contagens

Coords: importar de app/clusters_geo.CLUSTERS_GEO + _gps_from_metres.
Pinos: IR_A=GPIO36, IR_B=IO33.

Apagar o seed de 66 nós. /sensors deve refletir os 34 LilyGo após seed.
psycopg2 síncrono dentro de app async: usar asyncpg ou executar via alembic seed.
pytest -q verde.
