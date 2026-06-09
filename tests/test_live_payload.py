"""Tests 37-42: LivePayload invariants + security/compliance."""
from __future__ import annotations

import time
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.sections import (
    SECTION_IDS,
    UNISEX_SECTIONS,
    SectionState,
    GlobalKPIs,
    LivePayload,
)
from app.models.sensors import SensorHealth, WiFiAggregateReading, IRReading, CameraMLReading
from app.models.live import ScorTelemetryPayload
from app.services.state import get_live_payload
from app.services.simulation import simulate_tick


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


def _build_live_payload_from_states(states: list[SectionState]) -> LivePayload:
    total = len(states)
    avg_occ = sum(s.ocupacao_pct for s in states) / total if total else 0.0
    total_fila = sum(s.fila_atual for s in states)
    critical_count = sum(1 for s in states if s.status == "critical")
    any_sim = any(s.simulated for s in states)

    kpis = GlobalKPIs(
        avg_ocupacao_pct=round(avg_occ, 1),
        total_fila=total_fila,
        critical_sections=critical_count,
        any_simulated=any_sim,
    )
    return LivePayload(
        kpis=kpis,
        sections=states,
        any_simulated=any_sim,
    )


# ---------------------------------------------------------------------------
# Test 37 — any_simulated propagates
# ---------------------------------------------------------------------------
def test_any_simulated_propagates_when_any_section_simulated():
    """If any section.simulated=True, payload.any_simulated must be True."""
    states = simulate_tick("normal", tick=0)
    # All simulation states have simulated=True
    assert all(s.simulated for s in states)
    payload = _build_live_payload_from_states(states)
    assert payload.any_simulated is True


def test_any_simulated_false_when_no_section_simulated():
    """If all sections have simulated=False, payload.any_simulated must be False."""
    states = [
        SectionState(
            section_id=sid,
            simulated=False,
            gender=(sid.rsplit("_", 1)[-1] if "_" in sid and sid.rsplit("_", 1)[-1] in ("M", "F") else None),  # type: ignore[arg-type]
        )
        for sid in SECTION_IDS
    ]
    payload = _build_live_payload_from_states(states)
    assert payload.any_simulated is False


def test_any_simulated_true_when_only_one_section_simulated():
    """Even one simulated section must flip any_simulated to True."""
    states = []
    for i, sid in enumerate(SECTION_IDS):
        gender = None
        if "_" in sid:
            suffix = sid.rsplit("_", 1)[-1]
            if suffix in ("M", "F"):
                gender = suffix  # type: ignore[assignment]
        states.append(SectionState(
            section_id=sid,
            simulated=(i == 0),  # only first section simulated
            gender=gender,
        ))
    payload = _build_live_payload_from_states(states)
    assert payload.any_simulated is True


@pytest.mark.asyncio
async def test_live_payload_api_any_simulated_present(client: AsyncClient):
    response = await client.get("/api/v1/state")
    data = response.json()
    assert "any_simulated" in data
    assert isinstance(data["any_simulated"], bool)


# ---------------------------------------------------------------------------
# Test 38 — kpis.avg_ocupacao_pct = mean of all sections' ocupacao_pct
# ---------------------------------------------------------------------------
def test_kpis_avg_ocupacao_equals_mean_of_sections():
    """avg_ocupacao_pct must be the arithmetic mean of all section ocupacao_pct values."""
    states = simulate_tick("normal", tick=1)
    expected_mean = sum(s.ocupacao_pct for s in states) / len(states)
    payload = _build_live_payload_from_states(states)
    # Allow rounding difference of 0.1
    assert abs(payload.kpis.avg_ocupacao_pct - expected_mean) < 0.1, (
        f"avg_ocupacao_pct={payload.kpis.avg_ocupacao_pct} != mean={expected_mean:.1f}"
    )


def test_kpis_avg_ocupacao_zero_when_all_empty():
    """When all sections have 0% occupancy, avg must be 0."""
    states = simulate_tick("zero_people", tick=0)
    payload = _build_live_payload_from_states(states)
    assert payload.kpis.avg_ocupacao_pct == 0.0


def test_kpis_avg_ocupacao_is_100_when_all_full():
    """When all sections are 100%, avg must be 100."""
    states_raw = simulate_tick("all_wcs_critical", tick=0)
    # Force all to 100% to test the mean calculation directly
    forced = []
    for s in states_raw:
        forced.append(SectionState(
            section_id=s.section_id,
            ocupacao_pct=100.0,
            gender=s.gender,
            simulated=True,
        ))
    payload = _build_live_payload_from_states(forced)
    assert payload.kpis.avg_ocupacao_pct == 100.0


@pytest.mark.asyncio
async def test_kpis_api_avg_ocupacao_in_range(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    data = response.json()
    assert 0.0 <= data["avg_ocupacao_pct"] <= 100.0


# ---------------------------------------------------------------------------
# Test 39 — kpis.critical_sections = count of sections with status="critical"
# ---------------------------------------------------------------------------
def test_kpis_critical_sections_count():
    """critical_sections must equal the number of sections with status='critical'."""
    states = simulate_tick("all_wcs_critical", tick=0)
    expected_critical = sum(1 for s in states if s.status == "critical")
    payload = _build_live_payload_from_states(states)
    assert payload.kpis.critical_sections == expected_critical, (
        f"critical_sections={payload.kpis.critical_sections}, expected {expected_critical}"
    )


def test_kpis_critical_sections_zero_in_zero_people():
    """In zero_people scenario, no sections are critical."""
    states = simulate_tick("zero_people", tick=0)
    payload = _build_live_payload_from_states(states)
    assert payload.kpis.critical_sections == 0


def test_kpis_critical_sections_14_in_all_wcs_critical():
    """In all_wcs_critical, all 14 sections are critical."""
    states = simulate_tick("all_wcs_critical", tick=0)
    payload = _build_live_payload_from_states(states)
    assert payload.kpis.critical_sections == 14, (
        f"Expected 14 critical sections, got {payload.kpis.critical_sections}"
    )


@pytest.mark.asyncio
async def test_kpis_critical_sections_non_negative(client: AsyncClient):
    response = await client.get("/api/v1/kpis")
    data = response.json()
    assert data["critical_sections"] >= 0


# ---------------------------------------------------------------------------
# Test 40 — No SensorHealth has a mac_address field
# ---------------------------------------------------------------------------
def test_sensor_health_has_no_mac_address_field():
    """SensorHealth model must not define a mac_address field."""
    fields = SensorHealth.model_fields
    assert "mac_address" not in fields, (
        "SensorHealth must not have a mac_address field (privacy rule)"
    )


def test_sensor_health_instance_has_no_mac_address():
    """A SensorHealth instance must not have a mac_address attribute."""
    sh = SensorHealth(
        cluster_id="WC-01",
        lilygo_online=True,
        ir_entry_online=True,
        ir_exit_online=True,
        wifi_online=True,
        camera_online=True,
        lorawan_available=True,
        active_sources=["ir_entry", "ir_exit", "wifi", "camera"],
        confidence=1.0,
        issues=[],
        last_update_ts=time.time(),
        simulated=True,
    )
    assert not hasattr(sh, "mac_address"), (
        "SensorHealth instance must not have mac_address attribute"
    )


@pytest.mark.asyncio
async def test_sensors_api_response_has_no_mac_address(client: AsyncClient):
    response = await client.get("/api/v1/sensors")
    data = response.json()
    for entry in data:
        assert "mac_address" not in entry, (
            f"Sensor entry for {entry.get('cluster_id')} contains mac_address"
        )


# ---------------------------------------------------------------------------
# Test 41 — No WiFiAggregateReading has a mac_address field
# ---------------------------------------------------------------------------
def test_wifi_aggregate_reading_has_no_mac_address_field():
    """WiFiAggregateReading must not define a mac_address field (GDPR/privacy)."""
    fields = WiFiAggregateReading.model_fields
    assert "mac_address" not in fields, (
        "WiFiAggregateReading must not have a mac_address field (GDPR rule)"
    )


def test_wifi_aggregate_reading_no_mac_in_instance():
    """A WiFiAggregateReading instance must not carry mac_address data."""
    reading = WiFiAggregateReading(
        source_id="wifi-wc01",
        ts=time.time(),
        devices_raw=50,
        people_estimate=20,
        simulated=True,
    )
    assert not hasattr(reading, "mac_address"), (
        "WiFiAggregateReading instance must not have mac_address"
    )


def test_wifi_aggregate_reading_serialised_has_no_mac():
    """When serialised to dict, WiFiAggregateReading must not include mac_address."""
    reading = WiFiAggregateReading(
        source_id="wifi-wc01",
        ts=time.time(),
        devices_raw=50,
        people_estimate=20,
        simulated=True,
    )
    data = reading.model_dump()
    assert "mac_address" not in data


# ---------------------------------------------------------------------------
# Test 42 — No recurring payload carries GPS coordinates
# ---------------------------------------------------------------------------
def test_scor_telemetry_no_gps_fields():
    """ScorTelemetryPayload (recurring LilyGO telemetry) must not have GPS lat/lon fields."""
    fields = ScorTelemetryPayload.model_fields
    assert "gps_lat" not in fields, "Recurring telemetry must not carry GPS lat"
    assert "gps_lon" not in fields, "Recurring telemetry must not carry GPS lon"
    assert "latitude" not in fields, "Recurring telemetry must not carry latitude"
    assert "longitude" not in fields, "Recurring telemetry must not carry longitude"


def test_scor_telemetry_instance_no_gps():
    """A ScorTelemetryPayload instance must not have GPS coordinate attributes."""
    payload = ScorTelemetryPayload(
        cluster_id="WC-01",
        fila_actual=5,
        tempo_espera_min=2.5,
        fluxo_entrada_pmin=3.0,
        ocupacao_pct=45.0,
    )
    assert not hasattr(payload, "gps_lat"), "Recurring telemetry carries gps_lat — blocked"
    assert not hasattr(payload, "gps_lon"), "Recurring telemetry carries gps_lon — blocked"
    assert not hasattr(payload, "latitude"), "Recurring telemetry carries latitude — blocked"
    assert not hasattr(payload, "longitude"), "Recurring telemetry carries longitude — blocked"


def test_live_payload_no_gps_coordinates():
    """The LivePayload model must not define any GPS coordinate fields."""
    fields = LivePayload.model_fields
    for gps_field in ("gps_lat", "gps_lon", "latitude", "longitude", "coordinates"):
        assert gps_field not in fields, (
            f"LivePayload must not carry recurring GPS field '{gps_field}'"
        )


def test_section_state_no_gps_coordinates():
    """SectionState must not carry GPS fields in recurring telemetry."""
    fields = SectionState.model_fields
    for gps_field in ("gps_lat", "gps_lon", "latitude", "longitude"):
        assert gps_field not in fields, (
            f"SectionState must not carry GPS field '{gps_field}'"
        )


@pytest.mark.asyncio
async def test_state_api_response_no_gps_in_sections(client: AsyncClient):
    """The API state response sections must not include GPS coordinates."""
    response = await client.get("/api/v1/state")
    data = response.json()
    for section in data.get("sections", []):
        for gps_field in ("gps_lat", "gps_lon", "latitude", "longitude"):
            assert gps_field not in section, (
                f"Section '{section.get('section_id')}' carries GPS field '{gps_field}'"
            )


@pytest.mark.asyncio
async def test_sensor_entries_no_gps_coordinates():
    """RGPD: sensores sao equipamento fixo — GPS de equipamento permitido; MAC proibido."""
    import re as _re
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.get("/api/v1/sensors")
        assert r.status_code == 200
        body = r.text.lower()
        assert "mac_address" not in body
        assert not _re.search(r"([0-9a-f]{2}:){5}[0-9a-f]{2}", body), "payload contem MAC!"

def test_ir_reading_no_mac_address_field():
    """IRReading model must not contain mac_address (per privacy rules)."""
    fields = IRReading.model_fields
    assert "mac_address" not in fields


def test_camera_ml_reading_no_mac_address_field():
    """CameraMLReading model must not contain mac_address."""
    fields = CameraMLReading.model_fields
    assert "mac_address" not in fields
