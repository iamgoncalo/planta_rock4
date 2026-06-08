---
name: ino-template
description: Template .ino base IR + paxcount + flag porta/fonte. ALTERA firmware.
tools: Read, Write, Edit, Bash
model: sonnet
---
Cria firmware/rir2026/_TEMPLATE.ino com estas caracteristicas obrigatorias:

CABECALHO (variaveis a substituir por cluster):
  CLUSTER_ID, NOME, CAP, PORTA ("LL" ou "LR"), USAR_IR (true/false), LAT, LON

PINOS IR (obrigatorio quando USAR_IR=true):
  #define IR_A_PIN 36   // exterior, GPIO36 VP, pull-up interno, idle=1 detecao=0
  #define IR_B_PIN 33   // interior, IO33, pull-up interno

DEBOUNCE:
  volatile long lastA = -10000, lastB = -10000;  // -10000 para nao bloquear 1o evento

DIRECAO:
  A antes de B = entrada; B antes de A = saida.

WIFI:
  WiFi.persistent(false); WiFi.mode(WIFI_STA); WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  NUNCA esp_wifi_deinit() no ciclo. Promiscuo por cima da ligacao existente.

OLED:
  Usar codigo SSD1306 direto (sem biblioteca U8g2 — bloqueia boot).
  oledInit() chamado APOS WiFi.begin(), nao antes.
  Pinos SDA=21, SCL=22.

WATCHDOG:
  So reinicia apos 6 falhas seguidas (~45s). falhasSeguidas++ em cada erro, reset em sucesso.

PAYLOAD POST /api/v1/ingest:
  cluster_id, ts (ms), params: {telemoveis_detectados, pessoas_estimadas, homens, mulheres,
  entradas_ir, saidas_ir, ocupacao_instantanea, contagem_prosegur, confianca_cruzada,
  estado_sensor, porta, fonte:"lilygo", uptime_s, rssi}
  "fonte":"lilygo" sempre presente.

WiFi: SSID="RiR2026", PASS="rockinrio2026"
API: api.plantarockinrio.com

O template deve ter #ifdef USAR_IR para compilar IR so quando necessario.
Lê firmware/rockinrio_v6/rockinrio_v6.ino como referencia de estrutura.
Cria o ficheiro em firmware/rir2026/_TEMPLATE.ino.
