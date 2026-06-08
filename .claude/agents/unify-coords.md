---
name: unify-coords
description: clusters_geo.py = única fonte de coordenadas. Apaga o segundo, os ficheiros hardcoded importam de lá. ALTERA backend.
tools: Read, Edit, Bash
model: sonnet
---

app/clusters_geo.py é a ÚNICA fonte de verdade de coordenadas GPS.
ANCHOR_GPS e _gps_from_metres são a forma canónica de derivar lat/lon.

Ficheiros a corrigir:
- app/core/sensor_registry.py → substituir dict hardcoded por import de CLUSTERS_GEO + _gps_from_metres
- app/seeds/sensors.py → idem
- app/startup_seeds.py → idem
- app/services/routing.py → substituir dict hardcoded por GPS de clusters_geo
- app/services/weather.py → substituir LAT/LON hardcoded por ANCHOR_GPS
- app/services/state.py → substituir lat hardcoded por ANCHOR_GPS
- app/routers/chat.py → substituir lat hardcoded por ANCHOR_GPS

NÃO apagar app/routers/clusters_geo.py — é um thin wrapper que serve /api/v1/clusters/geo.
Testes verdes (pytest -q) antes de commitar.
Zero divergências: todas as coords derivam de CLUSTERS_GEO + ANCHOR_GPS.
