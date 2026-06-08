---
name: harden
description: Backend hiper resiliente — nunca 500, snapshot persistido, try/except completo. ALTERA backend.
tools: Read, Edit, Bash
model: sonnet
---

Objectivos:
1. flow_history.py: cada query individual em try/except; devolve [] ou último valor em caso de erro.
2. ingest_store: snapshot a Postgres cada 60s (thread separada). Ao reiniciar, recarrega snapshot.
   Tabela: ingest_snapshots (cluster_id, params_json, ts_server, ts_device).
3. Nenhum endpoint devolve HTTP 500 ao utilizador — sempre último valor + age_s ou {"ok":false, "reason":"..."}.
4. Watchdog de restart do ingest_store: se Postgres indisponível, funciona com o estado em memória.

pytest -q verde. railway up + health check verde.
