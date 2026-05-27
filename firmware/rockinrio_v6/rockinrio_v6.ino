/*
 * PlantaOS × Rock in Rio Lisboa 2026
 * Firmware v6 — BIDIRECTIONAL — receives commands, streams serial, OTA
 *
 * Board: TTGO T-SIM7000G (ESP32) OR LilyGo LoRa32 V1
 * Libraries required (install via Arduino Library Manager):
 *   - PubSubClient 2.8.0 (knolleary)
 *   - ArduinoJson 7.x (bblanchon)
 *   - WiFi (built-in ESP32)
 *   - HTTPClient (built-in ESP32)
 *   - HTTPUpdate (built-in ESP32)
 *   - Preferences (built-in ESP32)
 *
 * Upload:
 *   1. Arduino IDE → Tools → Board → ESP32 Dev Module
 *   2. Tools → Port → select COM port
 *   3. Upload Speed: 921600
 *   4. Hold BOOT button during upload if needed
 *   5. After upload: press RST to start
 */

// ═══════════════════════════════════════════════════════════
// CONFIGURATION — edit these per device before flashing
// After first flash, use 'set' commands to change at runtime
// ═══════════════════════════════════════════════════════════
#define DEFAULT_CLUSTER_ID   "WC-01"
#define FIRMWARE_VERSION     "6.0.0"
#define FIRMWARE_BUILD_DATE  __DATE__ " " __TIME__

#define WIFI_SSID  "PlantaOS-RIR"
#define WIFI_PASS  "planta2026"

// Local RPi during setup: "192.168.1.120"
// Production: hostname from Railway
#define MQTT_HOST  "192.168.1.120"
#define MQTT_PORT  1883
#define MQTT_USER  DEFAULT_CLUSTER_ID
#define MQTT_PASS  "planta2026mqtt"

// IR GPIO (LilyGo LoRa32 V1)
#define IR1_ENT_INT  13
#define IR2_ENT_EXT  14
#define IR3_SAI_INT  26
#define IR4_SAI_EXT  27

#define HEARTBEAT_MS   10000
#define TELEMETRY_MS   60000
#define DEBOUNCE_MS    200
#define DIRECTION_MS   500

// ═══════════════════════════════════════════════════════════
// INCLUDES
// ═══════════════════════════════════════════════════════════
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <esp_wifi.h>

// ═══════════════════════════════════════════════════════════
// GLOBALS
// ═══════════════════════════════════════════════════════════
Preferences  prefs;
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);

char     cluster_id[16];
float    wifi_factor;
uint32_t post_interval_ms;
float    ir_calibration;
uint32_t direction_window_ms;
bool     serial_stream_enabled;

volatile uint32_t entradas     = 0;
volatile uint32_t saidas       = 0;
volatile uint32_t ocupacao_ir  = 0;
volatile uint32_t mac_count    = 0;

volatile unsigned long t_ir1 = 0, t_ir2 = 0, t_ir3 = 0, t_ir4 = 0;

unsigned long last_heartbeat = 0;
unsigned long last_telemetry = 0;

char topic_telemetry[64];
char topic_status[64];
char topic_serial[64];
char topic_response[64];
char topic_event[64];
char topic_cmd[64];
char topic_broadcast[32] = "planta/system/broadcast";

// ═══════════════════════════════════════════════════════════
// CONFIG (NVS Preferences)
// ═══════════════════════════════════════════════════════════
void load_config() {
  prefs.begin("plantaos", false);
  String saved_id = prefs.getString("cluster_id", DEFAULT_CLUSTER_ID);
  saved_id.toCharArray(cluster_id, 16);
  wifi_factor           = prefs.getFloat("wifi_factor",  2.5);
  post_interval_ms      = prefs.getUInt( "post_interval", TELEMETRY_MS);
  ir_calibration        = prefs.getFloat("ir_cal",        1.0);
  direction_window_ms   = prefs.getUInt( "dir_window",    DIRECTION_MS);
  serial_stream_enabled = prefs.getBool( "serial_stream", false);
  prefs.end();

  snprintf(topic_telemetry, 64, "planta/wc/%s/telemetry", cluster_id);
  snprintf(topic_status,    64, "planta/wc/%s/status",    cluster_id);
  snprintf(topic_serial,    64, "planta/wc/%s/serial",    cluster_id);
  snprintf(topic_response,  64, "planta/wc/%s/response",  cluster_id);
  snprintf(topic_event,     64, "planta/wc/%s/event",     cluster_id);
  snprintf(topic_cmd,       64, "planta/wc/%s/cmd",       cluster_id);

  Serial.printf("[CONFIG] cluster=%s wifi_factor=%.1f ir_cal=%.2f\n",
    cluster_id, wifi_factor, ir_calibration);
}

void save_config() {
  prefs.begin("plantaos", false);
  prefs.putString("cluster_id",    cluster_id);
  prefs.putFloat( "wifi_factor",   wifi_factor);
  prefs.putUInt(  "post_interval", post_interval_ms);
  prefs.putFloat( "ir_cal",        ir_calibration);
  prefs.putUInt(  "dir_window",    direction_window_ms);
  prefs.putBool(  "serial_stream", serial_stream_enabled);
  prefs.end();
}

// ═══════════════════════════════════════════════════════════
// IR ISRs
// ═══════════════════════════════════════════════════════════
void publish_event(const char* direction, uint32_t count);

void IRAM_ATTR isr_ir1() {
  if (millis() - t_ir1 > DEBOUNCE_MS) t_ir1 = millis();
}
void IRAM_ATTR isr_ir2() {
  unsigned long now = millis();
  if (now - t_ir2 < DEBOUNCE_MS) return;
  t_ir2 = now;
  if (t_ir1 > 0 && now - t_ir1 < direction_window_ms) {
    uint32_t real = max(1U, (uint32_t)(1.0 / ir_calibration));
    entradas   += real;
    ocupacao_ir = min(ocupacao_ir + real, (uint32_t)500);
    t_ir1 = 0;
    publish_event("entrada", real);
  }
}
void IRAM_ATTR isr_ir3() {
  if (millis() - t_ir3 > DEBOUNCE_MS) t_ir3 = millis();
}
void IRAM_ATTR isr_ir4() {
  unsigned long now = millis();
  if (now - t_ir4 < DEBOUNCE_MS) return;
  t_ir4 = now;
  if (t_ir3 > 0 && now - t_ir3 < direction_window_ms) {
    uint32_t real = max(1U, (uint32_t)(1.0 / ir_calibration));
    saidas++;
    if (ocupacao_ir >= real) ocupacao_ir -= real; else ocupacao_ir = 0;
    t_ir3 = 0;
    publish_event("saida", real);
  }
}

// ═══════════════════════════════════════════════════════════
// WiFi SNIFFER
// ═══════════════════════════════════════════════════════════
void IRAM_ATTR sniffer_cb(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type == WIFI_PKT_MGMT) mac_count++;
}

// ═══════════════════════════════════════════════════════════
// PUBLISH HELPERS
// ═══════════════════════════════════════════════════════════
bool mqtt_publish(const char* topic, JsonDocument& doc) {
  char buf[512];
  size_t n = serializeJson(doc, buf, sizeof(buf));
  return mqtt.publish(topic, buf, n);
}

void publish_event(const char* direction, uint32_t count) {
  if (!mqtt.connected()) return;
  JsonDocument doc;
  doc["cluster_id"]  = cluster_id;
  doc["direction"]   = direction;
  doc["count"]       = count;
  doc["ocupacao_ir"] = ocupacao_ir;
  doc["ts"]          = millis() / 1000;
  mqtt_publish(topic_event, doc);
  Serial.printf("[IR] %s: %d pessoa(s) — ocupacao=%d\n", direction, count, (int)ocupacao_ir);
}

void publish_status() {
  JsonDocument doc;
  doc["cluster_id"]    = cluster_id;
  doc["firmware_ver"]  = FIRMWARE_VERSION;
  doc["build_date"]    = FIRMWARE_BUILD_DATE;
  doc["uptime_s"]      = millis() / 1000;
  doc["ip"]            = WiFi.localIP().toString();
  doc["rssi_dbm"]      = WiFi.RSSI();
  doc["wifi_ssid"]     = WiFi.SSID();
  doc["mac"]           = WiFi.macAddress();
  doc["wifi_factor"]   = wifi_factor;
  doc["ir_cal"]        = ir_calibration;
  doc["dir_window"]    = direction_window_ms;
  doc["post_interval"] = post_interval_ms;
  doc["entradas_total"]= entradas;
  doc["saidas_total"]  = saidas;
  doc["ocupacao_ir"]   = ocupacao_ir;
  doc["mac_count_sec"] = mac_count;
  doc["heap_free"]     = ESP.getFreeHeap();
  mqtt_publish(topic_status, doc);

  if (serial_stream_enabled) {
    char msg[256];
    snprintf(msg, 256, "[STATUS] %s · uptime=%lus · ip=%s · rssi=%d · occ=%d",
      cluster_id, millis()/1000, WiFi.localIP().toString().c_str(),
      WiFi.RSSI(), (int)ocupacao_ir);
    mqtt.publish(topic_serial, msg);
  }
}

void publish_telemetry() {
  uint32_t pessoas_wifi = (uint32_t)(mac_count / wifi_factor);
  JsonDocument doc;
  doc["cluster_id"]             = cluster_id;
  doc["ts"]                     = millis() / 1000;
  doc["telemoveis_detectados"]  = mac_count;
  doc["pessoas_estimadas_wifi"] = pessoas_wifi;
  doc["entradas_ir"]            = entradas;
  doc["saidas_ir"]              = saidas;
  doc["ocupacao_ir"]            = ocupacao_ir;
  doc["uptime_s"]               = millis() / 1000;
  mqtt_publish(topic_telemetry, doc);
  mac_count = 0;
  Serial.printf("[TELEMETRY] occ=%d wifi=%d entradas=%d saidas=%d\n",
    (int)ocupacao_ir, (int)pessoas_wifi, (int)entradas, (int)saidas);
}

// ═══════════════════════════════════════════════════════════
// COMMAND HANDLER
// ═══════════════════════════════════════════════════════════
void handle_command(const char* payload_str) {
  Serial.printf("[CMD] received: %s\n", payload_str);

  JsonDocument cmd;
  DeserializationError err = deserializeJson(cmd, payload_str);
  if (err) { Serial.printf("[CMD] JSON error: %s\n", err.c_str()); return; }

  const char* action = cmd["cmd"] | "unknown";
  JsonDocument resp;
  resp["cluster_id"] = cluster_id;
  resp["cmd"]        = action;
  resp["ts"]         = millis() / 1000;

  if (strcmp(action, "ping") == 0) {
    resp["pong"]     = true;
    resp["uptime_s"] = millis() / 1000;
    resp["ip"]       = WiFi.localIP().toString();
    resp["rssi_dbm"] = WiFi.RSSI();
    resp["firmware"] = FIRMWARE_VERSION;
    resp["ocupacao"] = ocupacao_ir;
    resp["status"]   = "ok";

  } else if (strcmp(action, "diagnostics") == 0) {
    resp["firmware_ver"]  = FIRMWARE_VERSION;
    resp["build_date"]    = FIRMWARE_BUILD_DATE;
    resp["uptime_s"]      = millis() / 1000;
    resp["ip"]            = WiFi.localIP().toString();
    resp["rssi_dbm"]      = WiFi.RSSI();
    resp["heap_free"]     = ESP.getFreeHeap();
    resp["flash_size"]    = ESP.getFlashChipSize();
    resp["wifi_factor"]   = wifi_factor;
    resp["ir_cal"]        = ir_calibration;
    resp["dir_window"]    = direction_window_ms;
    resp["post_interval"] = post_interval_ms;
    resp["entradas"]      = entradas;
    resp["saidas"]        = saidas;
    resp["ocupacao_ir"]   = ocupacao_ir;
    resp["mac_ssid"]      = WiFi.SSID();
    resp["mac_address"]   = WiFi.macAddress();
    resp["status"]        = "ok";

  } else if (strcmp(action, "set_wifi_factor") == 0) {
    float prev = wifi_factor;
    wifi_factor = cmd["value"] | wifi_factor;
    save_config();
    resp["prev"]   = prev;
    resp["now"]    = wifi_factor;
    resp["saved"]  = true;
    resp["status"] = "ok";

  } else if (strcmp(action, "set_post_interval") == 0) {
    post_interval_ms = cmd["value"] | post_interval_ms;
    save_config();
    resp["post_interval_ms"] = post_interval_ms;
    resp["status"]           = "ok";

  } else if (strcmp(action, "set_cluster_id") == 0) {
    const char* new_id = cmd["value"] | "";
    if (strlen(new_id) > 0) {
      strlcpy(cluster_id, new_id, 16);
      save_config();
      resp["cluster_id"] = cluster_id;
      resp["status"]     = "ok";
      resp["note"]       = "Restart required for new topic subscription";
    } else {
      resp["status"] = "error";
      resp["msg"]    = "empty cluster_id";
    }

  } else if (strcmp(action, "calibrate_ir") == 0) {
    float prev     = ir_calibration;
    ir_calibration = cmd["factor"] | ir_calibration;
    save_config();
    resp["prev"]   = prev;
    resp["now"]    = ir_calibration;
    resp["status"] = "ok";

  } else if (strcmp(action, "set_direction_window") == 0) {
    direction_window_ms = cmd["value"] | direction_window_ms;
    save_config();
    resp["direction_window_ms"] = direction_window_ms;
    resp["status"]              = "ok";

  } else if (strcmp(action, "reset_counters") == 0) {
    entradas = saidas = ocupacao_ir = 0;
    resp["status"] = "ok";
    resp["note"]   = "Counters reset to 0";

  } else if (strcmp(action, "stream_serial") == 0) {
    serial_stream_enabled = cmd["enable"] | false;
    save_config();
    resp["serial_stream"] = serial_stream_enabled;
    resp["status"]        = "ok";

  } else if (strcmp(action, "get_status") == 0) {
    publish_status();
    resp["status"] = "ok";
    resp["note"]   = "Status published to /status topic";

  } else if (strcmp(action, "ota") == 0) {
    const char* url = cmd["url"] | "";
    if (strlen(url) == 0) {
      resp["status"] = "error";
      resp["msg"]    = "No OTA URL provided";
    } else {
      resp["status"] = "updating";
      resp["url"]    = url;
      mqtt_publish(topic_response, resp);
      Serial.printf("[OTA] Starting update from: %s\n", url);
      WiFiClient ota_client;
      t_httpUpdate_return ret = httpUpdate.update(ota_client, url);
      if (ret == HTTP_UPDATE_FAILED) {
        Serial.printf("[OTA] FAILED: %s\n", httpUpdate.getLastErrorString().c_str());
      }
      return;
    }

  } else if (strcmp(action, "restart") == 0) {
    resp["status"] = "restarting";
    mqtt_publish(topic_response, resp);
    delay(500);
    ESP.restart();
    return;

  } else {
    resp["status"] = "error";
    resp["msg"]    = "Unknown command";
    resp["cmd"]    = action;
  }

  mqtt_publish(topic_response, resp);
  char buf[256];
  serializeJson(resp, buf, 256);
  Serial.printf("[CMD_RESP] %s\n", buf);
}

// ═══════════════════════════════════════════════════════════
// MQTT CALLBACK
// ═══════════════════════════════════════════════════════════
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  char msg[512];
  strlcpy(msg, (char*)payload, min((unsigned int)511, length) + 1);
  if (strstr(topic, "/cmd") || strcmp(topic, topic_broadcast) == 0) {
    handle_command(msg);
  }
}

// ═══════════════════════════════════════════════════════════
// CONNECT
// ═══════════════════════════════════════════════════════════
void connect_wifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500); Serial.print("."); tries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] OK — IP: %s RSSI: %d\n",
      WiFi.localIP().toString().c_str(), WiFi.RSSI());
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_promiscuous_rx_cb(&sniffer_cb);
  } else {
    Serial.println("\n[WiFi] FAILED — running offline");
  }
}

void connect_mqtt() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqtt_callback);
  mqtt.setBufferSize(1024);
  Serial.printf("[MQTT] Connecting to %s:%d as %s\n", MQTT_HOST, MQTT_PORT, cluster_id);

  char lwt_topic[64] = "planta/system/online";
  char lwt_msg[64];
  snprintf(lwt_msg, 64, "{\"cluster_id\":\"%s\",\"online\":false}", cluster_id);

  if (mqtt.connect(cluster_id, MQTT_USER, MQTT_PASS, lwt_topic, 1, true, lwt_msg)) {
    Serial.println("[MQTT] Connected");
    mqtt.subscribe(topic_cmd, 1);
    mqtt.subscribe(topic_broadcast, 1);
    Serial.printf("[MQTT] Subscribed to %s\n", topic_cmd);

    char online_msg[128];
    snprintf(online_msg, 128,
      "{\"cluster_id\":\"%s\",\"online\":true,\"firmware\":\"%s\",\"ip\":\"%s\"}",
      cluster_id, FIRMWARE_VERSION, WiFi.localIP().toString().c_str());
    mqtt.publish(lwt_topic, online_msg, true);
  } else {
    Serial.printf("[MQTT] FAILED rc=%d\n", mqtt.state());
  }
}

// ═══════════════════════════════════════════════════════════
// SETUP + LOOP
// ═══════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.printf("\n\nPlantaOS RIR 2026 — Firmware v%s\nBuilt: %s\n",
    FIRMWARE_VERSION, FIRMWARE_BUILD_DATE);

  load_config();

  pinMode(IR1_ENT_INT, INPUT_PULLUP);
  pinMode(IR2_ENT_EXT, INPUT_PULLUP);
  pinMode(IR3_SAI_INT, INPUT_PULLUP);
  pinMode(IR4_SAI_EXT, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(IR1_ENT_INT), isr_ir1, FALLING);
  attachInterrupt(digitalPinToInterrupt(IR2_ENT_EXT), isr_ir2, FALLING);
  attachInterrupt(digitalPinToInterrupt(IR3_SAI_INT), isr_ir3, FALLING);
  attachInterrupt(digitalPinToInterrupt(IR4_SAI_EXT), isr_ir4, FALLING);

  connect_wifi();
  connect_mqtt();
  Serial.printf("[READY] %s online\n", cluster_id);
}

void loop() {
  if (!mqtt.connected()) {
    if (millis() - last_heartbeat > 5000) {
      connect_mqtt();
      last_heartbeat = millis();
    }
  } else {
    mqtt.loop();
  }

  if (WiFi.status() != WL_CONNECTED) connect_wifi();

  if (millis() - last_heartbeat > HEARTBEAT_MS) {
    last_heartbeat = millis();
    publish_status();
    if (serial_stream_enabled) {
      char line[200];
      snprintf(line, 200, "[HEARTBEAT] occ=%d · entradas=%d · rssi=%d · heap=%d",
        (int)ocupacao_ir, (int)entradas, (int)WiFi.RSSI(), (int)ESP.getFreeHeap());
      mqtt.publish(topic_serial, line);
    }
  }

  if (millis() - last_telemetry > post_interval_ms) {
    last_telemetry = millis();
    publish_telemetry();
  }

  delay(5);
}
