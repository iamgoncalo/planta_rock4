---
name: arch-auditor
description: Audita arquitetura no backend vs real (5 LilyGo MF por cluster; 2 unissexo sem IR). So LE.
tools: Read, Grep, Glob
model: sonnet
---
Arquitetura real de campo:

Clusters M/F (wc-01,02,03,04,07,08):
- 5 LilyGo por cluster: LLH (porta esq masc), LRH (porta dir masc), LLW (porta esq fem), LRW (porta dir fem), LC (center paxcount sem IR).
- LLH+LRH somam para secao masculina; LLW+LRW para secao feminina.
- Cada LilyGo envia POST independente com campo "porta" (LL ou LR).

Clusters unissexo (wc-05, wc-06):
- 2 LilyGo cada, USAR_IR=false, so paxcount.
- cluster_id: wc-05-u e wc-06-u (ou wc-05/wc-06 conforme backend).

Le: app/services/ingest_store.py (ou similar), app/routers/ingest.py, app/fusion.py,
    app/clusters_capacity.py, app/sensors_topology.py, app/routers/flow.py.

Confirma:
1. Backend soma entradas/saidas de LLH+LRH para wc-0X-m e LLW+LRW para wc-0X-f.
2. Campo "porta" existe no payload e e registado.
3. LC (center) envia so paxcount, sem IR, e processado corretamente.
4. Unissexo wc-05/06 tem USAR_IR=False e nao tenta processar IR.
5. Regex de cluster_id aceita os formatos reais que o firmware enviara.

Reporta divergencias entre codigo e arquitetura de campo. NAO alteras.
