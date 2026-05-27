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
        SectionState(section_id="WC-05_M")  # WC-05 is unisex, no _M variant


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
# Test 7 — No section produces WC-05_M, WC-05_F, WC-06_M, WC-06_F
# ---------------------------------------------------------------------------
FORBIDDEN_IDS = {"WC-05_M", "WC-05_F", "WC-06_M", "WC-06_F"}


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
