# SENSORS.md

> Como funcionam os **62 dispositivos físicos** do PlantaOS no Parque Tejo.

---

## 1. Inventário total

| # | Tipo | Modelo | Função | Protocolo | Custo unit. |
|---|---|---|---|---|---|
| 16 | **IR** | Arduino ESP32 + E18-D80NK | Contar pessoas (entrada/saída) | LoRaWAN 868MHz | €6 |
| 11 | **WiFi AP** | TP-Link EAP670 WiFi 6E | Densidade agregada anónima | PoE → Ethernet | €240 |
| 5 | **Câmara** | Luxonis OAK-D Lite | Edge ML (sem rosto, sem MAC) | Ethernet | €180 |
| 2 | **Gateway** | Dragino DLOS8 | LoRaWAN concentrator (norte+sul) | Ethernet | €420 |
| 2 | **Hub 4G** | LilyGo T-SIM7000G | Uplink NOS + Vodafone failover | 4G LTE | €60 |
| 2 | **Edge** | Raspberry Pi 5 | MQTT broker local + cache | Ethernet | €110 |
| 24 | **Reed** | MC-38 + ESP32 | Estado de portas (abertas/fechadas) | LoRaWAN | €3 |
| **62** | **TOTAL** | | | | |

---

## 2. Distribuição por cluster

| Cluster | IR | WiFi | Câmara | Reed | Total local |
|---|---|---|---|---|---|
| WC-01 | 2 | 1 | — | 4 | 7 |
| WC-02 | 2 | 1 | 1 | 4 | 8 |
| WC-03 | 2 | 1 | — | 4 | 7 |
| WC-04 | 2 | 1 | — | 2 | 5 |
| WC-05 (UNISSEX) | 2 | 1 | 1 | — | 4 |
| WC-06 (UNISSEX) | 2 | 1 | 1 | — | 4 |
| WC-07 | 2 | 1 | 1 | 6 | 10 |
| WC-08 | 2 | 1 | 1 | 4 | 8 |
| **Infra** (gateways/hubs/edge) | — | 3 | — | — | 6 |
| **TOTAL** | **16** | **11** | **5** | **24** | **62** |

---

## 3. Identificação

Esquema de IDs:
```
{cluster}-{tipo}{n}
```

Exemplos:
- `WC-03-IR1` — IR #1 do WC-03
- `WC-06-CAM1` — câmara do WC-06
- `WC-07-REED3` — reed switch da porta 3 do WC-07
- `GW-N` — gateway LoRa norte
- `GW-S` — gateway LoRa sul
- `HUB-NOS` — hub 4G NOS
- `HUB-VOD` — hub 4G Vodafone
- `EDGE-1`, `EDGE-2` — edge Raspberry Pi

---

## 4. Esquema de payload

```json
{
  "id": "WC-03-IR1",
  "type": "ir",
  "cluster_id": "WC-03",
  "position": { "x_m": 280, "y_m": 80 },
  "status": "online",
  "device_model": "Arduino ESP32 + E18-D80NK",
  "protocol": "LoRaWAN 868MHz",
  "firmware_version": "ESP-IR 1.4.2",
  "gateway_id": "GW-N",
  "cost_eur": 6,
  "fusion_weight": 0.50,
  "telemetry": {
    "battery_pct": 87,
    "signal_dbm": -68,
    "last_seen_s": 3,
    "live_count_per_min": 47,
    "maintenance_due_days": 94
  },
  "created_at": "2026-04-15T09:12:00Z",
  "updated_at": "2026-05-28T14:23:11Z"
}
```

Tipos válidos: `ir`, `wifi`, `cam`, `lora`, `hub`, `reed`.

**Campos de telemetria são específicos do tipo** — usar `telemetry` como
mapa tipado por discriminator. Validação Pydantic v2 no backend.

---

## 5. Status do dispositivo

Estados permitidos:
- `online` — a reportar dentro do limite
- `degraded` — `last_seen_s > 300` (5 min)
- `maintenance` — marcado manualmente até timestamp
- `offline` — `last_seen_s > 1800` (30 min)

Transições automáticas:
- `online → degraded` se `last_seen_s > 300`
- `degraded → offline` se `last_seen_s > 1800`

Todas as outras transições requerem endpoint explícito.

---

## 6. Fusão sensorial

Para cada cluster, ocupação é calculada como média ponderada com pesos
**fixos** (não treinados, intencionalmente simples):

```python
ocupacao_cluster = sum(obs_i * peso_i * disp_i for i in sensors)
                 / sum(peso_i * disp_i for i in sensors)
```

| Tipo | Peso | Justificação |
|---|---|---|
| **IR** | 0.50 | Mais barato, mais robusto, contagem directa |
| **WiFi aggregate** | 0.30 | Indirecto (densidade) mas mais cobertura espacial |
| **Câmara edge** | 0.20 | Mais preciso mas instala-se em menos sítios |

### Quando um sensor cai

Se `IR1` está offline, o seu peso (0.50) é **redistribuído**:
```
novo_peso(WiFi) = 0.30 + 0.30 * 0.50 = 0.45
novo_peso(Cam)  = 0.20 + 0.20 * 0.50 = 0.30
soma            = 0.75   → renormalizar para 1.0
```

Se o cluster perde **>60%** do peso disponível, a observação fica
`low_confidence` e a UI mostra-o em amber `#C25A1A`.

### Regras invioláveis

- ❌ **Nunca dividir por zero.** Se `Σ peso_i × disp_i == 0`, devolver
  `{value: null, confidence: 0}`.
- ❌ **Nunca extrapolar** sem dados. Mostrar "—" ou último valor com timestamp.
- ✅ **Sempre mostrar confiança** ao utilizador (badge ou opacidade).

---

## 7. Camadas de redundância

| Camada | Primário | Failover 1 | Failover 2 |
|---|---|---|---|
| Detecção de pessoas | IR | WiFi aggregate | Câmara edge ML |
| Sensor → gateway | LoRaWAN GW-N | LoRaWAN GW-S | WiFi via AP local |
| Edge → cloud | 4G NOS (HUB-NOS) | 4G Vodafone (HUB-VOD) | Ethernet via venue |
| Edge compute | EDGE-1 (RPi 5) | EDGE-2 (RPi 5 hot standby) | — |

---

## 8. Cobertura por cluster

Calculada como média ponderada pelos pesos de fusão, normalizada e
descontada por sensores offline:

```python
coverage_pct = (
    (ir_active / ir_total) * 0.50 +
    (wifi_active / wifi_total) * 0.30 +
    (cam_active / cam_total) * 0.20
) * 100
```

Resultado em `GET /api/v1/coverage`:
```json
{
  "cluster_id": "WC-05",
  "score_pct": 67,
  "by_source": { "ir": 50, "wifi": 80, "cam": 100 },
  "gaps": [
    { "x_m": 445, "y_m": 200, "rationale": "sub-cobertura IR no lado sul" }
  ]
}
```

---

## 9. Sistema de coordenadas

Origem: **canto SW do perímetro festivaleiro** (consistente com
`LX26_IMPLANTAC_A_O_GERAL_R0824032026GERAL_SM.pdf`).

Eixos:
- `x_m` — metros para Este
- `y_m` — metros para Norte

Sensores físicos têm GPS estático apenas para visualização. **Nunca**
aparece em telemetria ao vivo.

---

## 10. Instalação física (11–12 Junho 2026)

### Dia 11 (Quinta)
- Manhã: gateways GW-N, GW-S + hubs HUB-NOS, HUB-VOD
- Tarde: edge nodes EDGE-1, EDGE-2 + APs WiFi 6E
- Noite: testes de uplink NOS↔Vodafone failover

### Dia 12 (Sexta)
- Manhã: sensores IR em todos os clusters
- Tarde: câmaras Luxonis OAK-D + calibração ML
- Noite: reed switches nas portas + smoke test end-to-end

### Equipa
- **Flinotech (Francisco Lino)** — instalação física
- **Planta (Gonçalo + 1)** — configuração de software + smoke test
- **Rock World (Matheus)** — coordenação de acessos ao venue

### Após 12 Jun
- Rótulo `SIMULADO` substituído por `LIVE` na UI.
- Métricas Prometheus em `/metrics` activas.
- Dataset anónimo disponível para FCT.

---

## 11. RGPD

- ✅ Câmaras: edge ML, **rosto descartado em hardware**, só count de pessoas.
- ✅ WiFi: agregado anónimo, **MACs descartados** antes do upload.
- ✅ IR: zero PII por design (não vê, só conta).
- ✅ Reed: estado on/off, sem identificação.

Nada na base de dados liga uma observação a uma pessoa específica.

---

## 12. Manutenção e custos

| Item | Custo |
|---|---|
| 16 IR ESP32 | 16 × €6 = €96 |
| 11 APs WiFi 6E | 11 × €240 = €2 640 |
| 5 câmaras OAK-D Lite | 5 × €180 = €900 |
| 2 gateways LoRa | 2 × €420 = €840 |
| 2 hubs 4G | 2 × €60 = €120 |
| 2 edge RPi 5 | 2 × €110 = €220 |
| 24 reed switches | 24 × €3 = €72 |
| Cabos, suportes, caixas IP65 | ~€500 |
| **TOTAL hardware** | **~€5 388** |

Operação:
- 4G SIMs (NOS + Vodafone): €40/mês cada × 2 meses = €160
- Energia (PoE + UPS): incluído no venue
- Manutenção emergencial: pessoa de standby Junho 20–28

---

## 13. Roadmap de evolução

Pós-2026:
1. **MEMs sensors** baratos para densidade em massa.
2. **mmWave radar** em substituição parcial de câmaras (mais privacy-friendly).
3. **TinyML on-device** para classificação local de filas vs movimento.
4. **Federated learning** entre vários festivais sem upload de raw data.

---

## 14. Endpoints relevantes

```
GET    /api/v1/sensors                  # lista
GET    /api/v1/sensors/{id}             # detalhe + histórico 24h
POST   /api/v1/sensors                  # criar (suggest-placement antes)
PATCH  /api/v1/sensors/{id}             # actualizar
DELETE /api/v1/sensors/{id}             # soft delete

POST   /api/v1/sensors/{id}/calibrate   # → 202 + command_id
POST   /api/v1/sensors/{id}/restart     # via MQTT
POST   /api/v1/sensors/{id}/maintenance # marcar em manutenção

GET    /api/v1/sensors/suggest-placement?type=ir
GET    /api/v1/gateways
GET    /api/v1/topology
GET    /api/v1/coverage
GET    /api/v1/coverage/{cluster_id}
```

Auth via JWT bearer. Comandos hardware requerem role `ops`. Ver
[`ARCHITECTURE.md`](ARCHITECTURE.md) §9.
