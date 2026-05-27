# PlantaOS — Data Model Reference

Rock in Rio Lisboa 2026 — WC Occupancy Management  
Version: 0.1.0 | Last updated: 2026-05-27

---

## FestivalState

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| sections | list[SectionState] | len == 14 | All 14 fixed WC sections |
| kpis | GlobalKPIs | required | Computed from sections |
| alerts | list[Alert] | required | Active unacknowledged alerts |
| last_tick_age_s | float | >= 0 | Seconds since last simulation/sensor tick |
| any_simulated | bool | required | True if any section is simulated |

---

## Cluster

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| cluster_id | str | one of 8 WC cluster IDs | e.g. "WC-01" through "WC-08" |
| unisex | bool | required | True for WC-05 and WC-06 |
| sections | list[ClusterSection] | len 1–2 | Unisex clusters have 1 section |
| summary | ClusterSummary | required | Aggregated occupancy/status |

---

## ClusterSection

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| section_id | str | in SECTION_IDS | One of the 14 fixed section IDs |
| ocupacao_pct | float | [0, 100] | Current occupancy percentage |
| fila_atual | int | >= 0 | Current queue length (people) |
| tempo_espera_min | float | >= 0 | Estimated wait time in minutes |
| status | SectionStatus | normal/warning/critical/offline | Derived from ocupacao_pct |
| simulated | bool | required | True when data is simulated |

---

## SectionState

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| section_id | str | in SECTION_IDS | Must be one of 14 fixed IDs |
| ocupacao_pct | float | [0, 100] | Occupancy percentage |
| fila_atual | int | >= 0 | Queue length |
| tempo_espera_min | float | >= 0 | Wait time in minutes |
| fluxo_entrada_pmin | float | >= 0 | Entry flow per minute |
| status | SectionStatus | normal/warning/critical/offline | Auto-derived |
| simulated | bool | default True | Always True for simulated data |
| gender | Optional[Literal["M","F"]] | MUST be null for WC-05 and WC-06 | Unisex sections reject gender |

**Constraints:**
- WC-05 and WC-06: `gender` MUST be `null`. Pydantic model_validator rejects any non-null value.
- `ocupacao_pct` is clamped to [0, 100].
- `section_id` is validated against the fixed 14-section tuple. Unknown IDs raise `ValidationError`.

---

## SensorReading

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| source_id | str | required | Unique sensor identifier |
| source_type | SensorSourceType | ir/wifi/camera/lorawan/manual | Enum |
| ts | float | Unix epoch seconds | Timestamp |
| value | float | required | Raw sensor value |
| confidence | float | [0, 1] | Fused confidence score |
| simulated | bool | default True | Always True when simulated |

---

## IRReading

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| source_id | str | required | e.g. "IR-WC01-ENTRY" |
| ts | float | Unix epoch seconds | Timestamp |
| count | int | >= 0 | People count in direction |
| direction | Literal["in","out"] | required | Beam direction |
| confidence | float | [0, 1] | Sensor confidence |
| simulated | bool | required | True when simulated |

---

## WiFiAggregateReading

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| source_id | str | required | Probe source identifier |
| ts | float | Unix epoch seconds | Timestamp |
| devices_raw | int | >= 0 | Raw probe count |
| people_estimate | int | >= 0 | Estimated unique people |
| calibration_factor | float | default 2.5 | Devices-to-people divisor |
| simulated | bool | required | True when simulated |

**No `mac_address` field. No individual device tracking. Aggregate counts only.**

---

## CameraMLReading

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| source_id | str | required | Camera identifier |
| ts | float | Unix epoch seconds | Timestamp |
| count | int | >= 0 | ML headcount estimate |
| confidence | float | [0, 1] | ML model confidence |
| zone | str | required | Zone label (e.g. "entry", "queue") |
| simulated | bool | required | True when simulated |

---

## LoRaWANPacket

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| device_id | str | required | LoRaWAN device EUI |
| last_seen_ts | Optional[float] | nullable | Unix epoch seconds |
| available | bool | required | Device reachable |
| last_packet | Optional[str] | nullable | Last raw packet hex or base64 |

---

## SensorHealth

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| cluster_id | str | one of 8 cluster IDs | e.g. "WC-01" |
| lilygo_online | bool | required | LilyGO device responding |
| lilygo_last_seen | Optional[float] | nullable | Unix epoch seconds |
| ir_entry_online | bool | required | IR entry beam online |
| ir_exit_online | bool | required | IR exit beam online |
| wifi_online | bool | required | WiFi probe scanner online |
| camera_online | bool | required | Camera ML pipeline online |
| lorawan_available | bool | required | LoRaWAN channel reachable |
| active_sources | list[str] | required | Names of active sensor sources |
| confidence | float | [0, 1] | Aggregate cluster confidence |
| issues | list[str] | required | List of issue codes |
| last_update_ts | float | Unix epoch seconds | Last update timestamp |
| simulated | bool | required | True when simulated |

---

## DeviceHealth

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| device_id | str | required | Unique device identifier |
| device_type | str | required | e.g. "lilygo_t3s3", "ir_beam" |
| online | bool | required | Device reachable |
| last_seen_ts | Optional[float] | nullable | Unix epoch seconds |
| uptime_s | Optional[float] | nullable | Uptime in seconds |
| packet_status | Optional[str] | nullable | Latest packet status code |

---

## RouteGraph

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| nodes | list[RouteNode] | required | All reachable WC nodes |
| edges | list[RouteEdge] | required | Walking connections between nodes |

---

## RouteNode

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| node_id | str | required | Unique node identifier |
| section_id | str | in SECTION_IDS | Linked WC section |
| walk_time_from_user_min | float | >= 0 | Walking time from user position |
| gps_lat | float | required | Cluster centroid latitude (static metadata) |
| gps_lon | float | required | Cluster centroid longitude (static metadata) |

---

## RouteEdge

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| from_node | str | required | Source node_id |
| to_node | str | required | Destination node_id |
| walk_time_min | float | >= 0 | Walking time along edge |

---

## BathroomRouteDecision

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| recommended | RouteOption | required | Best-cost option |
| alternatives | list[RouteOption] | len >= 2 | At least 2 alternatives returned |
| all_critical | bool | required | True when every section is critical/offline |
| any_simulated | bool | required | True when any option uses simulated data |
| ts | float | Unix epoch seconds | Decision timestamp |

---

## RouteOption

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| section_id | str | in SECTION_IDS | Target section |
| walk_time_min | float | >= 0 | Walking time in minutes |
| queue_wait_min | float | >= 0 | Queue wait time in minutes |
| total_cost_min | float | >= 0 | Sum of all penalties (see formula below) |
| confidence | float | [0, 1] | Routing confidence |
| avoidance_reasons | list[AvoidanceReason] | required | Reasons to avoid (may be empty) |
| simulated | bool | required | True when section data is simulated |

**Cost formula:**
```
total_cost = walk_time_min + queue_wait_min + congestion_penalty
           + show_surge_penalty + confidence_penalty + safety_penalty

congestion_penalty   = (ocupacao_pct / 100) * 3.0          (max 3.0 min)
confidence_penalty   = (1 - confidence) * 2.0
safety_penalty       = 10.0 if critical, 5.0 if offline, 0.0 otherwise
show_surge_penalty   = ShowImpact.surge_penalty_min if section affected by active show
```

WC-05 (entry_only): +2.0 min added to walk_time for routing (traffic back-up risk).

---

## AvoidanceReason

Literal enum: `"critical"` | `"offline"` | `"low_confidence"` | `"surge"` | `"full"`

---

## GlobalKPIs

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| avg_ocupacao_pct | float | [0, 100] | Average occupancy across 14 sections |
| total_fila | int | >= 0 | Sum of all queue lengths |
| critical_sections | int | >= 0 | Count of sections at critical status |
| redirected_count | int | >= 0 | Count of sections being redirected |
| any_simulated | bool | required | True when any section is simulated |

---

## Show

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| show_id | str | required | Unique show identifier |
| name | str | required | Artist/show name |
| stage | str | required | Stage name (e.g. "Palco Mundo") |
| start_iso | str | ISO 8601 datetime | Show start time with TZ |
| end_iso | str | ISO 8601 datetime | Show end time with TZ |
| headliner | bool | required | True if headliner slot |
| expected_surge_pct | float | [0, 100] | Expected crowd surge percentage |

---

## ShowImpactModel

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| show_id | str | required | References Show.show_id |
| affected_sections | list[str] | subset of SECTION_IDS | Sections impacted by surge |
| surge_penalty_min | float | >= 0 | Routing penalty in minutes during surge |

---

## Alert

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| alert_id | str | required | Unique alert identifier |
| severity | AlertSeverity | info/warning/critical | Alert severity level |
| section_id | Optional[str] | nullable | Related section, if applicable |
| message | str | required | Human-readable alert message |
| ts | float | Unix epoch seconds | Alert creation timestamp |
| acknowledged | bool | default False | Whether alert has been acknowledged |

**Critical colour code: `#C25A1A` (amber/orange) — NOT red, NOT `#FF0000`.**

---

## TVScreenState

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| screen_id | str | required | Screen identifier (e.g. "TV-PALCO-MUNDO-EAST") |
| recommended_section | str | in SECTION_IDS | Best available section |
| direction | str | required | Human-readable direction text (Portuguese) |
| walk_time_min | float | >= 0 | Walk time to recommended section |
| queue_wait_min | float | >= 0 | Queue wait at recommended section |
| alternative_section | Optional[str] | nullable | Backup section if recommended fills |
| avoid_list | list[str] | required | Section IDs to avoid (critical/offline) |
| critical_override | bool | required | True when all sections are critical |
| last_update_ts | float | Unix epoch seconds | Last screen update |
| any_simulated | bool | required | True when data is simulated |

---

## LivePayload

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| kpis | GlobalKPIs | required | Festival-wide KPIs |
| sections | list[SectionState] | len == 14 | All 14 section states |
| alerts | list[str] | required | Active alert messages (not acknowledged) |
| last_tick_age_s | float | >= 0 | Seconds since last tick |
| any_simulated | bool | required | True when any section is simulated |

---

## ChatContext

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| live_payload | Optional[Any] | nullable | Current LivePayload snapshot |
| active_show | Optional[Any] | nullable | Currently active Show, if any |
| route_decision | Optional[Any] | nullable | Most recent routing decision |

---

## DeploymentStatus

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| environment | str | required | e.g. "preview", "production" |
| url | str | required | Deployment URL |
| status | str | required | "ok", "error", "building" |
| deployed_at | str | ISO 8601 datetime | Deployment timestamp |
| git_sha | str | required | Git commit SHA |

---

## ScorTelemetryPayload

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| cluster_id | str | one of 8 cluster IDs | e.g. "WC-01" |
| fila_actual | int | >= 0 | Current queue length |
| tempo_espera_min | float | >= 0 | Wait time in minutes |
| fluxo_entrada_pmin | float | >= 0 | Entry flow per minute |
| ocupacao_pct | float | [0, 100] | Occupancy percentage |

**SCOR payload constraints (non-negotiable):**
- Exactly these 5 fields — no GPS, no CO2, no temperature, no humidity.
- GPS coordinates are STATIC metadata loaded once at startup — never in recurring telemetry.
- Exactly 14 rows per publish call (one per section).
- Never sends gendered variants of unisex sections: WC-05_M, WC-05_F, WC-06_M, WC-06_F are forbidden cluster_ids.
- Tokens read from environment only: `SCOR_TOKEN_KPI`, `SCOR_TOKEN_CLUSTER`, `SCOR_BASE_URL`.

---

## PublicAppSession

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| session_id | str | UUID | Unique session identifier |
| user_lat | Optional[float] | nullable | User latitude (ephemeral, not stored) |
| user_lon | Optional[float] | nullable | User longitude (ephemeral, not stored) |
| preferred_gender | Optional[Literal["M","F"]] | nullable | User preference for M/F section |
| created_ts | float | Unix epoch seconds | Session creation time |
| last_active_ts | float | Unix epoch seconds | Last activity time |

**Privacy:** GPS coordinates are ephemeral per request — never persisted. No MAC address storage.

---

## Fusion Weights

| Sensor | Weight | Notes |
|--------|--------|-------|
| IR (entry − exit) | 0.50 | Highest weight — most reliable |
| WiFi aggregate | 0.30 | Medium weight |
| Camera ML | 0.20 | Lowest weight |

Weights are redistributed proportionally when sensors are missing. When all sensors are absent, returns `(0.0, 0.0, ["all_sensors_missing"])`. Confidence is reduced by 25% when sensor disagreement exceeds 30%.

---

## Section ID Reference

| Section ID | Type | Gender |
|-----------|------|--------|
| WC-01_M | Gendered | Male |
| WC-01_F | Gendered | Female |
| WC-02_M | Gendered | Male |
| WC-02_F | Gendered | Female |
| WC-03_M | Gendered | Male |
| WC-03_F | Gendered | Female |
| WC-04_M | Gendered | Male |
| WC-04_F | Gendered | Female |
| WC-05 | UNISEX | null (mandatory) |
| WC-06 | UNISEX | null (mandatory) |
| WC-07_M | Gendered | Male |
| WC-07_F | Gendered | Female |
| WC-08_M | Gendered | Male |
| WC-08_F | Gendered | Female |
