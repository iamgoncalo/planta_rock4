# PlantaOS — Local Development Runbook

Rock in Rio Lisboa 2026 — WC Occupancy Management

---

## Install

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```

## Run Tests

```bash
pytest -q
```

## Verify Health

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{"status": "ok", "version": "0.1.0", "simulation": true, "ts": 1748390400.0}
```

## Kill Stray Process on :8000

```bash
lsof -ti :8000 | xargs kill -9
```

## Kill Stray Process on :8001

```bash
lsof -ti :8001 | xargs kill -9
```

## Reset Virtual Environment

```bash
rm -rf .venv && python -m venv .venv && pip install -r requirements.txt
```

## Run Forbidden Terms Check

```bash
bash scripts/check_forbidden_terms.sh
```

Exit code 0 means clean. Any output means a forbidden term was found in checked files.

---

## Quick Reference — Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | Health check |
| GET | /api/v1/state | Full live payload (14 sections + KPIs) |
| GET | /api/v1/clusters | 8 cluster summaries |
| GET | /api/v1/kpis | Festival-wide KPIs |
| GET | /api/v1/shows | Show schedule |
| GET | /api/v1/sensors | Sensor health for 8 clusters |
| GET | /api/v1/alerts | Active alerts |
| GET | /api/v1/tv/{screen_id} | TV screen state |
| POST | /api/v1/route | Routing decision (body: {user_lat, user_lon}) |
| POST | /api/v1/chat | Chat assistant (body: {message}) |
| POST | /api/v1/simulate/tick | Advance simulation tick (body: {scenario}) |
| POST | /api/v1/scor/dry-run | SCOR telemetry dry-run (14 sections) |
| WS | /api/v1/ws | Live WebSocket stream (5s interval) |
| GET | /docs | OpenAPI interactive docs |

---

## SCOR Dry-Run

```bash
curl -X POST http://localhost:8000/api/v1/scor/dry-run | python3 -m json.tool
```

Expected: `sections_sent: 14`, `gps_present: false`, `co2_present: false`, `status: "dry_run_ok"`
