"""Tests 20-30: API endpoint contracts using AsyncClient + ASGITransport."""
from __future__ import annotations

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
# Test 20 — GET /api/v1/health → 200, {status: "ok"}
#   The app mounts health at /health and /v1/health (no /api prefix on health).
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health is served at /v1/health (canonical versioned path)."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_bare_path(client: AsyncClient):
    """The /health shortcut also works."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Test 21 — GET /api/v1/state → 200, valid LivePayload shape
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_state_endpoint_200(client: AsyncClient):
    response = await client.get("/api/v1/state")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_state_endpoint_has_live_payload_shape(client: AsyncClient):
    response = await client.get("/api/v1/state")
    data = response.json()
    assert "sections" in data
    assert "kpis" in data
    assert "any_simulated" in data


@pytest.mark.asyncio
async def test_state_sections_have_section_ids(client: AsyncClient):
    response = await client.get("/api/v1/state")
    data = response.json()
    returned_ids = {s["section_id"] for s in data["sections"]}
    for sid in returned_ids:
        assert sid in SECTION_IDS, f"Unknown section_id '{sid}' in state response"


# ---------------------------------------------------------------------------
# Test 22 — GET /api/v1/clusters → 200, 8 clusters
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_clusters_endpoint_200(client: AsyncClient):
    response = await client.get("/api/v1/clusters")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clusters_endpoint_returns_8_clusters(client: AsyncClient):
    response = await client.get("/api/v1/clusters")
    data = response.json()
    assert "clusters" in data
    assert len(data["clusters"]) == 8, (
        f"Expected 8 clusters, got {len(data['clusters'])}"
    )


@pytest.mark.asyncio
async def test_clusters_total_count_field(client: AsyncClient):
    response = await client.get("/api/v1/clusters")
    data = response.json()
    assert data.get("total_clusters") == 8


# ---------------------------------------------------------------------------
# Test 23 — GET /api/v1/kpis → 200, avg_ocupacao_pct in [0, 100]
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_kpis_endpoint_200(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_kpis_avg_ocupacao_in_range(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    data = response.json()
    avg = data["avg_ocupacao_pct"]
    assert 0.0 <= avg <= 100.0, f"avg_ocupacao_pct={avg} out of [0,100]"


@pytest.mark.asyncio
async def test_kpis_required_fields(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    data = response.json()
    assert "avg_ocupacao_pct" in data
    assert "total_fila" in data
    assert "critical_sections" in data


# ---------------------------------------------------------------------------
# Test 24 — GET /api/v1/shows → 200, list
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_shows_endpoint_200(client: AsyncClient):
    response = await client.get("/api/v1/shows")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_shows_endpoint_returns_shows_list(client: AsyncClient):
    """Shows endpoint returns a dict with a 'shows' list (includes active_show metadata)."""
    response = await client.get("/api/v1/shows")
    data = response.json()
    # The endpoint wraps shows in a dict: {"shows": [...], "active_show": ..., "total_shows": N}
    assert "shows" in data, f"Expected 'shows' key in response, got keys: {list(data.keys())}"
    assert isinstance(data["shows"], list), "shows must be a list"


@pytest.mark.asyncio
async def test_shows_endpoint_not_empty(client: AsyncClient):
    response = await client.get("/api/v1/shows")
    data = response.json()
    shows = data.get("shows") if isinstance(data, dict) else data
    assert len(shows) > 0, "Shows list must not be empty"


# ---------------------------------------------------------------------------
# Test 25 — GET /api/v1/sensors → 200, 8 sensor health entries
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sensors_endpoint_200(client: AsyncClient):
    response = await client.get("/api/v1/sensors")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sensors_endpoint_returns_8_entries(client: AsyncClient):
    response = await client.get("/api/v1/sensors")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 34  # 34 LilyGo + 6 Luxonis + 8 Prosegur + 2 gateways = 50, f"Expected 8 sensor health entries, got {len(data)}"


@pytest.mark.asyncio
async def test_sensors_entries_have_cluster_id(client: AsyncClient):
    response = await client.get("/api/v1/sensors")
    data = response.json()
    for entry in data:
        assert "cluster_id" in entry
        cid = entry.get("cluster_id")
        if cid is not None:
            assert cid.upper().startswith("WC-")


# ---------------------------------------------------------------------------
# Test 26 — GET /api/v1/alerts → 200, list
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_alerts_endpoint_200(client: AsyncClient):
    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_alerts_endpoint_returns_list(client: AsyncClient):
    response = await client.get("/api/v1/alerts")
    data = response.json()
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"


# ---------------------------------------------------------------------------
# Test 27 — GET /api/v1/tv/screen-01 → 200, TVScreenState
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tv_endpoint_200(client: AsyncClient):
    response = await client.get("/api/v1/tv/screen-01")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tv_endpoint_shape(client: AsyncClient):
    response = await client.get("/api/v1/tv/screen-01")
    data = response.json()
    assert "screen_id" in data
    assert "recommended_section" in data
    assert "direction" in data
    assert "walk_time_min" in data
    assert "queue_wait_min" in data


@pytest.mark.asyncio
async def test_tv_recommended_section_is_valid(client: AsyncClient):
    response = await client.get("/api/v1/tv/screen-01")
    data = response.json()
    rec = data["recommended_section"]
    assert rec in SECTION_IDS, f"TV recommended section '{rec}' not in SECTION_IDS"


@pytest.mark.asyncio
async def test_tv_screen_id_matches_request(client: AsyncClient):
    response = await client.get("/api/v1/tv/screen-42")
    data = response.json()
    assert data["screen_id"] == "screen-42"


# ---------------------------------------------------------------------------
# Test 28 — POST /api/v1/simulate/tick with {"scenario":"normal"} → 200
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_simulate_tick_normal_200(client: AsyncClient):
    response = await client.post("/api/v1/simulate/tick", json={"scenario": "normal"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_simulate_tick_response_shape(client: AsyncClient):
    response = await client.post("/api/v1/simulate/tick", json={"scenario": "normal"})
    data = response.json()
    assert "scenario" in data
    assert "tick" in data
    assert "sections_count" in data
    assert data["sections_count"] == 14


@pytest.mark.asyncio
async def test_simulate_tick_invalid_scenario_returns_400(client: AsyncClient):
    response = await client.post("/api/v1/simulate/tick", json={"scenario": "nonexistent_scenario"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test 29 — POST /api/v1/route → 200, recommended section in SECTION_IDS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_route_endpoint_200(client: AsyncClient):
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.782, "user_lon": -9.093}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_route_recommended_section_in_section_ids(client: AsyncClient):
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.782, "user_lon": -9.093}
    )
    data = response.json()
    rec_id = data["recommended"]["section_id"]
    assert rec_id in SECTION_IDS, f"Recommended section '{rec_id}' not in SECTION_IDS"


@pytest.mark.asyncio
async def test_route_response_shape(client: AsyncClient):
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.782, "user_lon": -9.093}
    )
    data = response.json()
    assert "recommended" in data
    assert "alternatives" in data
    assert "all_critical" in data
    assert "any_simulated" in data


@pytest.mark.asyncio
async def test_route_different_position(client: AsyncClient):
    """Routing should succeed for any valid GPS coordinates."""
    response = await client.post(
        "/api/v1/route", json={"user_lat": 38.790, "user_lon": -9.100}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommended"]["section_id"] in SECTION_IDS


# ---------------------------------------------------------------------------
# Test 30 — POST /api/v1/chat → 200, ChatResponse
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_chat_endpoint_200(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat", json={"message": "Qual é a melhor WC?"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_response_shape(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat", json={"message": "Qual é a melhor WC?"}
    )
    data = response.json()
    assert "reply" in data
    assert "grounded" in data
    assert "live_data_available" in data
    assert "ts" in data


@pytest.mark.asyncio
async def test_chat_reply_is_nonempty_string(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat", json={"message": "Qual é a melhor WC?"}
    )
    data = response.json()
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0


@pytest.mark.asyncio
async def test_chat_english_query(client: AsyncClient):
    response = await client.post(
        "/api/v1/chat", json={"message": "Which bathroom is available?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["live_data_available"] is True
