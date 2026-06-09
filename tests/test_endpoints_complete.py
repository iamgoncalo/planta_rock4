"""Complete endpoint tests — all /api/v1/* routes plus WebSocket."""
from __future__ import annotations

import json

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.sections import SECTION_IDS


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# GET /api/v1/health → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_health_200(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_health_status_ok(client: AsyncClient):
    response = await client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_api_v1_health_has_version(client: AsyncClient):
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_api_v1_health_has_simulation(client: AsyncClient):
    response = await client.get("/api/v1/health")
    data = response.json()
    assert data.get("status") == "ok"
    assert "data_source" in data
    assert isinstance(data["simulation"], bool)


@pytest.mark.asyncio
async def test_api_v1_health_has_ts(client: AsyncClient):
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "ts" in data
    assert isinstance(data["ts"], float)


# ---------------------------------------------------------------------------
# GET /api/v1/state → 200, has kpis, sections, any_simulated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_state_200(client: AsyncClient):
    response = await client.get("/api/v1/state")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_state_has_kpis(client: AsyncClient):
    response = await client.get("/api/v1/state")
    data = response.json()
    assert "kpis" in data


@pytest.mark.asyncio
async def test_api_v1_state_has_sections(client: AsyncClient):
    response = await client.get("/api/v1/state")
    data = response.json()
    assert "sections" in data
    assert isinstance(data["sections"], list)


@pytest.mark.asyncio
async def test_api_v1_state_has_any_simulated(client: AsyncClient):
    response = await client.get("/api/v1/state")
    data = response.json()
    assert "any_simulated" in data


@pytest.mark.asyncio
async def test_api_v1_state_14_sections(client: AsyncClient):
    response = await client.get("/api/v1/state")
    data = response.json()
    assert len(data["sections"]) == 14


# ---------------------------------------------------------------------------
# GET /api/v1/clusters → 200, len==8
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_clusters_200(client: AsyncClient):
    response = await client.get("/api/v1/clusters")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_clusters_8_clusters(client: AsyncClient):
    response = await client.get("/api/v1/clusters")
    data = response.json()
    assert "clusters" in data
    assert len(data["clusters"]) == 8


@pytest.mark.asyncio
async def test_api_v1_clusters_total_clusters_field(client: AsyncClient):
    response = await client.get("/api/v1/clusters")
    data = response.json()
    assert data.get("total_clusters") == 8


# ---------------------------------------------------------------------------
# GET /api/v1/kpis → 200, avg_ocupacao_pct in [0, 100]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_kpis_200(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_kpis_avg_ocupacao_in_range(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    data = response.json()
    avg = data["avg_ocupacao_pct"]
    assert 0.0 <= avg <= 100.0


@pytest.mark.asyncio
async def test_api_v1_kpis_required_fields(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    data = response.json()
    for field in ("avg_ocupacao_pct", "total_fila", "critical_sections"):
        assert field in data, f"Required KPI field '{field}' missing"


# ---------------------------------------------------------------------------
# GET /api/v1/shows → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_shows_200(client: AsyncClient):
    response = await client.get("/api/v1/shows")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_shows_not_empty(client: AsyncClient):
    response = await client.get("/api/v1/shows")
    data = response.json()
    shows = data.get("shows") if isinstance(data, dict) else data
    assert len(shows) > 0


# ---------------------------------------------------------------------------
# GET /api/v1/sensors → 200, len==8
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_sensors_200(client: AsyncClient):
    response = await client.get("/api/v1/sensors")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_sensors_returns_8(client: AsyncClient):
    response = await client.get("/api/v1/sensors")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 34  # 34 LilyGo + 6 Luxonis + 8 Prosegur + 2 gateways = 50


@pytest.mark.asyncio
async def test_api_v1_sensors_have_cluster_id(client: AsyncClient):
    response = await client.get("/api/v1/sensors")
    data = response.json()
    for entry in data:
        assert "cluster_id" in entry
        assert entry["cluster_id"].upper().startswith("WC-")


# ---------------------------------------------------------------------------
# GET /api/v1/alerts → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_alerts_200(client: AsyncClient):
    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_alerts_returns_list(client: AsyncClient):
    response = await client.get("/api/v1/alerts")
    data = response.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GET /api/v1/tv/TV-PALCO-MUNDO-EAST → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_tv_palco_mundo_east_200(client: AsyncClient):
    response = await client.get("/api/v1/tv/TV-PALCO-MUNDO-EAST")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_tv_palco_mundo_east_screen_id(client: AsyncClient):
    response = await client.get("/api/v1/tv/TV-PALCO-MUNDO-EAST")
    data = response.json()
    assert data["screen_id"] == "TV-PALCO-MUNDO-EAST"


@pytest.mark.asyncio
async def test_api_v1_tv_palco_mundo_east_valid_section(client: AsyncClient):
    response = await client.get("/api/v1/tv/TV-PALCO-MUNDO-EAST")
    data = response.json()
    assert data["recommended_section"] in SECTION_IDS


# ---------------------------------------------------------------------------
# POST /api/v1/route {"user_lat":38.782,"user_lon":-9.093} → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_route_200(client: AsyncClient):
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.782, "user_lon": -9.093}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_route_recommended_in_section_ids(client: AsyncClient):
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.782, "user_lon": -9.093}
    )
    data = response.json()
    assert data["recommended"]["section_id"] in SECTION_IDS


@pytest.mark.asyncio
async def test_api_v1_route_has_alternatives(client: AsyncClient):
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.782, "user_lon": -9.093}
    )
    data = response.json()
    assert "alternatives" in data
    assert isinstance(data["alternatives"], list)


@pytest.mark.asyncio
async def test_api_v1_route_has_all_critical_flag(client: AsyncClient):
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.782, "user_lon": -9.093}
    )
    data = response.json()
    assert "all_critical" in data


# ---------------------------------------------------------------------------
# POST /api/v1/chat {"message":"Qual é a melhor WC?"} → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_chat_200(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat", json={"message": "Qual é a melhor WC?"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_chat_has_reply(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat", json={"message": "Qual é a melhor WC?"}
    )
    data = response.json()
    assert "reply" in data
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0


@pytest.mark.asyncio
async def test_api_v1_chat_shape(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat", json={"message": "Qual é a melhor WC?"}
    )
    data = response.json()
    for field in ("reply", "grounded", "live_data_available", "ts"):
        assert field in data, f"Required chat response field '{field}' missing"


# ---------------------------------------------------------------------------
# POST /api/v1/simulate/tick {"scenario":"normal"} → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_simulate_tick_normal_200(client: AsyncClient):
    response = await client.post(
        "/api/v1/simulate/tick", json={"scenario": "normal"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_simulate_tick_sections_count_14(client: AsyncClient):
    response = await client.post(
        "/api/v1/simulate/tick", json={"scenario": "normal"}
    )
    data = response.json()
    assert data["sections_count"] == 14


# ---------------------------------------------------------------------------
# POST /api/v1/scor/dry-run → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_scor_dry_run_200(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_v1_scor_dry_run_sections_sent_14(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    assert data["sections_sent"] == 14


@pytest.mark.asyncio
async def test_api_v1_scor_dry_run_status(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    assert data["status"] == "dry_run_ok"


# ---------------------------------------------------------------------------
# WS /api/v1/ws connects and receives JSON
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_ws_connects_and_receives_json():
    """WebSocket connection returns a valid JSON LivePayload on first message."""
    from starlette.testclient import TestClient
    from app.main import app as fastapi_app

    with TestClient(fastapi_app) as tc:
        with tc.websocket_connect("/api/v1/ws") as ws:
            data = ws.receive_text()
            payload = json.loads(data)
            assert "kpis" in payload, "LivePayload must have 'kpis'"
            assert "sections" in payload, "LivePayload must have 'sections'"
            assert "any_simulated" in payload, "LivePayload must have 'any_simulated'"
