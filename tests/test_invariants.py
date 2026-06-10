"""Tests 1-7: Model invariants for SECTION_IDS, UNISEX_SECTIONS, SectionState."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.sections import (
    SECTION_IDS,
    UNISEX_SECTIONS,
    SectionState,
)


# ---------------------------------------------------------------------------
# Test 1 — Exactly 14 section IDs
# ---------------------------------------------------------------------------
def test_exactly_14_section_ids():
    assert len(SECTION_IDS) == 14, (
        f"Expected 14 section IDs, got {len(SECTION_IDS)}: {list(SECTION_IDS)}"
    )


# ---------------------------------------------------------------------------
# Test 2 — WC-05 and WC-06 in UNISEX_SECTIONS
# ---------------------------------------------------------------------------
def test_wc05_in_unisex():
    assert "WC-05" in UNISEX_SECTIONS


def test_wc06_in_unisex():
    assert "WC-06" in UNISEX_SECTIONS


# ---------------------------------------------------------------------------
# Test 3 — SectionState with gender for WC-05 raises ValueError
# ---------------------------------------------------------------------------
def test_section_state_wc05_gender_m_raises():
    with pytest.raises((ValidationError, ValueError)):
        SectionState(section_id="WC-05", gender="M")


def test_section_state_wc05_gender_f_raises():
    with pytest.raises((ValidationError, ValueError)):
        SectionState(section_id="WC-05", gender="F")


# ---------------------------------------------------------------------------
# Test 4 — SectionState with gender for WC-06 raises ValueError
# ---------------------------------------------------------------------------
def test_section_state_wc06_gender_m_raises():
    with pytest.raises((ValidationError, ValueError)):
        SectionState(section_id="WC-06", gender="M")


def test_section_state_wc06_gender_f_raises():
    with pytest.raises((ValidationError, ValueError)):
        SectionState(section_id="WC-06", gender="F")


# ---------------------------------------------------------------------------
# Test 5 — SectionState with invalid section_id raises ValueError
# ---------------------------------------------------------------------------
def test_section_state_invalid_id_raises():
    with pytest.raises((ValidationError, ValueError)):
        SectionState(section_id="BOGUS-99")


def test_section_state_invalid_id_raises_empty_string():
    with pytest.raises((ValidationError, ValueError)):
        SectionState(section_id="")


def test_section_state_invalid_id_raises_typo():
    with pytest.raises((ValidationError, ValueError)):
        SectionState(section_id="WC-05" + "_M")  # WC-05 is unisex, no _M variant


# ---------------------------------------------------------------------------
# Test 6 — SectionState confidence always in [0, 1]
# ---------------------------------------------------------------------------
def test_sensor_reading_confidence_valid_range():
    """SectionState itself doesn't have a confidence field, but SensorReading does."""
    from app.models.sections import SensorReading
    import time

    r = SensorReading(
        source_id="test",
        source_type="ir",
        ts=time.time(),
        value=5.0,
        confidence=0.75,
    )
    assert 0.0 <= r.confidence <= 1.0


def test_sensor_reading_confidence_zero():
    from app.models.sections import SensorReading
    import time

    r = SensorReading(
        source_id="test",
        source_type="wifi",
        ts=time.time(),
        value=0.0,
        confidence=0.0,
    )
    assert r.confidence == 0.0


def test_sensor_reading_confidence_one():
    from app.models.sections import SensorReading
    import time

    r = SensorReading(
        source_id="test",
        source_type="camera",
        ts=time.time(),
        value=1.0,
        confidence=1.0,
    )
    assert r.confidence == 1.0


def test_sensor_reading_confidence_above_one_raises():
    from app.models.sections import SensorReading
    import time

    with pytest.raises((ValidationError, ValueError)):
        SensorReading(
            source_id="test",
            source_type="ir",
            ts=time.time(),
            value=1.0,
            confidence=1.1,
        )


def test_sensor_reading_confidence_below_zero_raises():
    from app.models.sections import SensorReading
    import time

    with pytest.raises((ValidationError, ValueError)):
        SensorReading(
            source_id="test",
            source_type="ir",
            ts=time.time(),
            value=1.0,
            confidence=-0.1,
        )


# ---------------------------------------------------------------------------
# Test 7 — No section produces gendered variants of the unisex sections
# ---------------------------------------------------------------------------
FORBIDDEN_IDS = {f"{cid}_{g}" for cid in ("WC-05", "WC-06") for g in ("M", "F")}


def test_forbidden_gendered_ids_not_in_section_ids():
    """The fixed tuple must never contain gendered variants of unisex sections."""
    for fid in FORBIDDEN_IDS:
        assert fid not in SECTION_IDS, (
            f"Forbidden section ID '{fid}' found in SECTION_IDS"
        )


def test_cannot_construct_forbidden_section_state():
    """It must be impossible to construct a SectionState with a forbidden ID."""
    for fid in FORBIDDEN_IDS:
        with pytest.raises((ValidationError, ValueError)):
            SectionState(section_id=fid)


def test_all_14_ids_are_valid_and_unique():
    """All 14 IDs should be unique strings."""
    assert len(set(SECTION_IDS)) == 14


def test_section_state_valid_unisex_no_gender():
    """WC-05 and WC-06 should accept gender=None without raising."""
    s5 = SectionState(section_id="WC-05", gender=None)
    assert s5.gender is None

    s6 = SectionState(section_id="WC-06", gender=None)
    assert s6.gender is None


def test_section_state_valid_gendered_sections():
    """Gendered sections (e.g., WC-01_M) should accept their gender."""
    s = SectionState(section_id="WC-01_M", gender="M")
    assert s.gender == "M"

    s2 = SectionState(section_id="WC-01_F", gender="F")
    assert s2.gender == "F"


# ---------------------------------------------------------------------------
# NorthStar invariants I-1..I-8
# ---------------------------------------------------------------------------

def test_startup_assert_passes():
    """startup_assert() must complete without raising."""
    from app.fusion import startup_assert
    startup_assert()


def test_i5_fusion_result_has_confianca():
    """I-5: FusionResult must always carry a 'confianca' field."""
    import dataclasses
    from app.fusion import FusionResult
    field_names = {f.name for f in dataclasses.fields(FusionResult)}
    assert "confianca" in field_names, "I-5: FusionResult missing 'confianca'"


def test_i5_section_state_has_confianca():
    """I-5: SectionState must also carry 'confianca' after the §3.5 extension."""
    s = SectionState(section_id="WC-01_M")
    assert hasattr(s, "confianca"), "I-5: SectionState missing 'confianca'"
    assert 0.0 <= s.confianca <= 1.0


def test_i7_all_cluster_ids_valid():
    """I-7: every cluster_id in ALL_CLUSTERS must match CLUSTER_ID_RE."""
    import re
    from app.sensors_topology import CLUSTER_ID_RE
    from app.clusters_capacity import ALL_CLUSTERS
    for cid in ALL_CLUSTERS:
        assert re.match(CLUSTER_ID_RE, cid), (
            f"I-7: '{cid}' does not match {CLUSTER_ID_RE!r}"
        )


def test_i8_critical_colour():
    """I-8: CRITICAL_COLOUR must be #C25A1A — never red."""
    from app.sensors_topology import CRITICAL_COLOUR
    assert CRITICAL_COLOUR == "#C25A1A", (
        f"I-8: CRITICAL_COLOUR={CRITICAL_COLOUR!r}, expected '#C25A1A'"
    )


def test_i3_base_weights_sum_to_one():
    """I-3/§3.2: BASE_WEIGHTS must sum to exactly 1.0."""
    from app.sensors_topology import BASE_WEIGHTS
    total = sum(BASE_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"BASE_WEIGHTS sum={total:.10f}, expected 1.0"


def test_i1_fusion_input_has_no_env_fields():
    """I-1: FusionInput must not expose environmental fields (CO₂, temp, humidity)."""
    import dataclasses
    from app.fusion import FusionInput
    field_names = {f.name for f in dataclasses.fields(FusionInput)}
    forbidden = {"co2_ppm", "temperatura", "humidade", "humidity", "temp_c"}
    overlap = field_names & forbidden
    assert not overlap, f"I-1: FusionInput contains env fields: {overlap}"


def test_i4_fuse_section_all_sources_dead_no_crash():
    """I-4: fuse_section with no live sources must not raise and must return confianca."""
    from app.fusion import FusionInput, fuse_section, CONF_FLOOR
    inp = FusionInput(section_id="wc-05", ts_ms=0, usar_ir=False)
    result = fuse_section(inp)
    assert 0.0 <= result.confianca <= 1.0
    assert result.stale is True
