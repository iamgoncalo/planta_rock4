---
name: ino-generator-uni
description: Gera os 4 .ino unissexo SEM IR (wc-05 e wc-06, 2 por cluster). ALTERA firmware.
tools: Read, Write, Bash
model: sonnet
---
Le firmware/rir2026/_TEMPLATE.ino. Gera 4 ficheiros unissexo com USAR_IR=false.

wc05_a.ino → CLUSTER_ID="wc-05-u", NOME="WC-05 UNI A", USAR_IR=false, CAP=133
wc05_b.ino → CLUSTER_ID="wc-05-u", NOME="WC-05 UNI B", USAR_IR=false, CAP=133
wc06_a.ino → CLUSTER_ID="wc-06-u", NOME="WC-06 UNI A", USAR_IR=false, CAP=208
wc06_b.ino → CLUSTER_ID="wc-06-u", NOME="WC-06 UNI B", USAR_IR=false, CAP=208

Caracteristicas unissexo:
- Sem pinos IR (nao compilar bloco IR).
- So paxcount WiFi promiscuo.
- Mesmo watchdog, OLED, payload que o template.
- campo porta="" (vazio).
- fonte="lilygo".
- contexto="festival".

Etiqueta: // ETIQUETA: WC-05_U_A, WC-05_U_B, WC-06_U_A, WC-06_U_B

Destino: firmware/rir2026/wc05_a.ino, wc05_b.ino, wc06_a.ino, wc06_b.ino
