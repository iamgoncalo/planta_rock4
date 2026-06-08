/* ============================================================================
 *  PlantaOS · Rock in Rio Lisboa 2026
 *  LilyGo TTGO LoRa32 V2.1 (ESP32-PICO-D4)
 *  ETIQUETA: WC-07_M_LR
 * ============================================================================
 *  Cluster:  wc-07   (cluster_id no POST)
 *  Seccao:   m        ("m" | "f" | "u")
 *  Porta:    LR        ("LL" | "LR" | "C" | "")
 *  USAR_IR:  true      (true = LLH/LRH/LLW/LRW; false = LC/unissexo)
 *  Cap:      84
 *  Coord:    38.78278 / -9.09167
 * ============================================================================
 *  FIRMWARE RiR2026 v1 — Opcao A:
 *   - cluster_id fixo (sem sufixo), porta + secao no payload
 *   - IR A=GPIO36(VP) exterior  B=IO33 interior  debounce=-10000
 *   - A->B = entrada    B->A = saida
 *   - WiFi SEMPRE VIVO: setAutoReconnect, NUNCA esp_wifi_deinit
 *   - Promiscuo POR CIMA da ligacao WiFi (sem destruir stack)
 *   - OLED SSD1306 direto (sem U8g2 — bloqueia boot); init APOS WiFi
 *   - Watchdog PACIENTE: reinicia so apos 6 falhas seguidas (~45s)
 *   - POST /api/v1/ingest com fonte="lilygo", porta, secao
 * ========================================================================== */
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_wifi.h"
#include <Wire.h>

// ── Identidade ────────────────────────────────────────────────────────────────
const char* CLUSTER_ID = "wc-07";
const char* NOME_CURTO = "WC-07 MASC LR";
const char* PORTA_ID   = "LR";    // "LL", "LR", "C", ""
const char* SECAO_ID   = "m";   // "m", "f", "u"
int         CAPACIDADE = 84;
float       LAT        = 38.78278;
float       LON        = -9.09167;

const char* WIFI_SSID  = "RiR2026";
const char* WIFI_PASS  = "rockinrio2026";
const char* API_BASE   = "https://api.plantarockinrio.com";

// ── Pinos IR ──────────────────────────────────────────────────────────────────
// PROIBIDO: IO26 (LoRa DIO0, preso a 0)  |  EVITAR: GPIO39 (sem pull-up)
#define IR_A_PIN  36   // VP — exterior; idle=1, deteccao=0; pull-up interno
#define IR_B_PIN  33   // IO33 — interior; pull-up interno

// ── OLED SSD1306 (direto, sem U8g2) ──────────────────────────────────────────
#define OLED_ADDR 0x3C
#define OLED_SDA  21
#define OLED_SCL  22

// ── Estado WiFi/fusao ─────────────────────────────────────────────────────────
int falhasSeguidas = 0;
unsigned long bootMs = 0;

// ── Estado IR (so compilado se USAR_IR=true) ──────────────────────────────────
#if 1
volatile long _tA = -10000, _tB = -10000;  // debounce=-10000 (nao bloqueia 1o evento)
volatile long entradasIR = 0, saidasIR = 0;
#define DEBOUNCE_MS 80

void IRAM_ATTR isrA() {
  long now = millis();
  if (now - _tA < DEBOUNCE_MS) return;
  _tA = now;
  // A dispara primeiro: aguarda B dentro de 1s -> entrada
  if (_tB > 0 && (now - _tB) < 1000) {
    saidasIR++;       // B->A = saida
    _tB = -10000;
  } else {
    _tA = now;
  }
}
void IRAM_ATTR isrB() {
  long now = millis();
  if (now - _tB < DEBOUNCE_MS) return;
  _tB = now;
  // B dispara primeiro: aguarda A dentro de 1s -> entrada (A->B)
  if (_tA > 0 && (now - _tA) < 1000) {
    entradasIR++;     // A->B = entrada
    _tA = -10000;
  } else {
    _tB = now;
  }
}
void setupIR() {
  pinMode(IR_A_PIN, INPUT_PULLUP);
  pinMode(IR_B_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(IR_A_PIN), isrA, FALLING);
  attachInterrupt(digitalPinToInterrupt(IR_B_PIN), isrB, FALLING);
  Serial.println("IR OK (A=GPIO36 B=IO33 debounce=-10000)");
}
#else
long entradasIR = 0, saidasIR = 0;
void setupIR() { /* USAR_IR=false — sem pinos IR */ }
#endif

// ── Paxcount WiFi promiscuo ───────────────────────────────────────────────────
#define MAX_DEV 600
uint32_t devHash[MAX_DEV];
volatile int devCount = 0;
volatile int pacotesVistos = 0;
int rssiLimite = -72;
const unsigned long SNIFF_MS = 6000;
wifi_promiscuous_filter_t promiscFilter = {
  .filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT | WIFI_PROMIS_FILTER_MASK_DATA
};

void promiscCb(void* buf, wifi_promiscuous_pkt_type_t type) {
  pacotesVistos++;
  const wifi_promiscuous_pkt_t* p = (wifi_promiscuous_pkt_t*)buf;
  if (p->rx_ctrl.rssi < rssiLimite) return;
  const uint8_t* mac = p->payload + 10;
  uint32_t h = 2166136261u;
  for (int i = 0; i < 6; i++) { h ^= mac[i]; h *= 16777619u; }
  for (int i = 0; i < devCount; i++) if (devHash[i] == h) return;
  if (devCount < MAX_DEV) devHash[devCount++] = h;
}

int janelaContar() {
  int canalOriginal = WiFi.channel();
  esp_wifi_set_promiscuous_filter(&promiscFilter);
  esp_wifi_set_promiscuous_rx_cb(&promiscCb);
  esp_wifi_set_promiscuous(true);
  devCount = 0; pacotesVistos = 0;
  int canais[] = {1, 6, 11};
  for (int k = 0; k < 3; k++) {
    esp_wifi_set_channel(canais[k], WIFI_SECOND_CHAN_NONE);
    unsigned long t0 = millis();
    while (millis() - t0 < SNIFF_MS / 3) { delay(10); yield(); }
  }
  esp_wifi_set_promiscuous(false);
  if (canalOriginal >= 1 && canalOriginal <= 13)
    esp_wifi_set_channel(canalOriginal, WIFI_SECOND_CHAN_NONE);
  return devCount;
}

// ── OLED ──────────────────────────────────────────────────────────────────────
bool oledOk = false;
uint8_t oledBuf[1024];
void oCmd(uint8_t c) {
  Wire.beginTransmission(OLED_ADDR); Wire.write(0x00); Wire.write(c);
  Wire.endTransmission();
}
void oledInit() {
  Wire.begin(OLED_SDA, OLED_SCL); Wire.setClock(400000); Wire.setTimeOut(50);
  Wire.beginTransmission(OLED_ADDR);
  if (Wire.endTransmission() != 0) { oledOk = false; return; }
  oCmd(0xAE); oCmd(0xD5); oCmd(0x80); oCmd(0xA8); oCmd(0x3F);
  oCmd(0xD3); oCmd(0x00); oCmd(0x40); oCmd(0x8D); oCmd(0x14);
  oCmd(0x20); oCmd(0x00); oCmd(0xA1); oCmd(0xC8); oCmd(0xDA); oCmd(0x12);
  oCmd(0x81); oCmd(0xCF); oCmd(0xD9); oCmd(0xF1); oCmd(0xDB); oCmd(0x40);
  oCmd(0xA4); oCmd(0xA6); oCmd(0xAF);
  oledOk = true;
}
void oPix(int x, int y) {
  if (x < 0 || x > 127 || y < 0 || y > 63) return;
  oledBuf[(y / 8) * 128 + x] |= (1 << (y & 7));
}
struct Glyph { char c; uint8_t col[5]; };
const Glyph FONT[] = {
  {'0',{0x3E,0x51,0x49,0x45,0x3E}},{'1',{0x00,0x42,0x7F,0x40,0x00}},
  {'2',{0x42,0x61,0x51,0x49,0x46}},{'3',{0x21,0x41,0x45,0x4B,0x31}},
  {'4',{0x18,0x14,0x12,0x7F,0x10}},{'5',{0x27,0x45,0x45,0x45,0x39}},
  {'6',{0x3C,0x4A,0x49,0x49,0x30}},{'7',{0x01,0x71,0x09,0x05,0x03}},
  {'8',{0x36,0x49,0x49,0x49,0x36}},{'9',{0x06,0x49,0x49,0x29,0x1E}},
  {' ',{0,0,0,0,0}},{':',{0,0x36,0x36,0,0}},{'/',{0x20,0x10,0x08,0x04,0x02}},
  {'E',{0x7F,0x49,0x49,0x49,0x41}},{'I',{0x00,0x41,0x7F,0x41,0x00}},
  {'L',{0x7F,0x40,0x40,0x40,0x40}},{'M',{0x7F,0x02,0x0C,0x02,0x7F}},
  {'U',{0x3F,0x40,0x40,0x40,0x3F}},{'F',{0x7F,0x09,0x09,0x09,0x01}},
  {'C',{0x3E,0x41,0x41,0x41,0x22}},
};
const int NF = sizeof(FONT) / sizeof(FONT[0]);
const uint8_t* glyph(char c) {
  for (int i = 0; i < NF; i++) if (FONT[i].c == c) return FONT[i].col;
  return FONT[10].col;  // espaço
}
void oChar(int x, int y, char c, int sz) {
  const uint8_t* g = glyph(c);
  for (int col = 0; col < 5; col++) {
    uint8_t b = g[col];
    for (int row = 0; row < 7; row++)
      if (b & (1 << row))
        for (int dx = 0; dx < sz; dx++)
          for (int dy = 0; dy < sz; dy++)
            oPix(x + col * sz + dx, y + row * sz + dy);
  }
}
void oText(int x, int y, const char* s, int sz) {
  int cx = x;
  while (*s) { oChar(cx, y, *s, sz); cx += (5 * sz + sz); s++; }
}
void oledShow() {
  if (!oledOk) return;
  for (int pag = 0; pag < 8; pag++) {
    oCmd(0xB0 + pag); oCmd(0x00); oCmd(0x10);
    for (int col = 0; col < 128; col += 16) {
      Wire.beginTransmission(OLED_ADDR); Wire.write(0x40);
      for (int i = 0; i < 16; i++) Wire.write(oledBuf[pag * 128 + col + i]);
      Wire.endTransmission(); yield();
    }
  }
}
void oledDraw(int pessoas, int entradas, int saidas) {
  if (!oledOk) return;
  memset(oledBuf, 0, sizeof(oledBuf));
  // Linha 1: NOME_CURTO
  oText(0, 0, NOME_CURTO, 1);
  // Linha 2: numero grande de pessoas
  char num[6]; snprintf(num, sizeof(num), "%d", pessoas);
  oText(6, 14, num, 3);
  char cap[8]; snprintf(cap, sizeof(cap), "/%d", CAPACIDADE);
  oText(70, 22, cap, 2);
  // Linha 3: E/S se IR activo
  char es[20]; snprintf(es, sizeof(es), "E:%ld S:%ld", entradas, saidas);
  oText(0, 52, es, 1);
  // Barra de ocupacao
  int pct = CAPACIDADE > 0 ? (int)((long)pessoas * 100 / CAPACIDADE) : 0;
  if (pct > 100) pct = 100;
  for (int x = 0; x < 128; x++) { oPix(x, 42); oPix(x, 50); }
  int w = 126 * pct / 100;
  for (int x = 1; x <= w; x++) for (int y = 43; y <= 49; y++) oPix(x, y);
  oledShow();
}

// ── WiFi SEMPRE VIVO ──────────────────────────────────────────────────────────
void garantirWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("(religar)");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) {
    delay(250); yield();
  }
}

// ── Envio POST /api/v1/ingest ─────────────────────────────────────────────────
void enviar(int pessoas, int telemoveis) {
  garantirWiFi();
  if (WiFi.status() != WL_CONNECTED) {
    falhasSeguidas++;
    Serial.printf("sem WiFi (%d/6)\n", falhasSeguidas);
    goto watchdog;
  }

  {
    HTTPClient http;
    String url = String(API_BASE) + "/api/v1/ingest";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(8000);

    char payload[800];
    snprintf(payload, sizeof(payload),
      "{"
        "\"cluster_id\":\"%s\","
        "\"ts\":%lu,"
        "\"params\":{"
          "\"telemoveis_detectados\":%d,"
          "\"pessoas_estimadas\":%d,"
          "\"entradas_ir\":%ld,"
          "\"saidas_ir\":%ld,"
          "\"ocupacao_instantanea\":%d,"
          "\"estado_sensor\":\"okay\","
          "\"fonte\":\"lilygo\","
          "\"porta\":\"%s\","
          "\"secao\":\"%s\","
          "\"rssi\":%d,"
          "\"pacotes\":%d,"
          "\"uptime_s\":%lu,"
          "\"lat\":%.6f,"
          "\"lon\":%.6f"
        "}"
      "}",
      CLUSTER_ID,
      (unsigned long)(millis() - bootMs),
      telemoveis,
      pessoas,
      entradasIR, saidasIR,
      (CAPACIDADE > 0) ? (int)((long)pessoas * 100 / CAPACIDADE) : 0,
      PORTA_ID, SECAO_ID,
      (int)WiFi.RSSI(),
      pacotesVistos,
      (unsigned long)((millis() - bootMs) / 1000),
      LAT, LON
    );

    int code = http.POST(String(payload));
    if (code > 0) {
      falhasSeguidas = 0;
      Serial.printf("POST %d | %s/%s | pess=%d E:%ld S:%ld | rssi=%d\n",
        code, PORTA_ID, SECAO_ID, pessoas, entradasIR, saidasIR, (int)WiFi.RSSI());
    } else {
      falhasSeguidas++;
      Serial.printf("POST falhou %d (%d/6)\n", code, falhasSeguidas);
    }
    http.end();
  }

watchdog:
  if (falhasSeguidas >= 6) {
    Serial.println(">> 6 falhas — reinicio de seguranca");
    delay(500);
    ESP.restart();
  }
}

// ── setup / loop ──────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200); delay(1500);
  Serial.printf("\n>>> PlantaOS RiR2026 · %s · %s/%s <<<\n",
    NOME_CURTO, PORTA_ID, SECAO_ID);
  Serial.printf("Cluster: %s  Cap: %d  IR: %s\n",
    CLUSTER_ID, CAPACIDADE, "sim");
  bootMs = millis();

  // WiFi — ligar uma vez, manter sempre
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  { unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 10000) {
      delay(300); Serial.print("."); yield();
    }
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " ligado" : " (liga depois)");

  // OLED apos WiFi (nunca antes — garante boot limpo)
  oledInit();

  // IR
  setupIR();
}

void loop() {
  int telemoveis = janelaContar();
  int divisor = 3;
  int pessoas = (telemoveis + divisor / 2) / divisor;
  enviar(pessoas, telemoveis);
  oledDraw(pessoas, entradasIR, saidasIR);
}
