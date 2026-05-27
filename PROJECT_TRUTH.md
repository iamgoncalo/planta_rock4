# PlantaOS — Project Truth

Rock in Rio Lisboa 2026  
WC Occupancy Management System  
Last updated: 2026-05-27

Legend:
- [CONFIRMED_FROM_FILES] — verified by reading actual source files
- [REQUIRED_BY_USER] — explicitly stated in user requirements
- [SAFE_DEFAULT] — reasonable assumption not contradicted by any source
- [NOT_VERIFIED] — cannot confirm from available files
- [MISSING_DECISION] — decision has not been made yet

---

## Identity

| Key | Value | Source |
|-----|-------|--------|
| System name | PlantaOS | [CONFIRMED_FROM_FILES] app/main.py |
| Festival | Rock in Rio Lisboa 2026 | [CONFIRMED_FROM_FILES] app/main.py |
| Backend framework | FastAPI | [CONFIRMED_FROM_FILES] app/main.py |
| Language | Python 3.14 | [CONFIRMED_FROM_FILES] .venv/bin/python |
| App version | 0.1.0 | [CONFIRMED_FROM_FILES] app/config.py |

---

## Product

| Key | Value | Source |
|-----|-------|--------|
| Purpose | Real-time WC occupancy tracking and routing for festival attendees | [CONFIRMED_FROM_FILES] app/main.py |
| Audience | Festival ops team + TV screens + mobile app users | [REQUIRED_BY_USER] |
| Primary output | Routing recommendations + TV screen state + alerts | [CONFIRMED_FROM_FILES] app/routers/ |
| Simulation mode | Active by default (`simulation_active=True`) | [CONFIRMED_FROM_FILES] app/config.py |

---

## Codebases

| Path | Description | Source |
|------|-------------|--------|
| app/main.py | FastAPI app factory | [CONFIRMED_FROM_FILES] |
| app/config.py | Settings via pydantic-settings | [CONFIRMED_FROM_FILES] |
| app/models/ | Pydantic data models | [CONFIRMED_FROM_FILES] |
| app/routers/ | FastAPI route handlers | [CONFIRMED_FROM_FILES] |
| app/services/ | Business logic (state, fusion, routing, scor, simulation, chat) | [CONFIRMED_FROM_FILES] |
| app/services/scor.py | SCOR telemetry publisher (dry-run safe) | [CONFIRMED_FROM_FILES] |
| tests/ | pytest test suite | [CONFIRMED_FROM_FILES] |
| scripts/check_forbidden_terms.sh | Forbidden term guard | [CONFIRMED_FROM_FILES] |
| DATA_MODEL.md | Full data model reference | [CONFIRMED_FROM_FILES] |
| RUNBOOK_LOCAL.md | Local development runbook | [CONFIRMED_FROM_FILES] |

---

## Sections

| Key | Value | Source |
|-----|-------|--------|
| Total sections | 14 (exactly) | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| Unisex sections | WC-05, WC-06 | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| Gendered section pairs | WC-01, WC-02, WC-03, WC-04, WC-07, WC-08 (each has _M and _F) | [CONFIRMED_FROM_FILES] |
| Total clusters | 8 | [CONFIRMED_FROM_FILES] app/routers/clusters.py |
| WC-05 gender constraint | gender MUST be null — Pydantic model_validator enforces this | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| WC-06 gender constraint | gender MUST be null — Pydantic model_validator enforces this | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| Forbidden section IDs | WC-05_M, WC-05_F, WC-06_M, WC-06_F | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| WC-05 routing note | entry_only — +2.0 min walk penalty for routing | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |

Full section list: WC-01_M, WC-01_F, WC-02_M, WC-02_F, WC-03_M, WC-03_F, WC-04_M, WC-04_F, WC-05, WC-06, WC-07_M, WC-07_F, WC-08_M, WC-08_F

---

## Forbidden

| Rule | Detail | Source |
|------|--------|--------|
| No GPS in telemetry | GPS coordinates are static metadata loaded once — never in recurring payloads | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| No CO2 | No co2, co2_ppm fields anywhere | [REQUIRED_BY_USER] |
| No temperature | No temperature/temperatura fields anywhere | [REQUIRED_BY_USER] |
| No humidity | No humidity/humidade fields anywhere | [REQUIRED_BY_USER] |
| No MAC storage | WiFiAggregateReading has no mac_address field | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| No red #FF0000 | Critical alerts use #C25A1A (amber/orange) | [REQUIRED_BY_USER] |
| No #EF4444 | Tailwind red-500 is forbidden | [REQUIRED_BY_USER] |
| No Deucalion | Brand/naming constraint | [REQUIRED_BY_USER] |
| Simulated flag | All simulated data must have simulated=True | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |

---

## SCOR Tokens

| Token | Env Var | Notes | Source |
|-------|---------|-------|--------|
| KPI token | SCOR_TOKEN_KPI | Read from env only — never hardcoded | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| Cluster token | SCOR_TOKEN_CLUSTER | Read from env only — never hardcoded | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| Base URL | SCOR_BASE_URL | Read from env only — never hardcoded | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |

Note: app/config.py has `scor_token` and `scor_endpoint` as legacy fields. The new SCOR service (app/services/scor.py) reads the three required env vars directly via `os.environ.get()`.

---

## Routing Cost Equation

```
total_cost = walk_time_min
           + queue_wait_min
           + congestion_penalty
           + show_surge_penalty
           + confidence_penalty
           + safety_penalty
```

| Component | Formula | Max |
|-----------|---------|-----|
| congestion_penalty | (ocupacao_pct / 100) * 3.0 | 3.0 min |
| confidence_penalty | (1 - confidence) * 2.0 | 2.0 min |
| safety_penalty (critical) | 10.0 | 10.0 min |
| safety_penalty (offline) | 5.0 | 5.0 min |
| safety_penalty (normal) | 0.0 | 0.0 min |
| show_surge_penalty | ShowImpact.surge_penalty_min (if section affected) | varies |
| WC-05 walk penalty | +2.0 min (entry_only back-up risk) | 2.0 min |

Rules: [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] app/services/routing.py

**Avoidance rules:**
- Never recommend critical WC when non-critical alternatives exist [CONFIRMED_FROM_FILES]
- Never recommend offline WC when online alternatives exist [CONFIRMED_FROM_FILES]

---

## Fusion Weights

| Sensor | Weight | Source |
|--------|--------|--------|
| IR (entry − exit net flow) | 0.50 | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| WiFi aggregate | 0.30 | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |
| Camera ML | 0.20 | [REQUIRED_BY_USER] [CONFIRMED_FROM_FILES] |

Rules:
- Weights redistribute proportionally when sensors missing [CONFIRMED_FROM_FILES]
- Returns (0.0, 0.0, ["all_sensors_missing"]) when all sensors absent [CONFIRMED_FROM_FILES]
- Never returns negative occupancy delta [CONFIRMED_FROM_FILES]
- Disagreement > 30% reduces confidence by 25% [CONFIRMED_FROM_FILES]

---

## Deployment Targets

| Target | Status | Notes |
|--------|--------|-------|
| Local dev | Working | uvicorn on port 8000 |
| Vercel preview | [MISSING_DECISION] | Not configured in repo |
| Vercel production | [MISSING_DECISION] | Not configured in repo |
| Database | SQLite (phase 0) | [CONFIRMED_FROM_FILES] app/config.py |

---

## Status Board

| Component | Status | Tests | Notes |
|-----------|--------|-------|-------|
| 14 sections | CONFIRMED | test_invariants.py | Exact list locked |
| WC-05/06 unisex validator | CONFIRMED | test_invariants.py | Pydantic enforces |
| Sensor fusion | CONFIRMED | test_fusion.py | Weights correct |
| Routing engine | CONFIRMED | test_routing.py | Cost formula correct, WC-05 +2.0 added |
| /api/v1/health | CONFIRMED | test_endpoints_complete.py | Returns {status,version,simulation,ts} |
| /api/v1/state | CONFIRMED | test_api.py | 14 sections + KPIs |
| /api/v1/clusters | CONFIRMED | test_api.py | 8 clusters |
| /api/v1/kpis | CONFIRMED | test_api.py | avg_ocupacao_pct in [0,100] |
| /api/v1/alerts | CONFIRMED | test_api.py | List of Alert objects |
| /api/v1/sensors | CONFIRMED | test_api.py | 8 SensorHealth entries |
| /api/v1/tv/{id} | CONFIRMED | test_api.py | TVScreenState |
| /api/v1/route | CONFIRMED | test_api.py | BathroomRouteDecision |
| /api/v1/chat | CONFIRMED | test_api.py | ChatResponse |
| /api/v1/simulate/tick | CONFIRMED | test_api.py | Scenario advance |
| /api/v1/scor/dry-run | CONFIRMED | test_scor.py | 14 entries, no GPS, no CO2 |
| /api/v1/ws WebSocket | CONFIRMED | test_endpoints_complete.py | LivePayload JSON stream |
| SCOR publisher service | CONFIRMED | test_scor.py | Dry-run safe, no forbidden fields |
| Forbidden terms guard | CONFIRMED | scripts/check_forbidden_terms.sh | Exit 0 (clean) |
| DATA_MODEL.md | CONFIRMED | — | All structures documented |
| RUNBOOK_LOCAL.md | CONFIRMED | — | Copy-pasteable commands |
| Critical colour | #C25A1A | [REQUIRED_BY_USER] | NOT #FF0000, NOT #EF4444 |
| Total tests | 314 passing | — | 0 failures |
