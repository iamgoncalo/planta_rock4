---
name: ino-generator-mf
description: Gera os 30 .ino M/F (LLH LRH LLW LRW LC por cluster wc-01,02,03,04,07,08). ALTERA firmware.
tools: Read, Write, Bash
model: sonnet
---
Le firmware/rir2026/_TEMPLATE.ino e app/clusters_geo.py (ou clusters_capacity.py) para coords e capacidades.

Gera 5 .ino por cada cluster em {wc-01, wc-02, wc-03, wc-04, wc-07, wc-08} = 30 ficheiros total.

Por cluster wc-0X:
  wc0X_h_ll.ino  → CLUSTER_ID="wc-0X-m", PORTA="LL", USAR_IR=true,  NOME="WC-0X MASC LL"
  wc0X_h_lr.ino  → CLUSTER_ID="wc-0X-m", PORTA="LR", USAR_IR=true,  NOME="WC-0X MASC LR"
  wc0X_w_ll.ino  → CLUSTER_ID="wc-0X-f", PORTA="LL", USAR_IR=true,  NOME="WC-0X FEM LL"
  wc0X_w_lr.ino  → CLUSTER_ID="wc-0X-f", PORTA="LR", USAR_IR=true,  NOME="WC-0X FEM LR"
  wc0X_center.ino → CLUSTER_ID="wc-0X-c", PORTA="",  USAR_IR=false, NOME="WC-0X CENTER"

Cada ficheiro tem no cabecalho a etiqueta: // ETIQUETA: {CLUSTER}_{SEC}_{TAG}
Ex: // ETIQUETA: WC-01_M_LL

Capacidades e coords (LAT/LON) retirados de clusters_geo.py ou clusters_capacity.py.
Se nao encontrar coords para um cluster, usa 38.7XXX / -9.1XXX (placeholder).

Destino: firmware/rir2026/wc0X_h_ll.ino etc.
