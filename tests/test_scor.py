"""Tests for SCOR telemetry publisher service and endpoint."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.scor import build_scor_entries
from app.services.simulation import simulate_tick


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


def _make_sections():
    """Return 14 simulated SectionState objects for tick 0."""
    return simulate_tick("normal", 0)


# ---------------------------------------------------------------------------
# Test: SCOR dry-run returns exactly 14 sections
# ---------------------------------------------------------------------------

def test_scor_build_returns_exactly_14():
    sections = _make_sections()
    entries = build_scor_entries(sections)
    assert len(entries) == 14, f"Expected 14 SCOR entries, got {len(entries)}"


# ---------------------------------------------------------------------------
# Test: No GPS fields in SCOR payload
# ---------------------------------------------------------------------------

GPS_FIELDS = {"lat", "lon", "latitude", "longitude", "gps_lat", "gps_lon"}


def test_scor_no_gps_fields():
    sections = _make_sections()
    entries = build_scor_entries(sections)
    for entry in entries:
        for field in GPS_FIELDS:
            assert field not in entry, (
                f"Forbidden GPS field '{field}' found in SCOR entry: {entry}"
            )


# ---------------------------------------------------------------------------
# Test: No CO2 / environmental fields in SCOR payload
# ---------------------------------------------------------------------------

CO2_FIELDS = {"co2", "co2_ppm", "temperature", "temperatura", "humidity", "humidade"}


def test_scor_no_co2_fields():
    sections = _make_sections()
    entries = build_scor_entries(sections)
    for entry in entries:
        for field in CO2_FIELDS:
            assert field not in entry, (
                f"Forbidden CO2/env field '{field}' found in SCOR entry: {entry}"
            )


# ---------------------------------------------------------------------------
# Test: Exactly the 5 required fields and nothing else
# ---------------------------------------------------------------------------

REQUIRED_SCOR_FIELDS = {
    "cluster_id", "fila_actual", "tempo_espera_min",
    "fluxo_entrada_pmin", "ocupacao_pct",
}


def test_scor_entries_have_exactly_5_fields():
    sections = _make_sections()
    entries = build_scor_entries(sections)
    for entry in entries:
        assert set(entry.keys()) == REQUIRED_SCOR_FIELDS, (
            f"SCOR entry has unexpected fields. "
            f"Expected {REQUIRED_SCOR_FIELDS}, got {set(entry.keys())}"
        )


# ---------------------------------------------------------------------------
# Test: Never sends gendered unisex variants as cluster_ids
# ---------------------------------------------------------------------------

FORBIDDEN_CLUSTER_IDS = {f"{cid}_{g}" for cid in ("WC-05", "WC-06")
                         for g in ("M", "F")}


def test_scor_no_forbidden_cluster_ids():
    sections = _make_sections()
    entries = build_scor_entries(sections)
    for entry in entries:
        assert entry["cluster_id"] not in FORBIDDEN_CLUSTER_IDS, (
            f"Forbidden cluster_id '{entry['cluster_id']}' found in SCOR entries"
        )


def test_scor_wc05_cluster_id_is_wc05():
    """WC-05 (unisex) maps to cluster_id 'WC-05', not a gendered variant."""
    sections = _make_sections()
    entries = build_scor_entries(sections)
    wc05_entries = [e for e in entries if e["cluster_id"] == "WC-05"]
    assert len(wc05_entries) >= 1, "WC-05 should appear in SCOR entries"
    for e in wc05_entries:
        assert e["cluster_id"] == "WC-05"


def test_scor_wc06_cluster_id_is_wc06():
    """WC-06 (unisex) maps to cluster_id 'WC-06', not a gendered variant."""
    sections = _make_sections()
    entries = build_scor_entries(sections)
    wc06_entries = [e for e in entries if e["cluster_id"] == "WC-06"]
    assert len(wc06_entries) >= 1, "WC-06 should appear in SCOR entries"
    for e in wc06_entries:
        assert e["cluster_id"] == "WC-06"


# ---------------------------------------------------------------------------
# Test: SCOR publish_scor_sections dry_run=True returns 14 entries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scor_publish_sections_dry_run():
    from app.services.scor import publish_scor_sections
    sections = _make_sections()
    result = await publish_scor_sections(sections, dry_run=True)
    assert result["status"] == "dry_run"
    assert result["sections_sent"] == 14
    assert len(result["entries"]) == 14


# ---------------------------------------------------------------------------
# Test: POST /api/v1/scor/dry-run → 200 with sections_sent=14
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scor_endpoint_dry_run_200(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_scor_endpoint_dry_run_sections_sent(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    assert data["sections_sent"] == 14, (
        f"Expected sections_sent=14, got {data.get('sections_sent')}"
    )


@pytest.mark.asyncio
async def test_scor_endpoint_dry_run_no_gps(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    assert data["gps_present"] is False, "gps_present should be False in dry-run"


@pytest.mark.asyncio
async def test_scor_endpoint_dry_run_no_co2(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    assert data["co2_present"] is False, "co2_present should be False in dry-run"


@pytest.mark.asyncio
async def test_scor_endpoint_dry_run_status_ok(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    assert data["status"] == "dry_run_ok"


@pytest.mark.asyncio
async def test_scor_endpoint_dry_run_sample_has_required_fields(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    sample = data.get("sample", {})
    for field in ("cluster_id", "fila_actual", "tempo_espera_min",
                   "fluxo_entrada_pmin", "ocupacao_pct"):
        assert field in sample, f"Required SCOR field '{field}' missing from sample"


@pytest.mark.asyncio
async def test_scor_endpoint_dry_run_sample_no_forbidden_cluster(client: AsyncClient):
    response = await client.post("/api/v1/scor/dry-run")
    data = response.json()
    sample = data.get("sample", {})
    cluster_id = sample.get("cluster_id", "")
    assert cluster_id not in FORBIDDEN_CLUSTER_IDS, (
        f"Forbidden cluster_id '{cluster_id}' in SCOR sample"
    )


# ---------------------------------------------------------------------------
# Test: build_scor_entries rejects wrong section count
# ---------------------------------------------------------------------------

def test_scor_build_rejects_wrong_count():
    sections = _make_sections()[:10]  # only 10, not 14
    with pytest.raises(ValueError, match="14"):
        build_scor_entries(sections)
